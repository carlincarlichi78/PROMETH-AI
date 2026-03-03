# tests/test_worker_ocr_smart.py
from unittest.mock import patch
from pathlib import Path


def test_worker_usa_smart_ocr(tmp_path):
    ruta = tmp_path / "fv.pdf"
    ruta.write_bytes(b"%PDF")
    datos_mock = {"total": 100.0, "_fuente": "pdfplumber"}

    with patch("sfce.core.worker_ocr_gate0.SmartOCR") as mock_smart:
        mock_smart.extraer.return_value = datos_mock
        from sfce.core.worker_ocr_gate0 import _ejecutar_ocr_tiers
        resultado = _ejecutar_ocr_tiers(ruta)

    mock_smart.extraer.assert_called_once_with(ruta)
    assert resultado["total"] == 100.0


def test_worker_retorna_none_si_smart_ocr_falla(tmp_path):
    ruta = tmp_path / "fv.pdf"
    ruta.write_bytes(b"%PDF")

    with patch("sfce.core.worker_ocr_gate0.SmartOCR") as mock_smart:
        mock_smart.extraer.return_value = None
        from sfce.core.worker_ocr_gate0 import _ejecutar_ocr_tiers
        resultado = _ejecutar_ocr_tiers(ruta)

    assert resultado is None
