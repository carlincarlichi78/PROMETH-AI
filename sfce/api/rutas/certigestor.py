"""Webhook receiver para notificaciones de CertiGestor."""
import hashlib
import hmac
import json
import logging
import os

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from sfce.api.app import get_sesion_factory

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/certigestor", tags=["certigestor"])


def _verificar_firma_hmac(request_body: bytes, firma_recibida: str) -> bool:
    """Verifica la firma HMAC-SHA256 del cuerpo del request."""
    secreto = os.getenv("CERTIGESTOR_WEBHOOK_SECRET", "")
    if not secreto:
        logger.error("CERTIGESTOR_WEBHOOK_SECRET no configurado")
        return False
    firma_esperada = hmac.new(secreto.encode(), request_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(firma_esperada, firma_recibida)


class PayloadNotificacion(BaseModel):
    empresa_cif: str
    organismo: str = "DESCONOCIDO"
    tipo: str
    descripcion: str
    fecha_limite: str | None = None
    url_documento: str | None = None


@router.post("/webhook")
async def recibir_notificacion(
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
):
    """Recibe notificaciones AAPP desde CertiGestor via HMAC-SHA256."""
    cuerpo = await request.body()
    firma = request.headers.get("X-CertiGestor-Signature", "")
    if not firma or not _verificar_firma_hmac(cuerpo, firma):
        raise HTTPException(status_code=401, detail="Firma invalida o ausente")

    payload = PayloadNotificacion(**json.loads(cuerpo))

    with sesion_factory() as sesion:
        from sfce.db.modelos import Empresa
        empresa = sesion.query(Empresa).filter_by(cif=payload.empresa_cif).first()
        if not empresa:
            logger.warning("Notificacion para CIF desconocido: %s", payload.empresa_cif)
            return {"guardado": False, "motivo": "CIF no encontrado"}

        from sfce.core.certificados_aapp import ServicioNotificaciones
        svc = ServicioNotificaciones(sesion)
        notif = svc.registrar(
            empresa_id=empresa.id,
            organismo=payload.organismo,
            asunto=payload.descripcion,
            tipo=payload.tipo,
            fecha_limite=payload.fecha_limite,
            url_documento=payload.url_documento,
            origen="certigestor",
        )
        logger.info(
            "Notificacion AAPP guardada: %s para empresa %s",
            payload.tipo,
            empresa.id,
        )
        return {"guardado": True, "notificacion_id": notif.id, "empresa_id": empresa.id}
