import pytest
from unittest.mock import patch, MagicMock
from sfce.conectores.correo.ack_automatico import (
    generar_cuerpo_ack,
    enviar_ack,
    MOTIVOS_CON_ACK,
)


def test_ack_recibido_ok():
    cuerpo = generar_cuerpo_ack(
        motivo="recibido",
        contexto={"n_docs": 3, "empresa": "Pastorino SL"},
    )
    assert "3" in cuerpo
    assert "Pastorino" in cuerpo


def test_ack_pdf_ilegible():
    cuerpo = generar_cuerpo_ack(
        motivo="PDF_ILEGIBLE",
        contexto={"nombre": "factura.pdf"},
    )
    assert "factura.pdf" in cuerpo
    assert "calidad" in cuerpo.lower() or "legible" in cuerpo.lower()


def test_ack_duplicado_incluye_fecha():
    cuerpo = generar_cuerpo_ack(
        motivo="DUPLICADO",
        contexto={"nombre": "f.pdf", "fecha": "2025-01-10"},
    )
    assert "2025-01-10" in cuerpo


def test_ack_formato_no_soportado():
    cuerpo = generar_cuerpo_ack(
        motivo="FORMATO_NO_SOPORTADO",
        contexto={"extension": ".docx"},
    )
    assert ".docx" in cuerpo


def test_ack_zip_sin_clave():
    cuerpo = generar_cuerpo_ack(
        motivo="ZIP_PROTEGIDO_SIN_CLAVE",
        contexto={"nombre": "extracto.zip"},
    )
    assert "contraseña" in cuerpo.lower() or "protegido" in cuerpo.lower()


def test_ack_sin_adjuntos():
    cuerpo = generar_cuerpo_ack(motivo="SIN_ADJUNTOS", contexto={})
    assert "adjunto" in cuerpo.lower()


def test_motivo_desconocido_no_lanza_excepcion():
    cuerpo = generar_cuerpo_ack(motivo="MOTIVO_INVENTADO", contexto={})
    assert cuerpo  # retorna algo, no explota


def test_enviar_ack_llama_servicio_email():
    with patch("sfce.conectores.correo.ack_automatico.obtener_servicio_email") as mock_svc:
        mock_svc.return_value.enviar_raw = MagicMock()
        enviar_ack(
            destinatario="cliente@empresa.es",
            motivo="recibido",
            contexto={"n_docs": 1, "empresa": "Test"},
        )
        mock_svc.return_value.enviar_raw.assert_called_once()


def test_ack_remitente_no_autorizado_no_se_envia():
    """No enviar ACK a remitentes no autorizados para no confirmar la dirección."""
    with patch("sfce.conectores.correo.ack_automatico.obtener_servicio_email") as mock_svc:
        enviar_ack(
            destinatario="spam@externo.com",
            motivo="REMITENTE_NO_AUTORIZADO",
            contexto={},
        )
        mock_svc.return_value.enviar_raw.assert_not_called()
