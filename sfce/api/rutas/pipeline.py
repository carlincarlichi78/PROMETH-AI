"""SFCE API — Endpoints para el pipeline local.

El pipeline corre en el equipo del asesor (Windows u otro). Se autentica con
X-Pipeline-Token (token de servicio sin expiración) y puede:

  POST /api/pipeline/documentos/subir        → subir PDF al servidor
  GET  /api/pipeline/documentos/pendientes   → consultar cola por empresa
  GET  /api/pipeline/empresas                → listar empresas en scope del token
  GET  /api/pipeline/sync-status             → resumen contadores por empresa

El servidor procesa los documentos subidos automáticamente mediante
worker_pipeline.py (ciclo de 60s), sin intervención del pipeline local.
"""
import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form
from sqlalchemy import func, select

from sfce.api.app import get_sesion_factory
from sfce.api.audit import AuditAccion, auditar, ip_desde_request
from sfce.api.auth import verificar_token_servicio
from sfce.db.modelos import ColaProcesamiento, Documento, Empresa
from sfce.db.modelos_auth import TokenServicio

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])

# Directorio donde se almacenan los PDFs subidos por el pipeline
_UPLOADS_BASE = Path("docs/uploads")


def _empresas_en_scope(ts: TokenServicio, sesion) -> list[int]:
    """Devuelve lista de empresa_ids accesibles para este token."""
    empresa_ids_filtro = json.loads(ts.empresa_ids or "[]")

    if ts.gestoria_id is None:
        # scope superadmin → todas las empresas
        todas = sesion.scalars(select(Empresa.id)).all()
        return list(todas)

    q = select(Empresa.id).where(Empresa.gestoria_id == ts.gestoria_id)
    empresas_gestoria = sesion.scalars(q).all()

    if empresa_ids_filtro:
        # intersección: solo las que están en la lista Y en la gestoría
        return [e for e in empresas_gestoria if e in empresa_ids_filtro]
    return list(empresas_gestoria)


def _verificar_scope(ts: TokenServicio, empresa_id: int, sesion) -> None:
    """Lanza 403 si empresa_id no está en el scope del token."""
    en_scope = _empresas_en_scope(ts, sesion)
    if empresa_id not in en_scope:
        raise HTTPException(status_code=403, detail="Empresa fuera del scope del token")


@router.get("/empresas")
def listar_empresas_pipeline(request: Request):
    """Devuelve empresas accesibles para este token de servicio."""
    ts = verificar_token_servicio(request)
    sf = request.app.state.sesion_factory
    with sf() as s:
        ids = _empresas_en_scope(ts, s)
        if not ids:
            return []
        empresas = s.scalars(
            select(Empresa).where(Empresa.id.in_(ids)).order_by(Empresa.nombre)
        ).all()
        return [
            {
                "id": e.id,
                "nombre": e.nombre,
                "nif": getattr(e, "nif", None) or getattr(e, "cif", None),
                "slug": getattr(e, "slug", None),
                "gestoria_id": e.gestoria_id,
            }
            for e in empresas
        ]


@router.post("/documentos/subir", status_code=201)
async def subir_documento(
    request: Request,
    archivo: UploadFile = File(...),
    empresa_id: int = Form(...),
    ejercicio: Optional[str] = Form(None),
):
    """Sube un PDF al servidor y lo encola para procesamiento.

    Si ya existe un documento con el mismo SHA256 para esta empresa,
    devuelve {estado: "duplicado", documento_id} sin crear duplicado.
    El worker_pipeline.py recoge el documento en el próximo ciclo (60s).
    """
    ts = verificar_token_servicio(request)
    ejercicio = ejercicio or str(datetime.now(timezone.utc).year)

    sf = request.app.state.sesion_factory
    with sf() as s:
        _verificar_scope(ts, empresa_id, s)

        # Leer archivo y calcular SHA256
        contenido = await archivo.read()
        if not contenido:
            raise HTTPException(status_code=422, detail="El archivo está vacío")

        sha256 = hashlib.sha256(contenido).hexdigest()
        nombre_archivo = archivo.filename or f"doc_{sha256[:8]}.pdf"

        # Comprobar duplicado por SHA256 + empresa
        doc_existente = s.scalar(
            select(Documento).where(
                Documento.hash_pdf == sha256,
                Documento.empresa_id == empresa_id,
            )
        )
        if doc_existente:
            return {
                "documento_id": doc_existente.id,
                "cola_id": doc_existente.cola_id,
                "sha256": sha256,
                "estado": "duplicado",
            }

        # Guardar en disco
        ruta_dir = _UPLOADS_BASE / str(empresa_id)
        ruta_dir.mkdir(parents=True, exist_ok=True)
        nombre_en_disco = f"{sha256[:8]}_{nombre_archivo}"
        ruta_disco = ruta_dir / nombre_en_disco
        ruta_disco.write_bytes(contenido)

        # Crear Documento
        doc = Documento(
            empresa_id=empresa_id,
            tipo_doc="FV",         # tipo provisional; el worker lo detecta por OCR
            ruta_pdf=nombre_archivo,
            ruta_disco=str(ruta_disco),
            hash_pdf=sha256,
            estado="pendiente",
            ejercicio=ejercicio,
        )
        s.add(doc)
        s.flush()

        # Crear ColaProcesamiento para que el worker lo recoja
        cola = ColaProcesamiento(
            empresa_id=empresa_id,
            documento_id=doc.id,
            nombre_archivo=nombre_archivo,
            ruta_archivo=str(ruta_disco),
            estado="PENDIENTE",
            trust_level="MEDIA",
            sha256=sha256,
        )
        s.add(cola)
        s.flush()

        # Actualizar FK doc → cola
        doc.cola_id = cola.id

        # Auditoría
        auditar(
            s,
            AuditAccion.CREATE,
            "documento",
            usuario_id=None,
            email_usuario=f"pipeline:{ts.nombre}",
            rol="servicio",
            gestoria_id=ts.gestoria_id,
            recurso_id=str(doc.id),
            ip_origen=ip_desde_request(request),
            resultado="ok",
            detalles={
                "empresa_id": empresa_id,
                "nombre": nombre_archivo,
                "sha256": sha256,
                "ejercicio": ejercicio,
            },
        )

        s.commit()
        logger.info("pipeline: doc %s encolado para empresa %s", doc.id, empresa_id)

        return {
            "documento_id": doc.id,
            "cola_id": cola.id,
            "sha256": sha256,
            "estado": "encolado",
        }


