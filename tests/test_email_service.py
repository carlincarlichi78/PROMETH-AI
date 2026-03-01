"""Tests — Servicio de email (T-EMAIL)."""
import pytest
from unittest.mock import patch, MagicMock
from sfce.core.email_service import EmailService, EmailConfig


class TestEmailService:

    def test_enviar_invitacion_llama_smtp(self):
        config = EmailConfig(
            smtp_host="smtp.test.com",
            smtp_port=587,
            smtp_user="test@test.com",
            smtp_password="pass",
            from_address="noreply@sfce.local",
        )
        service = EmailService(config)

        with patch("smtplib.SMTP") as mock_smtp:
            instancia = MagicMock()
            mock_smtp.return_value.__enter__ = MagicMock(return_value=instancia)
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

            service.enviar_invitacion(
                destinatario="nuevo@gestoria.com",
                nombre="Ana García",
                url_invitacion="https://sfce.local/auth/aceptar-invitacion?token=abc123",
            )

            instancia.sendmail.assert_called_once()

    def test_sin_config_no_falla_solo_loguea(self):
        """Sin SMTP configurado, no lanza excepción."""
        service = EmailService(config=None)
        import os
        os.environ.pop("SFCE_SMTP_HOST", None)  # asegurar que no está
        service.enviar_invitacion(
            destinatario="test@test.com",
            nombre="Test",
            url_invitacion="https://sfce.local/token=xyz",
        )
        # No debe lanzar excepción
