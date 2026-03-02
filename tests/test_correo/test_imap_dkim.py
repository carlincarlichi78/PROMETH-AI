import email
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from sfce.conectores.correo.imap_servicio import ImapServicio


def _hacer_email_con_dkim(dkim_pass: bool) -> bytes:
    msg = MIMEMultipart()
    msg["From"] = "proveedor@empresa.es"
    msg["To"] = "gestoria@prometh-ai.es"
    msg["Subject"] = "Factura enero"
    if dkim_pass:
        msg["Authentication-Results"] = "mx.google.com; dkim=pass header.i=@empresa.es"
    else:
        msg["Authentication-Results"] = "mx.google.com; dkim=fail"
    msg.attach(MIMEText("Adjunto factura", "plain"))
    return msg.as_bytes()


def _hacer_email_con_eml_adjunto() -> bytes:
    """Email cuyo adjunto es un .eml que contiene un PDF."""
    inner = MIMEMultipart()
    inner["From"] = "cliente@empresa.es"
    inner["Subject"] = "factura"
    pdf_part = MIMEBase("application", "pdf")
    pdf_part.set_payload(b"%PDF-1.4 contenido_fake")
    pdf_part.add_header("Content-Disposition", 'attachment; filename="factura.pdf"')
    inner.attach(pdf_part)

    outer = MIMEMultipart()
    outer["From"] = "gestor@gestoria.es"
    outer["Subject"] = "reenvio factura cliente"
    eml_part = MIMEBase("message", "rfc822")
    eml_part.set_payload(inner.as_bytes())
    eml_part.add_header("Content-Disposition", 'attachment; filename="factura_cliente.eml"')
    outer.attach(eml_part)
    return outer.as_bytes()


def test_parsear_dkim_pass():
    raw = _hacer_email_con_dkim(dkim_pass=True)
    servicio = ImapServicio.__new__(ImapServicio)  # sin __init__
    resultado = servicio._parsear_email(b"1", {b"1": {b"RFC822": raw}})
    assert resultado["dkim_verificado"] is True


def test_parsear_dkim_fail():
    raw = _hacer_email_con_dkim(dkim_pass=False)
    servicio = ImapServicio.__new__(ImapServicio)
    resultado = servicio._parsear_email(b"1", {b"1": {b"RFC822": raw}})
    assert resultado["dkim_verificado"] is False


def test_extraer_adjuntos_de_eml():
    from sfce.conectores.correo.extractor_adjuntos import extraer_adjuntos
    raw = _hacer_email_con_eml_adjunto()
    msg = email.message_from_bytes(raw)
    adjuntos = extraer_adjuntos(msg)
    nombres = [a.nombre for a in adjuntos]
    assert "factura.pdf" in nombres
