"""Tests para detección y enrutamiento de emails reenviados entre asesores."""
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from sfce.db.base import Base
import sfce.db.modelos
import sfce.db.modelos_auth
from sfce.db.modelos import Empresa, CuentaCorreo, EmailProcesado, RemitenteAutorizado
from sfce.db.modelos_auth import Usuario, Gestoria


# ── fixtures ─────────────────────────────────────────────────────────────────

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
    """BD con gestoría Uralde, 2 empresas, 2 asesores."""
    with Session(engine) as s:
        gestoria = Gestoria(
            id=1, nombre="Uralde", email_contacto="sergio@prometh-ai.es",
            plan_tier="basico",
        )
        empresa_gerardo = Empresa(
            id=1, nombre="Gerardo González", cif="A12345678",
            forma_juridica="autonomo", gestoria_id=1,
        )
        empresa_pastorino = Empresa(
            id=2, nombre="Pastorino SL", cif="B87654321",
            forma_juridica="sl", gestoria_id=1,
        )
        # Asesores de la gestoría
        maria = Usuario(
            id=1, email="maria@prometh-ai.es", nombre="Maria",
            hash_password="x", rol="asesor", gestoria_id=1, activo=True,
            empresas_asignadas=[1],
        )
        francisco = Usuario(
            id=2, email="francisco@prometh-ai.es", nombre="Francisco",
            hash_password="x", rol="asesor", gestoria_id=1, activo=True,
            empresas_asignadas=[2],
        )
        # Cuenta dedicada de Francisco → Pastorino
        cuenta_francisco = CuentaCorreo(
            id=1, empresa_id=2, gestoria_id=1,
            nombre="Francisco", protocolo="imap",
            servidor="imap.google.com", usuario="francisco@prometh-ai.es",
            tipo_cuenta="dedicada", activa=True,
        )
        # Whitelist: cliente de Gerardo autorizado en empresa 1
        remitente_gerardo = RemitenteAutorizado(
            id=1, empresa_id=1, email="cliente@gerardo.es", activo=True,
        )
        s.add_all([
            gestoria, empresa_gerardo, empresa_pastorino,
            maria, francisco, cuenta_francisco, remitente_gerardo,
        ])
        s.commit()
    return engine


PDF_VALIDO = b"%PDF-1.4 contenido de prueba"

CUERPO_FORWARD_GMAIL = """\
Hola Francisco, te reenvío esta factura de Gerardo.

---------- Forwarded message ---------
From: cliente@gerardo.es <cliente@gerardo.es>
Date: Mon, 10 Feb 2025 09:00:00 +0100
Subject: Factura enero
To: maria@prometh-ai.es

Ver adjunto.
"""

CUERPO_FORWARD_OUTLOOK = """\
Fwd: factura enero

-----Original Message-----
From: cliente@gerardo.es
Sent: Monday, February 10, 2025 9:00 AM
To: maria@prometh-ai.es
Subject: Factura enero
"""

CUERPO_FORWARD_SIMPLE = """\
Te mando esto.

From: cliente@gerardo.es <cliente@gerardo.es>
Subject: Factura enero
"""

CUERPO_SIN_FORWARD = """\
Buenos días,
Adjunto factura de enero.
Saludos
"""


# ── Tests: extraer_remitente_reenviado ────────────────────────────────────────

