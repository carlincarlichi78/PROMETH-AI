"""Tests de integración del orquestador de ingesta de correo."""
import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session
import sfce.db.modelos_auth  # registra tabla gestorias en Base.metadata  # noqa: F401
from sfce.db.modelos import Base, CuentaCorreo, EmailProcesado


@pytest.fixture
def engine_test():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    return eng


def test_ingestar_email_nuevo_guarda_en_bd(engine_test):
    from sfce.conectores.correo.ingesta_correo import IngestaCorreo

    emails_mock = [
        {
            "uid": "5",
            "message_id": "<test@test>",
            "remitente": "facturas@iberdrola.es",
            "asunto": "Factura Enero",
            "fecha": "2025-01-15",
            "cuerpo_texto": "Total: 254.30 EUR",
            "cuerpo_html": "",
            "adjuntos": [],
        },
    ]
    reglas = [
        {
            "tipo": "REMITENTE_EXACTO",
            "activa": True,
            "condicion_json": '{"remitente": "facturas@iberdrola.es"}',
            "accion": "CLASIFICAR",
            "slug_destino": "pastorino",
            "prioridad": 10,
        }
    ]

    with Session(engine_test) as sesion:
        cuenta = CuentaCorreo(
            empresa_id=1,
            nombre="Test IMAP",
            protocolo="imap",
            servidor="imap.test.com",
            usuario="test@test.com",
        )
        sesion.add(cuenta)
        sesion.commit()
        cuenta_id = cuenta.id

    ingesta = IngestaCorreo(engine=engine_test)
    with patch.object(ingesta, "_descargar_emails_cuenta", return_value=emails_mock):
        with patch.object(ingesta, "_cargar_reglas", return_value=reglas):
            total = ingesta.procesar_cuenta(cuenta_id)

    assert total == 1

    with Session(engine_test) as sesion:
        emails = sesion.query(EmailProcesado).filter_by(cuenta_id=cuenta_id).all()
        assert len(emails) == 1
        assert emails[0].remitente == "facturas@iberdrola.es"
        assert emails[0].estado == "CLASIFICADO"
        assert emails[0].nivel_clasificacion == "REGLA"


def test_email_duplicado_no_se_procesa_dos_veces(engine_test):
    """Un email ya procesado (mismo uid) no se vuelve a insertar."""
    from sfce.conectores.correo.ingesta_correo import IngestaCorreo

    emails_mock = [
        {"uid": "3", "message_id": "<dup@test>", "remitente": "a@b.com",
         "asunto": "Test", "fecha": "2025-01-01", "cuerpo_texto": "",
         "cuerpo_html": "", "adjuntos": []},
    ]

    with Session(engine_test) as sesion:
        cuenta = CuentaCorreo(
            empresa_id=1, nombre="Dup", protocolo="imap",
            servidor="imap.test.com", usuario="x@y.com",
        )
        sesion.add(cuenta)
        sesion.commit()
        cuenta_id = cuenta.id

    ingesta = IngestaCorreo(engine=engine_test)
    with patch.object(ingesta, "_descargar_emails_cuenta", return_value=emails_mock):
        with patch.object(ingesta, "_cargar_reglas", return_value=[]):
            ingesta.procesar_cuenta(cuenta_id)
            total2 = ingesta.procesar_cuenta(cuenta_id)

    assert total2 == 0  # segunda vez: 0 nuevos


def test_cuenta_inactiva_retorna_cero(engine_test):
    from sfce.conectores.correo.ingesta_correo import IngestaCorreo

    with Session(engine_test) as sesion:
        cuenta = CuentaCorreo(
            empresa_id=1, nombre="Inactiva", protocolo="imap",
            servidor="imap.test.com", usuario="x@y.com", activa=False,
        )
        sesion.add(cuenta)
        sesion.commit()
        cuenta_id = cuenta.id

    ingesta = IngestaCorreo(engine=engine_test)
    total = ingesta.procesar_cuenta(cuenta_id)
    assert total == 0
