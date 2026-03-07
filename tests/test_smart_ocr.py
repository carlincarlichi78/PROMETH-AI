import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from sfce.core.smart_ocr import SmartOCR, _elegir_motor_ocr


def _perfil_digital():
    from sfce.core.pdf_analyzer import PDFProfile
    return PDFProfile(
        palabras_por_pagina=150.0, ratio_texto_real=0.85,
        tiene_imagenes=False, paginas=1, cif_detectado="B12345678",
        tipo_doc="FV", texto_pdfplumber=" ".join(["palabra"] * 35 + ["Factura 001 Total 121 euros IVA 21%"])
    )

def _perfil_scan_simple():
    from sfce.core.pdf_analyzer import PDFProfile
    return PDFProfile(
        palabras_por_pagina=3.0, ratio_texto_real=0.10,
        tiene_imagenes=True, paginas=1, cif_detectado=None,
        tipo_doc="FV", texto_pdfplumber="xzb"
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


def test_motor_elegido_scan_usa_mistral_ocr3():
    """EasyOCR/PaddleOCR eliminados: scan va directo a mistral_ocr3."""
    motor = _elegir_motor_ocr(_perfil_scan_simple())
    assert motor == "mistral_ocr3"


def test_smart_ocr_retorna_texto_de_pdfplumber():
    perfil = _perfil_digital()
    with patch("sfce.core.smart_ocr.PDFAnalyzer") as mock_analyzer:
        mock_analyzer.return_value.analizar.return_value = perfil
        texto = SmartOCR.extraer_texto(Path("factura.pdf"), tipo_doc="FV")
    assert "Factura 001" in texto


def test_smart_ocr_usa_mistral_ocr3_para_scan(tmp_path):
    """Scan sin texto → escala a Mistral OCR3 (no EasyOCR)."""
    ruta = tmp_path / "scan.pdf"
    ruta.write_bytes(b"%PDF")
    perfil = _perfil_scan_simple()

    with patch("sfce.core.smart_ocr.PDFAnalyzer") as mock_an, \
         patch("sfce.core.smart_ocr._mistral_ocr3_extraer_texto") as mock_mistral:
        mock_an.return_value.analizar.return_value = perfil
        mock_mistral.return_value = " ".join(["FACTURA", "ESCANEA", "Total", "121,00", "EUR"] + ["palabra"] * 20)
        texto = SmartOCR.extraer_texto(ruta, tipo_doc="FV")

    mock_mistral.assert_called_once()
    assert "FACTURA ESCANEA" in texto


def test_smart_ocr_fallback_a_gpt4o_si_mistral_ocr3_falla(tmp_path):
    """Si Mistral OCR3 falla → GPT-4o Vision como último recurso."""
    ruta = tmp_path / "scan.pdf"
    ruta.write_bytes(b"%PDF")
    perfil = _perfil_scan_simple()

    with patch("sfce.core.smart_ocr.PDFAnalyzer") as mock_an, \
         patch("sfce.core.smart_ocr._mistral_ocr3_extraer_texto", return_value=""), \
         patch("sfce.core.smart_ocr._gpt4o_extraer_texto") as mock_gpt4o:
        mock_an.return_value.analizar.return_value = perfil
        mock_gpt4o.return_value = "Texto GPT-4o Vision"
        texto = SmartOCR.extraer_texto(ruta, tipo_doc="FV")

    mock_gpt4o.assert_called_once()
    assert texto == "Texto GPT-4o Vision"


def test_smart_ocr_pdfplumber_insuficiente_escala_a_mistral(tmp_path):
    """pdfplumber con < 30 palabras → escala a Mistral OCR3."""
    ruta = tmp_path / "scan.pdf"
    ruta.write_bytes(b"%PDF")
    from sfce.core.pdf_analyzer import PDFProfile
    perfil = PDFProfile(
        palabras_por_pagina=5.0, ratio_texto_real=0.80,
        tiene_imagenes=False, paginas=1, cif_detectado=None,
        tipo_doc="FC", texto_pdfplumber="poco texto aqui nada mas",
    )

    with patch("sfce.core.smart_ocr.PDFAnalyzer") as mock_an, \
         patch("sfce.core.smart_ocr._mistral_ocr3_extraer_texto") as mock_m:
        mock_an.return_value.analizar.return_value = perfil
        mock_m.return_value = "Texto completo extraido por Mistral OCR3 Vision documento"
        texto = SmartOCR.extraer_texto(ruta, tipo_doc="FC")

    mock_m.assert_called_once()
