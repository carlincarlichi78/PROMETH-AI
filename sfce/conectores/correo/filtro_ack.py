"""Filtro de respuestas automáticas para prevenir loops de ACK."""
import re

_PATRONES_ACK = [
    r"^re\s*:",
    r"^automatic\s+reply",
    r"^out\s+of\s+office",
    r"^respuesta\s+autom",
    r"^auto\s*-?\s*reply",
    r"^delivery\s+status",
    r"^mailer.daemon",
    r"vacation\s+auto.reply",
    r"^resposta\s+autom",  # portugués
]
_RE_COMPILADOS = [re.compile(p, re.IGNORECASE) for p in _PATRONES_ACK]


def es_respuesta_automatica(asunto: str) -> bool:
    """True si el asunto indica que es una respuesta automática o rebote."""
    return any(r.search(asunto.strip()) for r in _RE_COMPILADOS)


def tiene_cabecera_ack(headers: dict) -> bool:
    """True si el email contiene la cabecera que ponen nuestros propios ACKs."""
    return headers.get("X-SFCE-ACK", "").lower() == "true"
