"""Tests de integración del orquestador de ingesta de correo."""
import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine, select
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


# ---- Tests routing por gestoría ----
from sfce.db.modelos_auth import Gestoria


@pytest.fixture
def engine_gestoria(engine_test):
    """engine_test ya tiene Base.metadata.create_all — solo añadir gestorias."""
    import sfce.db.modelos_auth as _auth
    _auth.Base.metadata.create_all(engine_test)
    return engine_test


def test_procesar_cuenta_gestoria_enruta_por_remitente(engine_gestoria):
    """Email a buzón de gestoría se enruta a empresa correcta por regla de remitente."""
    from sfce.conectores.correo.ingesta_correo import IngestaCorreo
    from sfce.db.modelos import Empresa, ReglaClasificacionCorreo

    with Session(engine_gestoria) as s:
        gestoria = Gestoria(
            nombre="Gestoría Test",
            email_contacto="admin@gt.es",
            plan_asesores=1,
            plan_clientes_tramo="1-10",
        )
        s.add(gestoria)
        s.flush()
        gestoria_id = gestoria.id

        empresa = Empresa(
            nombre="Pastorino",
            cif="B12345678",
            gestoria_id=gestoria_id,
            forma_juridica="srl",
        )
        s.add(empresa)
        s.flush()
        empresa_id = empresa.id

        regla = ReglaClasificacionCorreo(
            empresa_id=empresa_id,
            tipo="REMITENTE_EXACTO",
            condicion_json='{"remitente": "facturas@proveedor.es"}',
            accion="CLASIFICAR",
            slug_destino="pastorino",
            prioridad=10,
            activa=True,
        )
        s.add(regla)

        cuenta = CuentaCorreo(
            gestoria_id=gestoria_id,
            tipo_cuenta="gestoria",
            nombre="Gestoría Test inbox",
            protocolo="imap",
            servidor="imap.zoho.eu",
            puerto=993,
            ssl=True,
            usuario="gestoriatest@prometh-ai.es",
        )
        s.add(cuenta)
        s.commit()
        cuenta_id = cuenta.id

    emails_mock = [{
        "uid": "10",
        "message_id": "<gestoria@test>",
        "remitente": "facturas@proveedor.es",
        "asunto": "Factura marzo",
        "fecha": "2026-03-01",
        "cuerpo_texto": "Total 500 EUR",
        "cuerpo_html": "",
        "adjuntos": [],
    }]

    ingesta = IngestaCorreo(engine=engine_gestoria)
    with patch.object(ingesta, "_descargar_emails_cuenta", return_value=emails_mock):
        procesados = ingesta.procesar_cuenta(cuenta_id)

    assert procesados == 1
    with Session(engine_gestoria) as s:
        email_bd = s.execute(
            select(EmailProcesado).where(EmailProcesado.cuenta_id == cuenta_id)
        ).scalar_one()
    assert email_bd.empresa_destino_id == empresa_id
    assert email_bd.estado == "CLASIFICADO"


def test_procesar_cuenta_gestoria_cuarentena_si_remitente_desconocido(engine_gestoria):
    """Remitente desconocido en cuenta gestoría va a CUARENTENA."""
    from sfce.conectores.correo.ingesta_correo import IngestaCorreo

    with Session(engine_gestoria) as s:
        gestoria = Gestoria(
            nombre="Gestoría2",
            email_contacto="g2@test.es",
            plan_asesores=1,
            plan_clientes_tramo="1-10",
        )
        s.add(gestoria)
        s.flush()
        cuenta = CuentaCorreo(
            gestoria_id=gestoria.id,
            tipo_cuenta="gestoria",
            nombre="G2 inbox",
            protocolo="imap",
            servidor="imap.zoho.eu",
            puerto=993,
            ssl=True,
            usuario="g2@prometh-ai.es",
        )
        s.add(cuenta)
        s.commit()
        cuenta_id = cuenta.id

    emails_mock = [{
        "uid": "1",
        "message_id": "<x@x>",
        "remitente": "desconocido@nowhere.com",
        "asunto": "doc",
        "fecha": "2026-03-01",
        "cuerpo_texto": "",
        "cuerpo_html": "",
        "adjuntos": [],
    }]

    ingesta = IngestaCorreo(engine=engine_gestoria)
    with patch.object(ingesta, "_descargar_emails_cuenta", return_value=emails_mock):
        ingesta.procesar_cuenta(cuenta_id)

    with Session(engine_gestoria) as s:
        email_bd = s.execute(
            select(EmailProcesado).where(EmailProcesado.cuenta_id == cuenta_id)
        ).scalar_one()
    assert email_bd.estado == "CUARENTENA"


def test_ejecutar_polling_omite_cuentas_sistema(engine_gestoria):
    """Cuentas tipo 'sistema' no se incluyen en el polling IMAP."""
    from sfce.conectores.correo.ingesta_correo import ejecutar_polling_todas_las_cuentas

    with Session(engine_gestoria) as s:
        cuenta_sistema = CuentaCorreo(
            tipo_cuenta="sistema",
            nombre="noreply",
            protocolo="imap",
            servidor="smtp.zoho.eu",
            puerto=993,
            ssl=True,
            usuario="noreply@prometh-ai.es",
            activa=True,
        )
        s.add(cuenta_sistema)
        s.commit()
        cuenta_id = cuenta_sistema.id

    ingesta_mock = MagicMock()
    with patch("sfce.conectores.correo.ingesta_correo.IngestaCorreo") as MockIngesta:
        MockIngesta.return_value = ingesta_mock
        ejecutar_polling_todas_las_cuentas(engine_gestoria)

    # procesar_cuenta nunca fue llamado con la cuenta sistema
    llamadas = [call.args[0] for call in ingesta_mock.procesar_cuenta.call_args_list]
    assert cuenta_id not in llamadas
