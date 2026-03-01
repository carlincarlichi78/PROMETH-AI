"""SFCE API — Endpoints exportación RGPD.

Genera un ZIP con todos los datos de una empresa (facturas, asientos, partidas)
mediante un token de un solo uso con TTL 24 horas.
"""
import csv
import io
import zipfile
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from sfce.api.auth import JWT_ALGORITHM, _get_secret, obtener_usuario_actual, verificar_acceso_empresa
from sfce.api.audit import AuditAccion, auditar, ip_desde_request
from sfce.db.modelos import Asiento, Documento, Partida


router = APIRouter(tags=["rgpd"])

# Roles que pueden generar exportaciones RGPD
_ROLES_EXPORTACION = {"superadmin", "admin_gestoria", "admin", "gestor"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _verificar_rol_exportacion(request: Request) -> None:
    """Verifica que el usuario tenga rol autorizado para exportar datos."""
    usuario = obtener_usuario_actual(request)
    if usuario.rol not in _ROLES_EXPORTACION:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No autorizado. Se requiere rol gestor o admin.",
        )


def _generar_csv(filas: list[dict], campos: list[str]) -> str:
    """Genera CSV en memoria con los campos indicados."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=campos, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(filas)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/api/empresas/{empresa_id}/exportar-datos")
def generar_token_exportacion(empresa_id: int, request: Request):
    """Genera token de un solo uso (24h) para descarga RGPD de la empresa."""
    _verificar_rol_exportacion(request)
    usuario = obtener_usuario_actual(request)

    sf = request.app.state.sesion_factory
    with sf() as s:
        verificar_acceso_empresa(usuario, empresa_id, s)

    nonce = str(uuid4())
    expira = datetime.now(timezone.utc) + timedelta(hours=24)

    payload = {
        "sub": "rgpd_export",
        "empresa_id": empresa_id,
        "once": nonce,
        "exp": expira,
    }
    token = jwt.encode(payload, _get_secret(), algorithm=JWT_ALGORITHM)

    # Registrar nonce como "no usado aún"
    if not hasattr(request.app.state, "rgpd_nonces_usados"):
        request.app.state.rgpd_nonces_usados = set()
    # El nonce se registra como "emitido"; se marca usado al descargar

    sf = request.app.state.sesion_factory
    ip = ip_desde_request(request)
    usuario = obtener_usuario_actual(request)
    with sf() as sesion:
        auditar(
            sesion, AuditAccion.EXPORT, "empresa",
            usuario_id=usuario.id,
            email_usuario=usuario.email,
            recurso_id=str(empresa_id),
            ip_origen=ip,
            resultado="ok",
            detalles={"accion": "generar_token_rgpd", "nonce": nonce},
        )
        sesion.commit()

    url = f"/api/rgpd/descargar/{token}"
    return {
        "token": token,
        "url": url,
        "url_descarga": url,
        "expira": expira.isoformat(),
    }


@router.get("/api/rgpd/descargar/{token}")
def descargar_exportacion(token: str, request: Request):
    """Descarga ZIP RGPD. Token de un solo uso — segunda petición retorna 404."""
    # Verificar y decodificar JWT
    try:
        payload = jwt.decode(token, _get_secret(), algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido.")

    if payload.get("sub") != "rgpd_export":
        raise HTTPException(status_code=401, detail="Token inválido.")

    empresa_id = payload["empresa_id"]
    nonce = payload.get("once", "")

    # Verificar uso único
    if not hasattr(request.app.state, "rgpd_nonces_usados"):
        request.app.state.rgpd_nonces_usados = set()

    if nonce in request.app.state.rgpd_nonces_usados:
        raise HTTPException(
            status_code=404,
            detail="Token ya utilizado. Genera un nuevo enlace de descarga.",
        )

    # Marcar como usado ANTES de generar el ZIP
    request.app.state.rgpd_nonces_usados.add(nonce)

    # El token JWT ya acredita la empresa y fue generado por un usuario autenticado.
    # No se requiere auth adicional — el nonce de un solo uso es el mecanismo de seguridad.
    sf = request.app.state.sesion_factory

    # Generar ZIP en memoria
    with sf() as sesion:
        asientos = sesion.query(Asiento).filter(Asiento.empresa_id == empresa_id).all()
        asiento_ids = [a.id for a in asientos]

        partidas = (
            sesion.query(Partida)
            .filter(Partida.asiento_id.in_(asiento_ids))
            .all()
        ) if asiento_ids else []

        documentos = sesion.query(Documento).filter(Documento.empresa_id == empresa_id).all()

        # Serializar datos
        filas_asientos = [
            {
                "id": a.id,
                "ejercicio": a.ejercicio,
                "fecha": str(a.fecha),
                "concepto": a.concepto or "",
            }
            for a in asientos
        ]
        filas_partidas = [
            {
                "asiento_id": p.asiento_id,
                "subcuenta": p.subcuenta,
                "debe": float(p.debe or 0),
                "haber": float(p.haber or 0),
                "concepto": p.concepto or "",
            }
            for p in partidas
        ]
        filas_facturas = [
            {
                "id": d.id,
                "tipo": d.tipo_doc,
                "estado": d.estado,
                "ejercicio": d.ejercicio or "",
                "fecha_proceso": str(d.fecha_proceso) if d.fecha_proceso else "",
            }
            for d in documentos
        ]

    # Crear ZIP
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "asientos.csv",
            _generar_csv(filas_asientos, ["id", "ejercicio", "fecha", "concepto"]),
        )
        zf.writestr(
            "partidas.csv",
            _generar_csv(filas_partidas, ["asiento_id", "subcuenta", "debe", "haber", "concepto"]),
        )
        zf.writestr(
            "facturas.csv",
            _generar_csv(filas_facturas, ["id", "tipo", "estado", "ejercicio", "fecha_proceso"]),
        )

    buf.seek(0)

    # Auditar descarga
    with sf() as sesion:
        auditar(
            sesion, AuditAccion.EXPORT, "empresa",
            recurso_id=str(empresa_id),
            ip_origen=ip_desde_request(request),
            resultado="ok",
            detalles={"accion": "descarga_rgpd", "nonce": nonce},
        )
        sesion.commit()

    nombre_archivo = f"exportacion_empresa_{empresa_id}_{datetime.now().strftime('%Y%m%d')}.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{nombre_archivo}"'},
    )
