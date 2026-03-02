import pytest
from sfce.conectores.correo.filtro_ack import es_respuesta_automatica, tiene_cabecera_ack


@pytest.mark.parametrize("asunto", [
    "Re: Recibido tu documento",
    "RE: Factura enero",
    "Automatic reply: Documentos",
    "Out of office: Vacaciones",
    "Respuesta automática: Recibido",
    "Auto-Reply: your message",
    "Delivery Status Notification",
    "Mailer-Daemon",
    "vacation auto-reply",
    "RESPUESTA AUTOMÁTICA",
])
def test_asunto_de_respuesta_detectado(asunto):
    assert es_respuesta_automatica(asunto) is True


@pytest.mark.parametrize("asunto", [
    "Factura enero 2025",
    "Documentos del mes",
    "Nómina febrero",
    "Extracto bancario",
    "",
])
def test_asunto_normal_no_detectado(asunto):
    assert es_respuesta_automatica(asunto) is False


def test_cabecera_ack_detectada():
    headers = {"X-SFCE-ACK": "true", "From": "noreply@prometh-ai.es"}
    assert tiene_cabecera_ack(headers) is True


def test_cabecera_ack_no_detectada():
    headers = {"From": "cliente@empresa.es", "Subject": "Factura"}
    assert tiene_cabecera_ack(headers) is False
