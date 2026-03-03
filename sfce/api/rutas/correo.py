"""API REST módulo de correo: cuentas IMAP, emails procesados, reglas de clasificación."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from sfce.api.app import get_sesion_factory
from sfce.api.auth import obtener_usuario_actual, verificar_acceso_empresa
from sfce.core.cifrado import cifrar
from sfce.db.modelos import (
    AdjuntoEmail, ColaProcesamiento, CuentaCorreo, EmailProcesado,
    ReglaClasificacionCorreo, RemitenteAutorizado,
)

router = APIRouter(prefix="/api/correo", tags=["correo"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _test_conexion_imap(servidor: str, puerto: int, ssl: bool, usuario: str, contrasena: str) -> bool:
    """Intenta conectar vía IMAP para verificar credenciales."""
    import imaplib
    try:
        cls = imaplib.IMAP4_SSL if ssl else imaplib.IMAP4
        conn = cls(servidor, puerto)
        conn.login(usuario, contrasena)
        conn.logout()
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class CrearCuentaRequest(BaseModel):
    nombre: str
    empresa_id: int
    servidor: str
    puerto: int = 993
    ssl: bool = True
    usuario: str
    contrasena: str
    carpeta_entrada: str = "INBOX"


# ---------------------------------------------------------------------------
# Schemas admin
# ---------------------------------------------------------------------------

class CrearCuentaAdminRequest(BaseModel):
    nombre: str
    tipo_cuenta: str = "empresa"     # 'empresa'|'dedicada'|'gestoria'|'sistema'|'asesor'
    empresa_id: int | None = None
    gestoria_id: int | None = None
    usuario_id: int | None = None    # FK a usuarios.id, requerido para tipo='asesor'
    servidor: str | None = None
    puerto: int = 993
    ssl: bool = True
    usuario: str
    contrasena: str
    carpeta_entrada: str = "INBOX"
    polling_intervalo_segundos: int = 120


class ActualizarCuentaAdminRequest(BaseModel):
    nombre: str | None = None
    servidor: str | None = None
    puerto: int | None = None
    ssl: bool | None = None
    contrasena: str | None = None
    activa: bool | None = None


class CrearReglaRequest(BaseModel):
    empresa_id: int
    tipo: str
    condicion_json: str
    accion: str
    slug_destino: str | None = None
    prioridad: int = 100


class ActualizarEmailRequest(BaseModel):
    estado: str | None = None
    empresa_destino_id: int | None = None


# ---------------------------------------------------------------------------
# Cuentas IMAP
# ---------------------------------------------------------------------------

@router.get("/cuentas/{cuenta_id}")
def obtener_cuenta(
    cuenta_id: int,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    """G8: devuelve 404 si la cuenta no existe o fue borrada."""
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as s:
        cuenta = s.get(CuentaCorreo, cuenta_id)
        if not cuenta:
            raise HTTPException(status_code=404, detail="Cuenta no encontrada")
        verificar_acceso_empresa(usuario, cuenta.empresa_id, s)
        return {
            "id": cuenta.id,
            "nombre": cuenta.nombre,
            "usuario": cuenta.usuario,
            "protocolo": cuenta.protocolo,
            "activa": cuenta.activa,
            "ultimo_uid": cuenta.ultimo_uid,
            "empresa_id": cuenta.empresa_id,
        }


@router.get("/cuentas")
def listar_cuentas(
    empresa_id: int,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as s:
        verificar_acceso_empresa(usuario, empresa_id, s)
        cuentas = s.execute(
            select(CuentaCorreo).where(CuentaCorreo.empresa_id == empresa_id)
        ).scalars().all()
        return [
            {"id": c.id, "nombre": c.nombre, "usuario": c.usuario,
             "protocolo": c.protocolo, "activa": c.activa,
             "ultimo_uid": c.ultimo_uid}
            for c in cuentas
        ]


@router.post("/cuentas", status_code=status.HTTP_201_CREATED)
def crear_cuenta(
    datos: CrearCuentaRequest,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as s:
        verificar_acceso_empresa(usuario, datos.empresa_id, s)
        cuenta = CuentaCorreo(
            empresa_id=datos.empresa_id,
            nombre=datos.nombre,
            protocolo="imap",
            servidor=datos.servidor,
            puerto=datos.puerto,
            ssl=datos.ssl,
            usuario=datos.usuario,
            contrasena_enc=cifrar(datos.contrasena),
            carpeta_entrada=datos.carpeta_entrada,
        )
        s.add(cuenta)
        s.commit()
        return {"id": cuenta.id, "nombre": cuenta.nombre}


@router.delete("/cuentas/{cuenta_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_cuenta(
    cuenta_id: int,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as s:
        cuenta = s.get(CuentaCorreo, cuenta_id)
        if not cuenta:
            raise HTTPException(status_code=404, detail="Cuenta no encontrada")
        verificar_acceso_empresa(usuario, cuenta.empresa_id, s)
        s.delete(cuenta)
        s.commit()


@router.post("/cuentas/{cuenta_id}/sincronizar")
def sincronizar_cuenta(
    cuenta_id: int,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as s:
        cuenta = s.get(CuentaCorreo, cuenta_id)
        if not cuenta:
            raise HTTPException(status_code=404, detail="Cuenta no encontrada")
        verificar_acceso_empresa(usuario, cuenta.empresa_id, s)

    from sfce.db.base import crear_motor
    from sfce.api.app import _leer_config_bd
    from sfce.conectores.correo.ingesta_correo import IngestaCorreo
    nuevos = IngestaCorreo(engine=crear_motor(_leer_config_bd())).procesar_cuenta(cuenta_id)
    return {"nuevos_emails": nuevos}


# ---------------------------------------------------------------------------
# Emails procesados
# ---------------------------------------------------------------------------

@router.get("/emails")
def listar_emails(
    empresa_id: int,
    estado: str | None = None,
    limit: int = 20,
    offset: int = 0,
    request: Request = None,
    sesion_factory=Depends(get_sesion_factory),
):
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as s:
        verificar_acceso_empresa(usuario, empresa_id, s)
        cuentas_ids = s.execute(
            select(CuentaCorreo.id).where(CuentaCorreo.empresa_id == empresa_id)
        ).scalars().all()
        if not cuentas_ids:
            return {"emails": [], "total": 0}
        query = select(EmailProcesado).where(
            EmailProcesado.cuenta_id.in_(cuentas_ids)
        )
        if estado:
            query = query.where(EmailProcesado.estado == estado.upper())
        total_q = select(EmailProcesado).where(EmailProcesado.cuenta_id.in_(cuentas_ids))
        if estado:
            total_q = total_q.where(EmailProcesado.estado == estado.upper())
        total = len(s.execute(total_q).scalars().all())
        emails = s.execute(
            query.order_by(EmailProcesado.created_at.desc()).limit(limit).offset(offset)
        ).scalars().all()
        return {
            "emails": [
                {"id": e.id, "remitente": e.remitente, "asunto": e.asunto,
                 "estado": e.estado, "nivel_clasificacion": e.nivel_clasificacion,
                 "fecha_email": e.fecha_email, "created_at": str(e.created_at)}
                for e in emails
            ],
            "total": total,
        }


@router.patch("/emails/{email_id}")
def actualizar_email(
    email_id: int,
    datos: ActualizarEmailRequest,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as s:
        email = s.get(EmailProcesado, email_id)
        if not email:
            raise HTTPException(status_code=404, detail="Email no encontrado")
        # Verificar acceso via cuenta
        cuenta = s.get(CuentaCorreo, email.cuenta_id)
        if cuenta:
            verificar_acceso_empresa(usuario, cuenta.empresa_id, s)
        if datos.estado is not None:
            email.estado = datos.estado
        if datos.empresa_destino_id is not None:
            email.empresa_destino_id = datos.empresa_destino_id
        s.commit()
        return {"ok": True}


# ---------------------------------------------------------------------------
# Reglas de clasificación
# ---------------------------------------------------------------------------

@router.get("/reglas")
def listar_reglas(
    empresa_id: int,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as s:
        verificar_acceso_empresa(usuario, empresa_id, s)
        reglas = s.execute(
            select(ReglaClasificacionCorreo).where(
                (ReglaClasificacionCorreo.empresa_id == empresa_id)
                | ReglaClasificacionCorreo.empresa_id.is_(None)
            ).order_by(ReglaClasificacionCorreo.prioridad)
        ).scalars().all()
        return [
            {"id": r.id, "tipo": r.tipo, "accion": r.accion,
             "slug_destino": r.slug_destino, "prioridad": r.prioridad,
             "origen": r.origen, "activa": r.activa}
            for r in reglas
        ]


@router.post("/reglas", status_code=status.HTTP_201_CREATED)
def crear_regla(
    datos: CrearReglaRequest,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    # G12: CLASIFICAR requiere slug_destino
    if datos.accion == "CLASIFICAR" and not datos.slug_destino:
        raise HTTPException(
            status_code=422,
            detail="slug_destino es obligatorio cuando accion=CLASIFICAR",
        )
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as s:
        verificar_acceso_empresa(usuario, datos.empresa_id, s)
        regla = ReglaClasificacionCorreo(
            empresa_id=datos.empresa_id,
            tipo=datos.tipo,
            condicion_json=datos.condicion_json,
            accion=datos.accion,
            slug_destino=datos.slug_destino,
            prioridad=datos.prioridad,
        )
        s.add(regla)
        s.commit()
        return {"id": regla.id}


@router.delete("/reglas/{regla_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_regla(
    regla_id: int,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as s:
        regla = s.get(ReglaClasificacionCorreo, regla_id)
        if not regla:
            raise HTTPException(status_code=404, detail="Regla no encontrada")
        if regla.empresa_id:
            verificar_acceso_empresa(usuario, regla.empresa_id, s)
        s.delete(regla)
        s.commit()


# ---------------------------------------------------------------------------
# Endpoints admin — CRUD cuentas (solo superadmin)
# ---------------------------------------------------------------------------

@router.get("/admin/cuentas")
def admin_listar_cuentas(
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    usuario = obtener_usuario_actual(request)
    if usuario.rol != "superadmin":
        raise HTTPException(status_code=403, detail="Solo superadmin")
    with sesion_factory() as s:
        cuentas = s.execute(select(CuentaCorreo)).scalars().all()
        return [
            {
                "id": c.id,
                "nombre": c.nombre,
                "tipo_cuenta": c.tipo_cuenta,
                "usuario": c.usuario,
                "servidor": c.servidor,
                "activa": c.activa,
                "ultimo_uid": c.ultimo_uid,
                "empresa_id": c.empresa_id,
                "gestoria_id": c.gestoria_id,
            }
            for c in cuentas
        ]


@router.post("/admin/cuentas", status_code=201)
def admin_crear_cuenta(
    body: CrearCuentaAdminRequest,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    usuario = obtener_usuario_actual(request)
    if usuario.rol != "superadmin":
        raise HTTPException(status_code=403, detail="Solo superadmin")
    with sesion_factory() as s:
        cuenta = CuentaCorreo(
            nombre=body.nombre,
            tipo_cuenta=body.tipo_cuenta,
            empresa_id=body.empresa_id,
            gestoria_id=body.gestoria_id,
            usuario_id=body.usuario_id,
            protocolo="imap",
            servidor=body.servidor,
            puerto=body.puerto,
            ssl=body.ssl,
            usuario=body.usuario,
            contrasena_enc=cifrar(body.contrasena),
            carpeta_entrada=body.carpeta_entrada,
            polling_intervalo_segundos=body.polling_intervalo_segundos,
        )
        s.add(cuenta)
        s.commit()
        return {
            "id": cuenta.id,
            "nombre": cuenta.nombre,
            "tipo_cuenta": cuenta.tipo_cuenta,
            "usuario_id": cuenta.usuario_id,
            "usuario": cuenta.usuario,
            "activa": cuenta.activa,
        }


@router.put("/admin/cuentas/{cuenta_id}")
def admin_actualizar_cuenta(
    cuenta_id: int,
    body: ActualizarCuentaAdminRequest,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    usuario = obtener_usuario_actual(request)
    if usuario.rol != "superadmin":
        raise HTTPException(status_code=403, detail="Solo superadmin")
    with sesion_factory() as s:
        cuenta = s.get(CuentaCorreo, cuenta_id)
        if not cuenta:
            raise HTTPException(status_code=404)
        if body.nombre is not None:
            cuenta.nombre = body.nombre
        if body.servidor is not None:
            cuenta.servidor = body.servidor
        if body.puerto is not None:
            cuenta.puerto = body.puerto
        if body.ssl is not None:
            cuenta.ssl = body.ssl
        if body.contrasena is not None:
            cuenta.contrasena_enc = cifrar(body.contrasena)
        if body.activa is not None:
            cuenta.activa = body.activa
        s.commit()
        return {"id": cuenta.id, "activa": cuenta.activa}


@router.delete("/admin/cuentas/{cuenta_id}")
def admin_desactivar_cuenta(
    cuenta_id: int,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    usuario = obtener_usuario_actual(request)
    if usuario.rol != "superadmin":
        raise HTTPException(status_code=403, detail="Solo superadmin")
    with sesion_factory() as s:
        cuenta = s.get(CuentaCorreo, cuenta_id)
        if not cuenta:
            raise HTTPException(status_code=404)
        cuenta.activa = False
        s.commit()
        return {"ok": True}


@router.post("/admin/cuentas/{cuenta_id}/test")
def test_cuenta_conexion(
    cuenta_id: int,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    """Prueba la conexión IMAP de una cuenta. Solo superadmin."""
    usuario = obtener_usuario_actual(request)
    if usuario.rol != "superadmin":
        raise HTTPException(status_code=403, detail="Solo superadmin")
    with sesion_factory() as s:
        cuenta = s.get(CuentaCorreo, cuenta_id)
        if not cuenta:
            raise HTTPException(status_code=404, detail="Cuenta no encontrada")
        from sfce.core.cifrado import descifrar
        contrasena = descifrar(cuenta.contrasena_enc) if cuenta.contrasena_enc else ""
        servidor = cuenta.servidor or ""
        puerto = cuenta.puerto or 993
        ssl = cuenta.ssl if cuenta.ssl is not None else True
        usuario_imap = cuenta.usuario or ""
    ok = _test_conexion_imap(servidor, puerto, ssl, usuario_imap, contrasena)
    return {"ok": ok, "mensaje": "Conexión exitosa" if ok else "No se pudo conectar"}


# ---------------------------------------------------------------------------
# Endpoints gestoría — ver/actualizar su propia cuenta
# ---------------------------------------------------------------------------

@router.get("/gestorias/{gestoria_id}/cuenta-correo")
def gestoria_get_cuenta(
    gestoria_id: int,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    usuario = obtener_usuario_actual(request)
    if usuario.rol not in ("superadmin", "admin_gestoria"):
        raise HTTPException(status_code=403)
    if usuario.rol == "admin_gestoria" and usuario.gestoria_id != gestoria_id:
        raise HTTPException(status_code=403)
    with sesion_factory() as s:
        cuenta = s.execute(
            select(CuentaCorreo).where(
                CuentaCorreo.gestoria_id == gestoria_id,
                CuentaCorreo.tipo_cuenta == "gestoria",
            )
        ).scalar_one_or_none()
        if not cuenta:
            raise HTTPException(status_code=404, detail="Sin cuenta de correo configurada")
        return {
            "id": cuenta.id,
            "nombre": cuenta.nombre,
            "servidor": cuenta.servidor,
            "usuario": cuenta.usuario,
            "activa": cuenta.activa,
            "ultimo_uid": cuenta.ultimo_uid,
        }


@router.put("/gestorias/{gestoria_id}/cuenta-correo")
def gestoria_actualizar_cuenta(
    gestoria_id: int,
    body: ActualizarCuentaAdminRequest,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    usuario = obtener_usuario_actual(request)
    if usuario.rol not in ("superadmin", "admin_gestoria"):
        raise HTTPException(status_code=403)
    if usuario.rol == "admin_gestoria" and usuario.gestoria_id != gestoria_id:
        raise HTTPException(status_code=403)
    with sesion_factory() as s:
        cuenta = s.execute(
            select(CuentaCorreo).where(
                CuentaCorreo.gestoria_id == gestoria_id,
                CuentaCorreo.tipo_cuenta == "gestoria",
            )
        ).scalar_one_or_none()
        if not cuenta:
            raise HTTPException(status_code=404)
        if body.servidor is not None:
            cuenta.servidor = body.servidor
        if body.contrasena is not None:
            cuenta.contrasena_enc = cifrar(body.contrasena)
        if body.activa is not None:
            cuenta.activa = body.activa
        s.commit()
        return {"ok": True, "id": cuenta.id}


# ---------------------------------------------------------------------------
# Whitelist de remitentes autorizados (G5)
# ---------------------------------------------------------------------------

class AnadirRemitenteRequest(BaseModel):
    email: str
    nombre: str | None = None


@router.get("/empresas/{empresa_id}/remitentes-autorizados")
def listar_remitentes_autorizados(
    empresa_id: int,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    """Lista los remitentes autorizados de una empresa e indica si la whitelist está activa."""
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as s:
        verificar_acceso_empresa(usuario, empresa_id, s)
        remitentes = s.execute(
            select(RemitenteAutorizado).where(
                RemitenteAutorizado.empresa_id == empresa_id,
                RemitenteAutorizado.activo == True,  # noqa: E712
            )
        ).scalars().all()
        whitelist_activa = len(remitentes) > 0
        return {
            "remitentes": [
                {"id": r.id, "email": r.email, "nombre": r.nombre}
                for r in remitentes
            ],
            "whitelist_activa": whitelist_activa,
            "aviso_primer_remitente": whitelist_activa and len(remitentes) == 1,
        }


@router.post("/empresas/{empresa_id}/remitentes-autorizados", status_code=201)
def anadir_remitente_autorizado(
    empresa_id: int,
    body: AnadirRemitenteRequest,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    """Añade un remitente a la whitelist de la empresa. Idempotente por email+empresa."""
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as s:
        verificar_acceso_empresa(usuario, empresa_id, s)
        from sfce.conectores.correo.whitelist_remitentes import agregar_remitente
        rem = agregar_remitente(body.email, empresa_id, s, nombre=body.nombre)
        s.commit()
        return {"id": rem.id, "email": rem.email}


@router.delete("/remitentes/{remitente_id}", status_code=204)
def eliminar_remitente_autorizado(
    remitente_id: int,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    """Soft-delete de un remitente autorizado."""
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as s:
        rem = s.get(RemitenteAutorizado, remitente_id)
        if not rem:
            raise HTTPException(status_code=404, detail="Remitente no encontrado")
        verificar_acceso_empresa(usuario, rem.empresa_id, s)
        rem.activo = False
        s.commit()


# ---------------------------------------------------------------------------
# Confirmar enriquecimiento (Task 11)
# ---------------------------------------------------------------------------

class ConfirmarEnriquecimientoRequest(BaseModel):
    campos: dict  # {campo: valor}


@router.post("/emails/{email_id}/confirmar")
def confirmar_enriquecimiento(
    email_id: int,
    body: ConfirmarEnriquecimientoRequest,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    """Confirma campos de enriquecimiento para un email procesado.

    Actualiza los hints de los docs en cola que proceden de ese email
    y crea una regla de aprendizaje para clasificaciones futuras.
    """
    import json as _json

    usuario = obtener_usuario_actual(request)
    with sesion_factory() as s:
        ep = s.get(EmailProcesado, email_id)
        if not ep:
            raise HTTPException(status_code=404, detail="Email no encontrado")

        empresa_id = ep.empresa_destino_id
        if empresa_id:
            verificar_acceso_empresa(usuario, empresa_id, s)

        # 1. Actualizar hints en docs de cola que apuntan a este email
        docs_en_cola = s.execute(
            select(ColaProcesamiento).where(
                ColaProcesamiento.empresa_origen_correo_id == email_id
            )
        ).scalars().all()

        for doc in docs_en_cola:
            try:
                hints = _json.loads(doc.hints_json or "{}")
                enr = hints.get("enriquecimiento", {})
                enr.update(body.campos)
                hints["enriquecimiento"] = enr
                doc.hints_json = _json.dumps(hints)
            except Exception:
                pass

        # 2. Crear regla de aprendizaje basada en el remitente
        if empresa_id:
            try:
                regla = ReglaClasificacionCorreo(
                    empresa_id=empresa_id,
                    tipo="REMITENTE_EXACTO",
                    condicion_json=_json.dumps({"remitente": ep.remitente}),
                    accion="CLASIFICAR",
                    slug_destino=None,
                    confianza=1.0,
                    origen="APRENDIZAJE",
                    prioridad=50,
                    activa=True,
                )
                s.add(regla)
            except Exception:
                pass

        s.commit()
        return {"confirmado": True, "campos_aplicados": body.campos}