class TestExtraerRemitenteReenviado:
    """Parsear el remitente original de un email reenviado."""

    def test_detecta_formato_gmail(self):
        from sfce.conectores.correo.reenvio import extraer_remitente_reenviado
        resultado = extraer_remitente_reenviado(CUERPO_FORWARD_GMAIL)
        assert resultado == "cliente@gerardo.es"

    def test_detecta_formato_outlook(self):
        from sfce.conectores.correo.reenvio import extraer_remitente_reenviado
        resultado = extraer_remitente_reenviado(CUERPO_FORWARD_OUTLOOK)
        assert resultado == "cliente@gerardo.es"

    def test_detecta_formato_simple_from(self):
        from sfce.conectores.correo.reenvio import extraer_remitente_reenviado
        resultado = extraer_remitente_reenviado(CUERPO_FORWARD_SIMPLE)
        assert resultado == "cliente@gerardo.es"

    def test_retorna_none_sin_forward(self):
        from sfce.conectores.correo.reenvio import extraer_remitente_reenviado
        resultado = extraer_remitente_reenviado(CUERPO_SIN_FORWARD)
        assert resultado is None

    def test_retorna_none_con_cuerpo_vacio(self):
        from sfce.conectores.correo.reenvio import extraer_remitente_reenviado
        assert extraer_remitente_reenviado("") is None

    def test_no_extrae_el_remitente_que_reenvio(self):
        """El From: que envió el forward (maria@) no debe ser el resultado."""
        from sfce.conectores.correo.reenvio import extraer_remitente_reenviado
        cuerpo = CUERPO_FORWARD_GMAIL
        resultado = extraer_remitente_reenviado(cuerpo)
        assert resultado != "maria@prometh-ai.es"


# ── Tests: es_asesor_gestoria ─────────────────────────────────────────────────

class TestEsAsesorGestoria:
    """Detectar si un email pertenece a un asesor de la gestoría."""

    def test_email_asesor_retorna_true(self, sesion):
        from sfce.conectores.correo.reenvio import es_asesor_gestoria
        with Session(sesion) as s:
            assert es_asesor_gestoria("maria@prometh-ai.es", gestoria_id=1, sesion=s) is True

    def test_email_externo_retorna_false(self, sesion):
        from sfce.conectores.correo.reenvio import es_asesor_gestoria
        with Session(sesion) as s:
            assert es_asesor_gestoria("cliente@gerardo.es", gestoria_id=1, sesion=s) is False

    def test_asesor_de_otra_gestoria_retorna_false(self, sesion):
        """Un asesor de gestoria_id=2 no debe detectarse en gestoria_id=1."""
        from sfce.conectores.correo.reenvio import es_asesor_gestoria
        with Session(sesion) as s:
            assert es_asesor_gestoria("maria@prometh-ai.es", gestoria_id=2, sesion=s) is False

    def test_usuario_inactivo_retorna_false(self, sesion):
        from sfce.conectores.correo.reenvio import es_asesor_gestoria
        with Session(sesion) as s:
            # Desactivar maria
            maria = s.get(Usuario, 1)
            maria.activo = False
            s.commit()
            assert es_asesor_gestoria("maria@prometh-ai.es", gestoria_id=1, sesion=s) is False


# ── Tests: resolver_empresa_reenvio ──────────────────────────────────────────

class TestResolverEmpresaReenvio:
    """Determinar empresa destino buscando remitente original en whitelists."""

    def test_remitente_original_en_whitelist_retorna_empresa(self, sesion):
        from sfce.conectores.correo.reenvio import resolver_empresa_reenvio
        with Session(sesion) as s:
            # cliente@gerardo.es está en whitelist de empresa_id=1 (Gerardo)
            resultado = resolver_empresa_reenvio(
                "cliente@gerardo.es", empresas_ids=[1, 2], sesion=s
            )
        assert resultado == 1

    def test_remitente_original_sin_whitelist_retorna_none(self, sesion):
        from sfce.conectores.correo.reenvio import resolver_empresa_reenvio
        with Session(sesion) as s:
            resultado = resolver_empresa_reenvio(
                "desconocido@nadie.es", empresas_ids=[1, 2], sesion=s
            )
        assert resultado is None

    def test_remitente_en_multiples_empresas_retorna_none(self, sesion):
        """Ambigüedad: remitente en 2 whitelists → no se puede decidir."""
        from sfce.conectores.correo.reenvio import resolver_empresa_reenvio
        with Session(sesion) as s:
            # Añadir mismo email en whitelist de empresa 2 también
            s.add(RemitenteAutorizado(empresa_id=2, email="cliente@gerardo.es", activo=True))
            s.commit()
            resultado = resolver_empresa_reenvio(
                "cliente@gerardo.es", empresas_ids=[1, 2], sesion=s
            )
        assert resultado is None


