"""Servicio de notificaciones push via Expo Push API."""
import logging
from typing import Optional
import requests

logger = logging.getLogger(__name__)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


def enviar_push(
    tokens: list[str],
    titulo: str,
    cuerpo: str,
    datos: Optional[dict] = None,
) -> bool:
    """
    Envía notificación push a una lista de tokens Expo.
    Retorna True si al menos un envío fue exitoso.
    Solo envía tokens que empiecen por 'ExponentPushToken'.
    """
    tokens_validos = [t for t in tokens if t.startswith("ExponentPushToken")]
    if not tokens_validos:
        return False

    mensajes = [
        {
            "to": token,
            "title": titulo,
            "body": cuerpo,
            "data": datos or {},
            "sound": "default",
        }
        for token in tokens_validos
    ]

    try:
        resp = requests.post(
            EXPO_PUSH_URL,
            json=mensajes,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        resp.raise_for_status()
        return True
    except Exception as exc:
        logger.error("Error enviando push: %s", exc)
        return False


def obtener_tokens_empresa(empresa_id: int, sesion) -> list[str]:
    """Obtiene tokens activos de todos los usuarios de una empresa."""
    from sqlalchemy import select
    from sfce.db.modelos import PushToken
    tokens = list(sesion.execute(
        select(PushToken.token)
        .where(PushToken.empresa_id == empresa_id)
        .where(PushToken.activo == True)  # noqa: E712
    ).scalars().all())
    return tokens