@router.get("/documentos/pendientes")
def documentos_pendientes(
    request: Request,
    empresa_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
):
    """Lista documentos en cola PENDIENTE o CUARENTENA para el scope del token.

    Si empresa_id se especifica, filtra por esa empresa (verifica scope).
    """
    ts = verificar_token_servicio(request)
    sf = request.app.state.sesion_factory
    with sf() as s:
        if empresa_id is not None:
            _verificar_scope(ts, empresa_id, s)
            ids_filtro = [empresa_id]
        else:
            ids_filtro = _empresas_en_scope(ts, s)

        if not ids_filtro:
            return {"total": 0, "items": []}

        base_q = (
            select(ColaProcesamiento)
            .where(
                ColaProcesamiento.empresa_id.in_(ids_filtro),
                ColaProcesamiento.estado.in_(["PENDIENTE", "CUARENTENA"]),
            )
            .order_by(ColaProcesamiento.created_at)
        )
        total = s.scalar(
            select(func.count()).select_from(base_q.subquery())
        ) or 0
        items = s.scalars(base_q.offset(offset).limit(limit)).all()

        return {
            "total": total,
            "items": [
                {
                    "cola_id": c.id,
                    "documento_id": c.documento_id,
                    "empresa_id": c.empresa_id,
                    "nombre_archivo": c.nombre_archivo,
                    "estado": c.estado,
                    "trust_level": c.trust_level,
                    "score_final": c.score_final,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                }
                for c in items
            ],
        }


@router.get("/sync-status")
def sync_status(request: Request):
    """Resumen de contadores por empresa en el scope del token.

    Útil para que el pipeline local sepa el estado de la cola antes de subir.
    """
    ts = verificar_token_servicio(request)
    sf = request.app.state.sesion_factory
    with sf() as s:
        ids_filtro = _empresas_en_scope(ts, s)
        if not ids_filtro:
            return []

        # Contar por empresa y estado en una sola query
        filas = s.execute(
            select(
                ColaProcesamiento.empresa_id,
                ColaProcesamiento.estado,
                func.count().label("n"),
            )
            .where(ColaProcesamiento.empresa_id.in_(ids_filtro))
            .group_by(ColaProcesamiento.empresa_id, ColaProcesamiento.estado)
        ).all()

        # Agregar por empresa
        por_empresa: dict[int, dict] = {}
        for empresa_id_row, estado, n in filas:
            if empresa_id_row not in por_empresa:
                por_empresa[empresa_id_row] = {
                    "empresa_id": empresa_id_row,
                    "pendiente": 0,
                    "procesando": 0,
                    "ok": 0,
                    "cuarentena": 0,
                    "error": 0,
                }
            estado_lower = estado.lower()
            if estado_lower in por_empresa[empresa_id_row]:
                por_empresa[empresa_id_row][estado_lower] += n

        # Asegurar que empresas sin docs también aparezcan
        for eid in ids_filtro:
            if eid not in por_empresa:
                por_empresa[eid] = {
                    "empresa_id": eid,
                    "pendiente": 0,
                    "procesando": 0,
                    "ok": 0,
                    "cuarentena": 0,
                    "error": 0,
                }

        return list(por_empresa.values())
