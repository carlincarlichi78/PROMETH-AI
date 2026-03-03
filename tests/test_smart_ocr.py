import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from sfce.core.smart_ocr import SmartOCR, _elegir_motor_ocr


def _perfil_digital():
    from sfce.core.pdf_analyzer import PDFProfile
    return PDFProfile(
        palabras_por_pagina=150.0, ratio_texto_real=0.85,
        tiene_imagenes=False, paginas=1, cif_detectado="B12345678",
        tipo_doc="FV", texto_pdfplumber="Factura 001 Total 121 euros IVA 21%"
    )

def _perfil_scan_simple():
    from sfce.core.pdf_analyzer import PDFProfile
    return PDFProfile(
        palabras_por_pagina=3.0, ratio_texto_real=0.10,
        tiene_imagenes=True, paginas=1, cif_detectado=None,
        tipo_doc="FV", texto_pdfplumber="xzb qwerty"
    )

def _perfil_ban():
    from sfce.core.pdf_analyzer import PDFProfile
    return PDFProfile(
        palabras_por_pagina=200.0, ratio_texto_real=0.90,
        tiene_imagenes=False, paginas=3, cif_detectado="A08663619",
        tipo_doc="BAN", texto_pdfplumber="Extracto CaixaBank movimientos"
    )


def test_motor_elegido_digital_usa_pdfplumber():
    motor = _elegir_motor_ocr(_perfil_digital())
    assert motor == "pdfplumber"


def test_motor_elegido_ban_fuerza_pdfplumber():
    motor = _elegir_motor_ocr(_perfil_ban())
    assert motor == "pdfplumber"


def test_motor_elegido_scan_simple_usa_easyocr():
    motor = _elegir_motor_ocr(_perfil_scan_simple())
    assert motor == "easyocr"


def test_smart_ocr_retorna_texto_de_pdfplumber():
    perfil = _perfil_digital()
    with patch("sfce.core.smart_ocr.PDFAnalyzer") as mock_analyzer:
        mock_analyzer.return_value.analizar.return_value = perfil
        texto = SmartOCR.extraer_texto(Path("factura.pdf"), tipo_doc="FV")
    assert "Factura 001" in texto


def test_smart_ocr_usa_easyocr_para_scan(tmp_path):
    ruta = tmp_path / "scan.pdf"
    ruta.write_bytes(b"%PDF")
    perfil = _perfil_scan_simple()

    with patch("sfce.core.smart_ocr.PDFAnalyzer") as mock_an, \
         patch("sfce.core.smart_ocr._easyocr_extraer_texto") as mock_easy:
        mock_an.return_value.analizar.return_value = perfil
        mock_easy.return_value = "FACTURA ESCANEA Total 121,00 EUR"
        texto = SmartOCR.extraer_texto(ruta, tipo_doc="FV")

    mock_easy.assert_called_once()
    assert texto == "FACTURA ESCANEA Total 121,00 EUR"


def test_smart_ocr_fallback_a_mistral_si_easyocr_falla(tmp_path):
    ruta = tmp_path / "scan.pdf"
    ruta.write_bytes(b"%PDF")
    perfil = _perfil_scan_simple()

    with patch("sfce.core.smart_ocr.PDFAnalyzer") as mock_an, \
         patch("sfce.core.smart_ocr._easyocr_extraer_texto", return_value=""), \
         patch("sfce.core.smart_ocr._paddleocr_extraer_texto", return_value=""), \
         patch("sfce.core.smart_ocr._mistral_extraer_texto") as mock_mistral:
        mock_an.return_value.analizar.return_value = perfil
        mock_mistral.return_value = "Texto Mistral OCR"
        texto = SmartOCR.extraer_texto(ruta, tipo_doc="FV")

    mock_mistral.assert_called_once()
    assert texto == "Texto Mistral OCR"
