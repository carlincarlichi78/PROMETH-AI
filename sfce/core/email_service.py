"""Servicio de email SMTP para invitaciones."""
import logging
import smtplib
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class EmailConfig:
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    from_address: str


def _config_desde_env() -> Optional[EmailConfig]:
    import os
    host = os.getenv("SFCE_SMTP_HOST")
    if not host:
        return None
    return EmailConfig(
        smtp_host=host,
        smtp_port=int(os.getenv("SFCE_SMTP_PORT", "587")),
        smtp_user=os.getenv("SFCE_SMTP_USER", ""),
        smtp_password=os.getenv("SFCE_SMTP_PASSWORD", ""),
        from_address=os.getenv("SFCE_SMTP_FROM", "noreply@sfce.local"),
    )


class EmailService:
    def __init__(self, config: Optional[EmailConfig] = None):
        self._config = config if config is not None else _config_desde_env()

    def enviar_invitacion(self, destinatario: str, nombre: str, url_invitacion: str) -> None:
        if not self._config:
            logger.warning(
                "SFCE_SMTP_HOST no configurado — invitacion NO enviada a %s. URL: %s",
                destinatario, url_invitacion
            )
            return

        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Invitacion a SFCE — Activa tu cuenta"
        msg["From"] = self._config.from_address
        msg["To"] = destinatario

        texto_plano = (
            f"Hola {nombre},\n\n"
            f"Has sido invitado al sistema SFCE.\n\n"
            f"Activa tu cuenta en:\n{url_invitacion}\n\n"
            f"El enlace caduca en 7 dias.\n"
        )
        texto_html = f"""<html><body>
        <h2>Bienvenido a SFCE</h2>
        <p>Hola <strong>{nombre}</strong>,</p>
        <p>Has sido invitado al sistema SFCE.</p>
        <p><a href="{url_invitacion}">Activar mi cuenta</a></p>
        <p style="color:#64748b;font-size:12px;">El enlace caduca en 7 dias.</p>
        </body></html>"""

        msg.attach(MIMEText(texto_plano, "plain"))
        msg.attach(MIMEText(texto_html, "html"))

        with smtplib.SMTP(self._config.smtp_host, self._config.smtp_port) as server:
            server.starttls()
            server.login(self._config.smtp_user, self._config.smtp_password)
            server.sendmail(self._config.from_address, destinatario, msg.as_string())
        logger.info("Invitacion enviada a %s", destinatario)

    def enviar_reset_password(self, destinatario: str, nombre: str, token: str) -> None:
        if not self._config:
            raise RuntimeError("SMTP no configurado")

        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Restablecer contrasena SFCE"
        msg["From"] = self._config.from_address
        msg["To"] = destinatario

        texto_plano = (
            f"Hola {nombre},\n\n"
            f"Tu codigo de recuperacion es:\n\n{token}\n\n"
            f"Introdu­celo en la app para establecer una nueva contrasena.\n"
            f"Caduca en 2 horas.\n"
        )
        texto_html = f"""<html><body>
        <h2>Restablecer contrasena</h2>
        <p>Hola <strong>{nombre}</strong>,</p>
        <p>Tu codigo de recuperacion es:</p>
        <p style="font-size:24px;font-weight:bold;letter-spacing:4px;color:#0f172a;">{token}</p>
        <p style="color:#64748b;font-size:12px;">Caduca en 2 horas.</p>
        </body></html>"""

        msg.attach(MIMEText(texto_plano, "plain"))
        msg.attach(MIMEText(texto_html, "html"))

        with smtplib.SMTP(self._config.smtp_host, self._config.smtp_port) as server:
            server.starttls()
            server.login(self._config.smtp_user, self._config.smtp_password)
            server.sendmail(self._config.from_address, destinatario, msg.as_string())
        logger.info("Reset password enviado a %s", destinatario)


_servicio_global: Optional[EmailService] = None


def obtener_servicio_email() -> EmailService:
    global _servicio_global
    if _servicio_global is None:
        _servicio_global = EmailService()
    return _servicio_global


def enviar_invitacion_onboarding(email: str, nombre_empresa: str) -> None:
    """Envia email al empresario para que complete el onboarding."""
    asunto = f"Completa el alta de {nombre_empresa} en SFCE"
    cuerpo = (
        f"Tu gestoria ha iniciado el alta de {nombre_empresa} en SFCE.\n"
        f"Accede a https://app.sfce.local/portal para completar tus datos.\n"
    )
    try:
        obtener_servicio_email().enviar_invitacion(
            destinatario=email,
            nombre=nombre_empresa,
            url_invitacion="https://app.sfce.local/portal",
        )
    except Exception:
        pass  # Email es best-effort
