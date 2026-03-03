"""Endpoints para gestión de colas de revisión de documentos."""
import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select

from sfce.api.app import get_sesion_factory
from sfce.api.auth import obtener_usuario_actual, verificar_acceso_empresa
from sfce.db.modelos import ColaProcesamiento, DocumentoTracking

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/colas", tags=["colas"])


@router.get("/revision")
def listar_cola_revision(
    request: Request,
    empresa_id: int,
    pagina: int = 1,
    limite: int = 20,
    sesion_factory=Depends(get_sesion_factory),
):
    """Cola de revisión del gestor: docs con decisión COLA_REVISION."""
    usuario = obtener_usuario_actual(request)
    if usuario.rol not in ("asesor", "admin_gestoria", "superadmin", "asesor_independiente"):
        raise HTTPException(status_code=403, detail="Se requiere rol de asesor o superior")
    offset = (pagina - 1) * limite
    with sesion_factory() as sesion:
        verificar_acceso_empresa(usuario, empresa_id, sesion)
        stmt = (
            select(ColaProcesamiento)
            .where(
                ColaProcesamiento.empresa_id == empresa_id,
                ColaProcesamiento.decision == "COLA_REVISION",
                ColaProcesamiento.estado.in_(["PENDIENTE", "PROCESANDO"]),
            )
            .order_by(ColaProcesamiento.created_at)
            .offset(offset)
            .limit(limite)
        )
        items = sesion.execute(stmt).scalars().all()

        stmt_total = select(ColaProcesamiento).where(
            ColaProcesamiento.empresa_id == empresa_id,
            ColaProcesamiento.decision == "COLA_REVISION",
            ColaProcesamiento.estado.in_(["PENDIENTE", "PROCESANDO"]),
        )
        total = len(sesion.execute(stmt_total).scalars().all())

        return {
            "items": [_serializar_item(i) for i in items],
            "total": total,
            "pagina": pagina,
        }


@router.get("/admin")
def listar_cola_admin(
    request: Request,
    empresa_id: int | None = None,
    sesion_factory=Depends(get_sesion_factory),
):
    """Cola de admin gestoría: docs escalados o score bajo."""
    usuario = obtener_usuario_actual(request)
    if usuario.rol not in ("admin_gestoria", "superadmin"):
        raise HTTPException(status_code=403, detail="Solo admin gestoría o superadmin")
    with sesion_factory() as sesion:
        stmt = select(ColaProcesamiento).where(
            ColaProcesamiento.decision == "COLA_ADMIN",
            ColaProcesamiento.estado.in_(["PENDIENTE", "PROCESANDO"]),
        )
        if empresa_id:
            stmt = stmt.where(ColaProcesamiento.empresa_id == empresa_id)
        items = sesion.execute(stmt).scalars().all()
        return {"items": [_serializar_item(i) for i in items]}


class RechazarRequest(BaseModel):
    motivo: str = ""


class AprobarConCorreccionRequest(BaseModel):
    campos_corregidos: dict = {}
    emisor_cif: str = ""


@router.post("/{item_id}/aprobar")
def aprobar_item(
    item_id: int,
    request: Request,
    datos: AprobarConCorreccionRequest = AprobarConCorreccionRequest(),
    sesion_factory=Depends(get_sesion_factory),
):
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as sesion:
        item = sesion.get(ColaProcesamiento, item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Item no encontrado")

        # Si el gestor corrigió campos → generar/actualizar Supplier Rule
        if datos.campos_corregidos and datos.emisor_cif:
            try:
                from sfce.core.supplier_rules import upsert_regla_desde_correccion
                upsert_regla_desde_correccion(
                    empresa_id=item.empresa_id,
                    emisor_cif=datos.emisor_cif,
                    campos_corregidos=datos.campos_corregidos,
                    sesion=sesion,
                )
            except Exception:
                logger.warning("No se pudo actualizar Supplier Rule")

        item.estado = "APROBADO"
        item.decision = "AUTO_PUBLICADO"
        _registrar_tracking(sesion, item.id, "APROBADO", actor=usuario.email)
        sesion.commit()
        sesion.refresh(item)
        return _serializar_item(item)


@router.post("/{item_id}/rechazar")
def rechazar_item(
    item_id: int,
    datos: RechazarRequest,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as sesion:
        item = sesion.get(ColaProcesamiento, item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Item no encontrado")

        item.estado = "RECHAZADO"
        hints = json.loads(item.hints_json or "{}")
        hints["motivo_rechazo"] = datos.motivo
        item.hints_json = json.dumps(hints)
        _registrar_tracking(
            sesion, item.id, "RECHAZADO",
            actor=usuario.email,
            detalle={"motivo": datos.motivo},
        )
        sesion.commit()
        sesion.refresh(item)
        return _serializar_item(item)


@router.post("/{item_id}/escalar")
def escalar_item(
    item_id: int,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    """Escala un item de cola gestor → cola admin gestoría."""
    usuario = obtener_usuario_actual(request)
    with sesion_factory() as sesion:
        item = sesion.get(ColaProcesamiento, item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Item no encontrado")
        item.decision = "COLA_ADMIN"
        _registrar_tracking(sesion, item.id, "ESCALADO", actor=usuario.email)
        sesion.commit()
        sesion.refresh(item)
        return _serializar_item(item)


@router.get("/documentos/{documento_id}/tracking")
def tracking_documento(
    documento_id: int,
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    """Historial de estados de un documento. Visible en portal y por gestor."""
    obtener_usuario_actual(request)  # verifica auth
    with sesion_factory() as sesion:
        # Verificar que el documento existe
        item = sesion.get(ColaProcesamiento, documento_id)
        if not item:
            raise HTTPException(status_code=404, detail="Documento no encontrado")

        estados = sesion.execute(
            select(DocumentoTracking)
            .where(DocumentoTracking.documento_id == documento_id)
            .order_by(DocumentoTracking.timestamp)
        ).scalars().all()

        return {
            "documento_id": documento_id,
            "nombre_archivo": item.nombre_archivo,
            "estados": [
                {
                    "estado": e.estado,
                    "timestamp": str(e.timestamp),
                    "actor": e.actor,
                }
                for e in estados
            ],
        }


def _serializar_item(item: ColaProcesamiento) -> dict:
    return {
        "id": item.id,
        "empresa_id": item.empresa_id,
        "nombre_archivo": item.nombre_archivo,
        "estado": item.estado,
        "trust_level": item.trust_level,
        "score_final": item.score_final,
        "decision": item.decision,
        "created_at": str(item.created_at),
    }


def _registrar_tracking(
    sesion,
    item_id: int,
    estado: str,
    actor: str = "sistema",
    detalle: dict | None = None,
) -> None:
    sesion.add(DocumentoTracking(
        documento_id=item_id,
        estado=estado,
        timestamp=datetime.utcnow(),
        actor=actor,
        detalle_json=json.dumps(detalle or {}),
    ))