# ── Tests: integración ingesta con forwarding ─────────────────────────────────

class TestIngestaForwarding:
    """Email reenviado por asesor → enruta a la empresa correcta."""

    def _email_reenviado(self, uid="10"):
        return {
            "uid": uid,
            "remitente": "maria@prometh-ai.es",  # maria reenvía
            "asunto": "Fwd: Factura enero",
            "fecha": "2025-02-10",
            "message_id": f"<fwd{uid}@test>",
            "adjuntos": [{"nombre": "factura.pdf", "datos_bytes": PDF_VALIDO,
                          "mime_type": "application/pdf"}],
            "cuerpo_texto": CUERPO_FORWARD_GMAIL,
            "cuerpo_html": None,
            "dkim_verificado": True,
        }

    def test_email_reenviado_enruta_a_empresa_de_cliente_original(self, sesion, tmp_path):
        """Factura de cliente@gerardo.es reenviada por maria → empresa Gerardo (id=1)."""
        from sfce.conectores.correo.ingesta_correo import IngestaCorreo
        from sfce.db.modelos import ColaProcesamiento

        email_data = self._email_reenviado()
        with patch.object(IngestaCorreo, "_descargar_emails_cuenta", return_value=[email_data]):
            ingesta = IngestaCorreo(engine=sesion, directorio_adjuntos=str(tmp_path))
            ingesta.procesar_cuenta(cuenta_id=1)  # cuenta de Francisco → Pastorino

        with Session(sesion) as s:
            email_bd = s.execute(
                __import__("sqlalchemy", fromlist=["select"]).select(EmailProcesado)
            ).scalar_one_or_none()
            # El email debe enrutarse a empresa 1 (Gerardo), no a empresa 2 (Pastorino)
            assert email_bd is not None
            assert email_bd.empresa_destino_id == 1, (
                f"Se esperaba empresa_id=1 (Gerardo) pero se obtuvo {email_bd.empresa_destino_id}"
            )

    def test_email_reenviado_sin_parsear_va_a_revision(self, sesion, tmp_path):
        """Maria reenvía pero el cuerpo no tiene el formato estándar → REVISION."""
        from sfce.conectores.correo.ingesta_correo import IngestaCorreo

        email_data = {
            **self._email_reenviado(uid="11"),
            "cuerpo_texto": "Te mando esto. Saludos.",  # sin forward header
        }
        with patch.object(IngestaCorreo, "_descargar_emails_cuenta", return_value=[email_data]):
            ingesta = IngestaCorreo(engine=sesion, directorio_adjuntos=str(tmp_path))
            ingesta.procesar_cuenta(cuenta_id=1)

        with Session(sesion) as s:
            email_bd = s.execute(
                __import__("sqlalchemy", fromlist=["select"]).select(EmailProcesado)
            ).scalar_one_or_none()
            assert email_bd is not None
            assert email_bd.motivo_cuarentena == "REENVIO_SIN_REMITENTE"

    def test_email_directo_no_afectado_por_logica_reenvio(self, sesion, tmp_path):
        """Email normal (no reenvío) sigue el flujo habitual."""
        from sfce.conectores.correo.ingesta_correo import IngestaCorreo

        email_data = {
            "uid": "12",
            "remitente": "proveedor@empresa.es",  # externo, no asesor
            "asunto": "Factura enero",
            "fecha": "2025-02-10",
            "message_id": "<normal@test>",
            "adjuntos": [{"nombre": "factura.pdf", "datos_bytes": PDF_VALIDO,
                          "mime_type": "application/pdf"}],
            "cuerpo_texto": CUERPO_SIN_FORWARD,
            "cuerpo_html": None,
            "dkim_verificado": True,
        }
        with patch.object(IngestaCorreo, "_descargar_emails_cuenta", return_value=[email_data]):
            ingesta = IngestaCorreo(engine=sesion, directorio_adjuntos=str(tmp_path))
            ingesta.procesar_cuenta(cuenta_id=1)

        with Session(sesion) as s:
            email_bd = s.execute(
                __import__("sqlalchemy", fromlist=["select"]).select(EmailProcesado)
            ).scalar_one_or_none()
            # Email normal → empresa de la cuenta (Pastorino = 2)
            assert email_bd is not None
            assert email_bd.empresa_destino_id == 2


