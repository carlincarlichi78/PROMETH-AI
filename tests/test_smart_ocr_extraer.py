import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


def test_extraer_usa_cache_si_existe(tmp_path):
    from sfce.core.smart_ocr import SmartOCR
    ruta = tmp_path / "fv.pdf"
    ruta.write_bytes(b"%PDF")
    datos_cache = {"total": 100.0, "base_imponible": 82.6, "_fuente": "cache"}

    with patch("sfce.core.smart_ocr.obtener_cache_ocr", return_value=datos_cache) as mock_cache:
        resultado = SmartOCR.extraer(ruta, tipo_doc="FV")

    mock_cache.assert_called_once_with(str(ruta))
    assert resultado["total"] == 100.0
    assert resultado["_fuente"] == "cache"


def test_extraer_guarda_en_cache_tras_procesar(tmp_path):
    from sfce.core.smart_ocr import SmartOCR
    ruta = tmp_path / "fv.pdf"
    ruta.write_bytes(b"%PDF")
    datos_ocr = {"total": 121.0, "_fuente": "gemini"}

    with patch("sfce.core.smart_ocr.obtener_cache_ocr", return_value=None), \
         patch("sfce.core.smart_ocr.SmartOCR.extraer_texto", return_value="Factura 001 Total 121"), \
         patch("sfce.core.smart_ocr.SmartParser.parsear", return_value=datos_ocr), \
         patch("sfce.core.smart_ocr.guardar_cache_ocr") as mock_guardar:

        resultado = SmartOCR.extraer(ruta, tipo_doc="FV")

    mock_guardar.assert_called_once()
    assert resultado["total"] == 121.0


def test_extraer_retorna_none_si_todo_falla(tmp_path):
    from sfce.core.smart_ocr import SmartOCR
    ruta = tmp_path / "fv.pdf"
    ruta.write_bytes(b"%PDF")

    with patch("sfce.core.smart_ocr.obtener_cache_ocr", return_value=None), \
         patch("sfce.core.smart_ocr.SmartOCR.extraer_texto", return_value=""), \
         patch("sfce.core.smart_ocr.SmartParser.parsear", return_value=None):

        resultado = SmartOCR.extraer(ruta, tipo_doc="FV")

    assert resultado is None
