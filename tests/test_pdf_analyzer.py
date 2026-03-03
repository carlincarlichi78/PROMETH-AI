import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from sfce.core.pdf_analyzer import PDFAnalyzer, PDFProfile


def _perfil_minimo():
    return PDFProfile(
        palabras_por_pagina=0.0,
        ratio_texto_real=0.0,
        tiene_imagenes=False,
        paginas=1,
        cif_detectado=None,
        tipo_doc=None,
        texto_pdfplumber="",
    )


def test_pdf_profile_es_dataclass():
    p = _perfil_minimo()
    assert p.paginas == 1


def test_tiene_texto_extractable_true():
    p = PDFProfile(
        palabras_por_pagina=120.0, ratio_texto_real=0.85,
        tiene_imagenes=False, paginas=1, cif_detectado=None,
        tipo_doc=None, texto_pdfplumber="factura texto completo con palabras"
    )
    assert p.tiene_texto_extractable is True


def test_tiene_texto_extractable_false_por_ratio():
    p = PDFProfile(
        palabras_por_pagina=5.0, ratio_texto_real=0.20,
        tiene_imagenes=True, paginas=1, cif_detectado=None,
        tipo_doc=None, texto_pdfplumber="abc def"
    )
    assert p.tiene_texto_extractable is False


def test_analizar_pdf_digital(tmp_path):
    ruta = tmp_path / "factura.pdf"
    ruta.write_bytes(b"%PDF-1.4 fake")

    with patch("sfce.core.pdf_analyzer.pdfplumber") as mock_pl, \
         patch("sfce.core.pdf_analyzer.fitz") as mock_fitz:

        mock_page = MagicMock()
        mock_page.extract_text.return_value = "FACTURA 001 NIF B12345678 Total 121.00 euros IVA incluido"
        mock_pdf = MagicMock()
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_pdf.pages = [mock_page]
        mock_pl.open.return_value = mock_pdf

        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([MagicMock(get_images=MagicMock(return_value=[]))]))
        mock_fitz.open.return_value = mock_doc

        perfil = PDFAnalyzer().analizar(ruta)

    assert perfil.paginas == 1
    assert perfil.cif_detectado == "B12345678"
    assert perfil.texto_pdfplumber != ""


def test_analizar_detecta_tipo_doc_ban():
    p = PDFProfile(
        palabras_por_pagina=200.0, ratio_texto_real=0.90,
        tiene_imagenes=False, paginas=3, cif_detectado="A08663619",
        tipo_doc="BAN", texto_pdfplumber="Extracto CaixaBank..."
    )
    assert p.tipo_doc == "BAN"
    assert p.tiene_texto_extractable is True
