"""Event store append-only — registra eventos analíticos del pipeline."""
import json
from datetime import date
from sqlalchemy.orm import Session
from sfce.analytics.modelos_analiticos import EventoAnalitico


def registrar(sesion: Session, empresa_id: int, tipo: str,
               fecha: date, payload: dict) -> int:
    evento = EventoAnalitico(
        empresa_id=empresa_id,
        tipo_evento=tipo,
        fecha_evento=fecha,
        payload=json.dumps(payload, ensure_ascii=False, default=str),
        procesado=False,
    )
    sesion.add(evento)
    sesion.flush()
    return evento.id
