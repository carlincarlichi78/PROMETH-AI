"""Tests para el módulo OCR GPT-4o companion."""
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from sfce.core.ocr_gpt import extraer_factura_gpt


@pytest.fixture
def ruta_pdf_ficticia(tmp_path) -> Path:
    """PDF mínimo válido para tests."""
    pdf = tmp_path / "factura.pdf"
    pdf.write_bytes(b"%PDF-1.4 test content")
    return pdf


def test_extraer_factura_gpt_retorna_dict(ruta_pdf_ficticia):
    """Con OpenAI disponible y respuesta válida, retorna dict."""
    datos_esperados = {
        "emisor_cif": "B12345678",
        "total": 121.0,
        "tipo": "factura_proveedor",
    }
    respuesta_mock = MagicMock()
    respuesta_mock.choices[0].message.content = json.dumps(datos_esperados)

    with patch("sfce.core.ocr_gpt._obtener_cliente") as mock_client_fn, \
         patch("sfce.core.ocr_gpt._extraer_texto_pdf", return_value="Texto de factura simulado"):
        cliente_mock = MagicMock()
        cliente_mock.chat.completions.create.return_value = respuesta_mock
        mock_client_fn.return_value = cliente_mock

        resultado = extraer_factura_gpt(ruta_pdf_ficticia)

    assert isinstance(resultado, dict)
    assert resultado["emisor_cif"] == "B12345678"
    assert resultado.get("_fuente") == "gpt4o"


def test_extraer_factura_gpt_retorna_none_si_json_invalido(ruta_pdf_ficticia):
    """Si la respuesta no es JSON válido, retorna None."""
    respuesta_mock = MagicMock()
    respuesta_mock.choices[0].message.content = "esto no es json {"

    with patch("sfce.core.ocr_gpt._obtener_cliente") as mock_client_fn, \
         patch("sfce.core.ocr_gpt._extraer_texto_pdf", return_value="Texto de factura"):
        cliente_mock = MagicMock()
        cliente_mock.chat.completions.create.return_value = respuesta_mock
        mock_client_fn.return_value = cliente_mock

        resultado = extraer_factura_gpt(ruta_pdf_ficticia)

    assert resultado is None


def test_extraer_factura_gpt_retorna_none_si_api_falla(ruta_pdf_ficticia):
    """Si la API lanza excepción, retorna None (no propaga)."""
    with patch("sfce.core.ocr_gpt._obtener_cliente") as mock_client_fn, \
         patch("sfce.core.ocr_gpt._extraer_texto_pdf", return_value="Texto"):
        cliente_mock = MagicMock()
        cliente_mock.chat.completions.create.side_effect = Exception("API error 429")
        mock_client_fn.return_value = cliente_mock

        resultado = extraer_factura_gpt(ruta_pdf_ficticia)

    assert resultado is None


def test_extraer_factura_gpt_retorna_none_si_cliente_no_disponible(ruta_pdf_ficticia):
    """Sin OPENAI_API_KEY, retorna None."""
    with patch("sfce.core.ocr_gpt._obtener_cliente", return_value=None):
        resultado = extraer_factura_gpt(ruta_pdf_ficticia)

    assert resultado is None
