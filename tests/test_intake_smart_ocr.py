# tests/test_intake_smart_ocr.py
import pytest
from pathlib import Path
from unittest.mock import patch


def test_intake_usa_smart_ocr_en_lugar_de_mistral_directo(tmp_path):
    """Verifica que intake no llama directamente a extraer_factura_mistral."""
    ruta = tmp_path / "fv.pdf"
    ruta.write_bytes(b"%PDF-1.4")
    datos_mock = {"total": 121.0, "base_imponible": 100.0, "_fuente": "gemini"}

    with patch("sfce.phases.intake.SmartOCR") as mock_smart:
        mock_smart.extraer.return_value = datos_mock
        from sfce.phases.intake import _extraer_datos_ocr
        resultado = _extraer_datos_ocr(ruta, tipo_doc="FV")

    mock_smart.extraer.assert_called_once_with(ruta, tipo_doc="FV")
    assert resultado["total"] == 121.0
