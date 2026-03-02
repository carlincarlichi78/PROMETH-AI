"""Tests G4/G10: slug desconocido → cuarentena en BD, no descarte silencioso."""
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from sfce.db.base import Base
import sfce.db.modelos
import sfce.db.modelos_auth
from sfce.db.modelos import EmailProcesado
from sfce.conectores.correo.worker_catchall import procesar_email_catchall


def _motor():
    e = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(e)
    return e


def _email_data(to: str, adjuntos: list | None = None):
    return {
        "uid": "99",
        "to": to,
        "from": "proveedor@empresa.es",
        "subject": "Factura enero",
        "cuerpo_texto": "adjunto factura",
        "cuerpo_html": "",
        "dkim_verificado": False,
        "adjuntos": adjuntos or [],
    }


def test_slug_desconocido_guarda_en_bd_como_cuarentena():
    """G4/G10: slug desconocido no descarta, guarda EmailProcesado CUARENTENA."""
    engine = _motor()
    email_data = _email_data("docs+sluginexistente+fv@prometh-ai.es")

    with Session(engine) as s:
        resultado = procesar_email_catchall(email_data, s)

    assert resultado.get("motivo") == "slug_desconocido"
    with Session(engine) as s:
        emails = s.execute(select(EmailProcesado)).scalars().all()
    assert len(emails) == 1
    assert emails[0].estado == "CUARENTENA"


def test_slug_desconocido_no_pierde_informacion():
    engine = _motor()
    email_data = _email_data("docs+empresainexistente+fc@prometh-ai.es")

    with Session(engine) as s:
        procesar_email_catchall(email_data, s)

    with Session(engine) as s:
        ep = s.execute(select(EmailProcesado)).scalar_one()
    assert ep.remitente == "proveedor@empresa.es"
    assert ep.asunto == "Factura enero"
