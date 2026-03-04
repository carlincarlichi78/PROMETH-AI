"""Tests del routing tipo='asesor' en IngestaCorreo."""
import pytest
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sfce.db.modelos import CuentaCorreo, Empresa, EmailProcesado
from sfce.db.modelos_auth import Usuario, Gestoria
from sfce.conectores.correo.ingesta_correo import IngestaCorreo


def _crear_engine_con_tablas():
    eng = create_engine("sqlite:///:memory:", poolclass=StaticPool)
    from sfce.db.base import Base
    Base.metadata.create_all(eng)
    # Aplicar migración 028
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location(
        "m028",
        Path(__file__).parent.parent.parent / "sfce" / "db" / "migraciones" / "028_cuenta_correo_asesor.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.aplicar(eng)
    return eng


@pytest.fixture
def engine():
    return _crear_engine_con_tablas()


@pytest.fixture
def datos_base(engine):
    from sqlalchemy.orm import Session
    from sfce.core.cifrado import cifrar
    with Session(engine) as s:
        g = Gestoria(
            nombre="Uralde", email_contacto="admin@u.es", plan_tier="basico"
        )
        s.add(g)
        s.flush()
        e1 = Empresa(nombre="PASTORINO", cif="B12345678", gestoria_id=g.id, forma_juridica="sl")
        e2 = Empresa(nombre="GERARDO", cif="76638663H", gestoria_id=g.id, forma_juridica="autonomo")
        s.add_all([e1, e2])
        s.flush()
        u = Usuario(
            email="francisco@prometh-ai.es",
            nombre="Francisco",
            hash_password="x",
            rol="asesor",
            gestoria_id=g.id,
            activo=True,
            empresas_asignadas=[e1.id],
        )
        s.add(u)
        s.flush()
        cuenta = CuentaCorreo(
            nombre="IMAP Francisco",
            tipo_cuenta="asesor",
            usuario_id=u.id,
            servidor="imap.gmail.com",
            puerto=993,
            ssl=True,
            protocolo="imap",
            usuario="francisco@prometh-ai.es",
            contrasena_enc=cifrar("password"),
            activa=True,
            ultimo_uid=0,
        )
        s.add(cuenta)
        s.commit()
        return {
            "cuenta_id": cuenta.id,
            "empresa_id": e1.id,
            "empresa2_id": e2.id,
            "usuario_id": u.id,
        }


def _email_con_adjunto():
    return {
        "uid": "1001",
        "remitente": "proveedor@externo.es",
        "asunto": "Factura adjunta",
        "cuerpo_texto": "Por favor revise la factura adjunta.",
        "cuerpo_html": None,
        "fecha": "2025-01-15",
        "message_id": "<abc@ext.es>",
        "adjuntos": [{"nombre": "factura.pdf", "bytes": b"%PDF-1.4 test", "datos_bytes": b"%PDF-1.4 test"}],
        "headers": {},
    }


class TestRoutingAsesor:
    @patch("sfce.conectores.correo.ingesta_correo._extraer_cif_pdf")
    @patch.object(IngestaCorreo, "_descargar_emails_cuenta")
    def test_routing_por_cif_match(self, mock_dl, mock_cif, engine, datos_base):
        """Email con CIF que coincide → empresa_destino_id correcta."""
        mock_dl.return_value = [_email_con_adjunto()]
        mock_cif.return_value = ["B12345678"]
        ingesta = IngestaCorreo(engine)
        procesados = ingesta.procesar_cuenta(datos_base["cuenta_id"])
        assert procesados == 1
        from sqlalchemy.orm import Session
        with Session(engine) as s:
            email = s.query(EmailProcesado).first()
            assert email.empresa_destino_id == datos_base["empresa_id"]
            assert email.estado != "CUARENTENA"

    @patch("sfce.conectores.correo.ingesta_correo._extraer_cif_pdf")
    @patch.object(IngestaCorreo, "_descargar_emails_cuenta")
    def test_routing_sin_cif_va_cuarentena(self, mock_dl, mock_cif, engine, datos_base):
        """Sin CIF en PDF → cuarentena."""
        mock_dl.return_value = [_email_con_adjunto()]
        mock_cif.return_value = []
        ingesta = IngestaCorreo(engine)
        ingesta.procesar_cuenta(datos_base["cuenta_id"])
        from sqlalchemy.orm import Session
        with Session(engine) as s:
            email = s.query(EmailProcesado).first()
            assert email.estado == "CUARENTENA"
            assert email.empresa_destino_id is None

    @patch("sfce.conectores.correo.ingesta_correo._extraer_cif_pdf")
    @patch.object(IngestaCorreo, "_descargar_emails_cuenta")
    def test_cif_fuera_de_scope_va_cuarentena(self, mock_dl, mock_cif, engine, datos_base):
        """CIF de empresa no asignada al asesor → cuarentena."""
        mock_dl.return_value = [_email_con_adjunto()]
        mock_cif.return_value = ["76638663H"]  # GERARDO, no asignado a francisco
        ingesta = IngestaCorreo(engine)
        ingesta.procesar_cuenta(datos_base["cuenta_id"])
        from sqlalchemy.orm import Session
        with Session(engine) as s:
            email = s.query(EmailProcesado).first()
            assert email.estado == "CUARENTENA"
