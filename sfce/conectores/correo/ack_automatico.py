"""ACK automático categorizado por motivo de cuarentena.

Regla de seguridad: NUNCA enviar ACK a REMITENTE_NO_AUTORIZADO
para no confirmar que la dirección existe.
"""
import logging
from sfce.core.email_service import obtener_servicio_email

logger = logging.getLogger(__name__)

# Motivos que NUNCA generan ACK (seguridad)
_MOTIVOS_SIN_ACK = {"REMITENTE_NO_AUTORIZADO"}

MOTIVOS_CON_ACK = {
    "recibido", "PDF_ILEGIBLE", "DUPLICADO", "FORMATO_NO_SOPORTADO",
    "ZIP_PROTEGIDO_SIN_CLAVE", "ZIP_DEMASIADO_GRANDE", "SIN_ADJUNTOS",
}

_TEMPLATES: dict[str, str] = {
    "recibido": (
        "Hemos recibido correctamente {n_docs} documento(s) de {empresa}. "
        "Los procesaremos en breve y recibirá una notificación cuando estén listos."
    ),
    "PDF_ILEGIBLE": (
        "El archivo '{nombre}' puede ser ilegible o estar dañado. "
        "Por favor, reenvíelo escaneado con mayor resolución (mínimo 150 DPI) "
        "o como PDF de texto si su aplicación lo permite."
    ),
    "DUPLICADO": (
        "El documento '{nombre}' ya fue recibido y registrado el {fecha}. "
        "No es necesario enviarlo de nuevo."
    ),
    "FORMATO_NO_SOPORTADO": (
        "El archivo con extensión '{extension}' no está soportado. "
        "Por favor, adjunte los documentos en formato PDF, ZIP, Excel (.xlsx) o TXT."
    ),
    "ZIP_PROTEGIDO_SIN_CLAVE": (
        "El archivo '{nombre}' está protegido con contraseña y no hemos podido abrirlo. "
        "Por favor, indíquenos la contraseña respondiendo a este mensaje "
        "o envíe el archivo sin protección."
    ),
    "ZIP_DEMASIADO_GRANDE": (
        "El archivo ZIP supera el límite de 100MB. "
        "Por favor, divídalo en varios emails con menos documentos cada uno."
    ),
    "SIN_ADJUNTOS": (
        "Hemos recibido su email pero no contiene ningún adjunto. "
        "Para enviar documentos, adjúntelos directamente al email."
    ),
}
_TEMPLATE_DEFAULT = (
    "Su email ha sido recibido. Nuestro equipo lo revisará en breve."
)


def generar_cuerpo_ack(motivo: str, contexto: dict) -> str:
    """Genera el texto del ACK según el motivo."""
    template = _TEMPLATES.get(motivo, _TEMPLATE_DEFAULT)
    try:
        return template.format(**contexto)
    except KeyError:
        return template


def enviar_ack(destinatario: str, motivo: str, contexto: dict) -> None:
    """Envía un email de confirmación/error al remitente.

    No hace nada si el motivo está en _MOTIVOS_SIN_ACK (seguridad).
    """
    if motivo in _MOTIVOS_SIN_ACK:
        logger.debug("ACK omitido para motivo '%s' (seguridad)", motivo)
        return

    cuerpo = generar_cuerpo_ack(motivo, contexto)
    asunto = "Documentos recibidos" if motivo == "recibido" else "Aviso sobre sus documentos"

    try:
        svc = obtener_servicio_email()
        svc.enviar_raw(
            destinatario=destinatario,
            asunto=asunto,
            cuerpo=cuerpo,
            cabeceras_extra={"X-SFCE-ACK": "true"},
        )
    except Exception as exc:
        logger.error("Error enviando ACK a %s: %s", destinatario, exc)
