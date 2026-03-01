"""Tests para validador de contenido PDF."""
import pytest
from sfce.core.validador_pdf import validar_pdf, ErrorValidacionPDF


def test_pdf_valido():
    contenido = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF"
    validar_pdf(contenido, "factura.pdf")  # No debe lanzar


def test_pdf_con_javascript_rechazado():
    contenido = b"%PDF-1.4\n/JavaScript\n%%EOF"
    with pytest.raises(ErrorValidacionPDF, match="JavaScript"):
        validar_pdf(contenido, "malicioso.pdf")


def test_pdf_con_js_rechazado():
    contenido = b"%PDF-1.4\n/JS \n%%EOF"
    with pytest.raises(ErrorValidacionPDF, match="JavaScript"):
        validar_pdf(contenido, "malicioso.pdf")


def test_magic_bytes_incorrectos():
    contenido = b"PK\x03\x04"  # ZIP, no PDF
    with pytest.raises(ErrorValidacionPDF, match="magic bytes"):
        validar_pdf(contenido, "fake.pdf")


def test_archivo_vacio():
    with pytest.raises(ErrorValidacionPDF, match="vac"):
        validar_pdf(b"", "vacio.pdf")
