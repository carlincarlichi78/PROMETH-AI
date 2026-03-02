"""Tests de integración: email → extracción → score → ColaProcesamiento."""
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from sfce.db.base import Base
import sfce.db.modelos
import sfce.db.modelos_auth
from sfce.db.modelos import Empresa, CuentaCorreo, ColaProcesamiento, EmailProcesado

PDF_VALIDO = b"%PDF-1.4 contenido de prueba"


@pytest.fixture
def engine():
    e = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(e)
    return e


@pytest.fixture
def sesion(engine):
    with Session(engine) as s:
        empresa = Empresa(id=1, nombre="Pastorino SL", cif="B12345678",
                          forma_juridica="sl", config_extra={"slug": "pastorino"})
        cuenta = CuentaCorreo(
            id=1, empresa_id=1, nombre="Buzon", protocolo="imap",
            servidor="imap.test.es", usuario="docs@test.es", activa=True,
        )
        s.add_all([empresa, cuenta])
        s.commit()
    return Session(engine)


def test_email_con_pdf_encola_en_cola_procesamiento(sesion, tmp_path):
    """Email con PDF adjunto → aparece en cola_procesamiento."""
    from sfce.conectores.correo.ingesta_correo import IngestaCorreo

    emails_mock = [{
        "uid": "1",
        "remitente": "proveedor@empresa.es",
        "asunto": "Factura enero",
        "fecha": "2025-01-15",
        "message_id": "<test@test>",
        "adjuntos": [{"nombre": "factura.pdf", "contenido": PDF_VALIDO,
                      "mime_type": "application/pdf", "datos_bytes": PDF_VALIDO}],
        "cuerpo_texto": "",
        "cuerpo_html": None,
        "to": "pastorino@prometh-ai.es",
        "dkim_verificado": False,
    }]

    with patch.object(IngestaCorreo, "_descargar_emails_cuenta", return_value=emails_mock):
        ingesta = IngestaCorreo(engine=sesion.get_bind(), directorio_adjuntos=str(tmp_path))
        ingesta.procesar_cuenta(cuenta_id=1)

    items = sesion.execute(select(ColaProcesamiento)).scalars().all()
    assert len(items) == 1
    assert items[0].empresa_id == 1


def test_email_respuesta_automatica_se_ignora(sesion, tmp_path):
    """Email con asunto 'Re: ...' no se encola."""
    from sfce.conectores.correo.ingesta_correo import IngestaCorreo

    emails_mock = [{
        "uid": "2",
        "remitente": "auto@empresa.es",
        "asunto": "Re: Recibido",
        "fecha": "2025-01-15",
        "message_id": "<auto@test>",
        "adjuntos": [{"nombre": "doc.pdf", "contenido": PDF_VALIDO,
                      "mime_type": "application/pdf", "datos_bytes": PDF_VALIDO}],
        "cuerpo_texto": "",
        "cuerpo_html": None,
        "to": "pastorino@prometh-ai.es",
        "dkim_verificado": False,
    }]

    with patch.object(IngestaCorreo, "_descargar_emails_cuenta", return_value=emails_mock):
        ingesta = IngestaCorreo(engine=sesion.get_bind(), directorio_adjuntos=str(tmp_path))
        ingesta.procesar_cuenta(cuenta_id=1)

    email_bd = sesion.execute(select(EmailProcesado)).scalar_one_or_none()
    assert email_bd is not None
    assert email_bd.es_respuesta_ack is True
    assert email_bd.estado == "IGNORADO"

    items = sesion.execute(select(ColaProcesamiento)).scalars().all()
    assert len(items) == 0


def test_score_bajo_va_a_cuarentena(sesion, tmp_path):
    """Score < umbral → email en cuarentena, no en cola."""
    from sfce.conectores.correo.ingesta_correo import IngestaCorreo

    emails_mock = [{
        "uid": "3",
        "remitente": "sospechoso@spam.io",
        "asunto": "Urgente",
        "fecha": "2025-01-16",
        "message_id": "<spam@test>",
        "adjuntos": [{"nombre": "aaaaaa.pdf", "contenido": PDF_VALIDO,
                      "mime_type": "application/pdf", "datos_bytes": PDF_VALIDO}],
        "cuerpo_texto": "",
        "cuerpo_html": None,
        "to": "pastorino@prometh-ai.es",
        "dkim_verificado": False,
    }]

    with patch.object(IngestaCorreo, "_descargar_emails_cuenta", return_value=emails_mock), \
         patch("sfce.conectores.correo.ingesta_correo.calcular_score_email",
               return_value=(0.1, {})):
        ingesta = IngestaCorreo(engine=sesion.get_bind(), directorio_adjuntos=str(tmp_path))
        ingesta.procesar_cuenta(cuenta_id=1)

    email_bd = sesion.execute(select(EmailProcesado)).scalar_one_or_none()
    assert email_bd.estado == "CUARENTENA"

    items = sesion.execute(select(ColaProcesamiento)).scalars().all()
    assert len(items) == 0