# ── Tests: fixes críticos ingesta ────────────────────────────────────────────

class TestFixesCriticosIngesta:
    """Bugs críticos identificados en la revisión."""

    def test_empresa_destino_id_asignado_en_cuentas_dedicadas(self, sesion, tmp_path):
        """empresa_destino_id debe ser empresa_id de la cuenta, no None."""
        from sfce.conectores.correo.ingesta_correo import IngestaCorreo

        email_data = {
            "uid": "20",
            "remitente": "proveedor@empresa.es",
            "asunto": "Factura",
            "fecha": "2025-01-10",
            "message_id": "<fix4@test>",
            "adjuntos": [],
            "cuerpo_texto": "",
            "cuerpo_html": None,
            "dkim_verificado": False,
        }
        with patch.object(IngestaCorreo, "_descargar_emails_cuenta", return_value=[email_data]):
            ingesta = IngestaCorreo(engine=sesion, directorio_adjuntos=str(tmp_path))
            ingesta.procesar_cuenta(cuenta_id=1)

        with Session(sesion) as s:
            email_bd = s.execute(
                __import__("sqlalchemy", fromlist=["select"]).select(EmailProcesado)
            ).scalar_one_or_none()
            # empresa_destino_id debe ser 2 (Pastorino, empresa de la cuenta)
            assert email_bd is not None
            assert email_bd.empresa_destino_id == 2, (
                f"empresa_destino_id era None (bug) o incorrecto: {email_bd.empresa_destino_id}"
            )

    def test_fallo_en_email_no_afecta_emails_anteriores_ya_guardados(self, sesion, tmp_path):
        """Atomicidad: si email N falla, los emails anteriores ya están commiteados."""
        from sfce.conectores.correo.ingesta_correo import IngestaCorreo

        emails_mock = [
            {
                "uid": "30",
                "remitente": "ok@empresa.es",
                "asunto": "OK",
                "fecha": "2025-01-10",
                "message_id": "<ok@test>",
                "adjuntos": [],
                "cuerpo_texto": "",
                "cuerpo_html": None,
                "dkim_verificado": False,
            },
            {
                "uid": "31",
                "remitente": "fallo@empresa.es",
                "asunto": "Este causa error",
                "fecha": "2025-01-10",
                "message_id": "<fail@test>",
                "adjuntos": [],
                "cuerpo_texto": "",
                "cuerpo_html": None,
                "dkim_verificado": False,
            },
        ]

        # El segundo email provoca un error en calcular_score_email
        call_count = 0
        original_calcular = None

        def score_con_fallo(email_data, empresa_id, sesion_arg):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("Error inesperado en el segundo email")
            return (0.9, {})

        with patch.object(IngestaCorreo, "_descargar_emails_cuenta", return_value=emails_mock), \
             patch("sfce.conectores.correo.ingesta_correo.calcular_score_email", side_effect=score_con_fallo):
            ingesta = IngestaCorreo(engine=sesion, directorio_adjuntos=str(tmp_path))
            ingesta.procesar_cuenta(cuenta_id=1)

        with Session(sesion) as s:
            from sqlalchemy import select
            emails_bd = s.execute(select(EmailProcesado)).scalars().all()
            # El email OK debe haberse guardado aunque el segundo fallara
            uids = [e.uid_servidor for e in emails_bd]
            assert "30" in uids, "El primer email debería haberse guardado (atomicidad por email)"
