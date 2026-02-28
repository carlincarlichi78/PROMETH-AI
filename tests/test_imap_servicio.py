"""Tests del conector IMAP — usa mock para no necesitar servidor real."""
import email
from email.mime.text import MIMEText
from unittest.mock import MagicMock, patch
import pytest


def _email_de_prueba(remitente: str, asunto: str) -> bytes:
    msg = MIMEText("Cuerpo del email de prueba")
    msg["From"] = remitente
    msg["To"] = "gestor@migestoria.com"
    msg["Subject"] = asunto
    msg["Message-ID"] = f"<test-{asunto}@test>"
    return msg.as_bytes()


@pytest.fixture
def config_imap():
    return {
        "servidor": "imap.gmail.com",
        "puerto": 993,
        "ssl": True,
        "usuario": "test@gmail.com",
        "contrasena": "secreto",
        "carpeta": "INBOX",
    }


def test_descargar_emails_nuevos_desde_uid(config_imap):
    """Descarga solo emails con UID > ultimo_uid."""
    from sfce.conectores.correo.imap_servicio import ImapServicio
    svc = ImapServicio(**config_imap)
    with patch.object(svc, "_conectar"), patch.object(svc, "_desconectar"):
        svc._conn = MagicMock()
        svc._conn.search.return_value = [b"3", b"4", b"5"]
        svc._conn.fetch.return_value = {
            b"3": {b"RFC822": _email_de_prueba("facturas@iberdrola.es", "Factura Enero")},
            b"4": {b"RFC822": _email_de_prueba("info@aeat.es", "Notificacion")},
            b"5": {b"RFC822": _email_de_prueba("proveedor@empresa.com", "Fra. 2025-001")},
        }
        emails = svc.descargar_nuevos(ultimo_uid=2)
    assert len(emails) == 3
    assert emails[0]["uid"] == "3"
    assert emails[0]["remitente"] == "facturas@iberdrola.es"
    assert emails[1]["asunto"] == "Notificacion"


def test_retorna_lista_vacia_si_no_hay_nuevos(config_imap):
    """Si search no devuelve UIDs, retorna lista vacía."""
    from sfce.conectores.correo.imap_servicio import ImapServicio
    svc = ImapServicio(**config_imap)
    with patch.object(svc, "_conectar"), patch.object(svc, "_desconectar"):
        svc._conn = MagicMock()
        svc._conn.search.return_value = []
        emails = svc.descargar_nuevos(ultimo_uid=99)
    assert emails == []


def test_parsea_adjunto(config_imap):
    """Emails con adjunto PDF se parsean correctamente."""
    from email.mime.multipart import MIMEMultipart
    from email.mime.application import MIMEApplication
    from sfce.conectores.correo.imap_servicio import ImapServicio

    msg = MIMEMultipart()
    msg["From"] = "proveedor@test.com"
    msg["Subject"] = "Factura con adjunto"
    msg["Message-ID"] = "<adj@test>"
    parte = MIMEApplication(b"%PDF-adjunto", Name="factura.pdf")
    parte["Content-Disposition"] = 'attachment; filename="factura.pdf"'
    msg.attach(parte)
    raw = msg.as_bytes()

    svc = ImapServicio(**config_imap)
    with patch.object(svc, "_conectar"), patch.object(svc, "_desconectar"):
        svc._conn = MagicMock()
        svc._conn.search.return_value = [b"10"]
        svc._conn.fetch.return_value = {b"10": {b"RFC822": raw}}
        emails = svc.descargar_nuevos(ultimo_uid=9)

    assert len(emails) == 1
    assert len(emails[0]["adjuntos"]) == 1
    assert emails[0]["adjuntos"][0]["nombre"] == "factura.pdf"
