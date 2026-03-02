"""Tests para el clasificador de documentos de onboarding masivo."""
import pytest
from pathlib import Path
from sfce.core.onboarding.clasificador import clasificar_documento, TipoDocOnboarding


def test_clasifica_036_por_cabecera(tmp_path):
    pdf_fake = tmp_path / "censo.pdf"
    from unittest.mock import patch, MagicMock
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "MODELO 036\nAGENCIA TRIBUTARIA\nNIF: B12345678"
    with patch("pdfplumber.open") as mock_pdf:
        mock_pdf.return_value.__enter__.return_value.pages = [mock_page]
        resultado = clasificar_documento(pdf_fake)
    assert resultado.tipo == TipoDocOnboarding.CENSO_036_037
    assert resultado.confianza >= 0.9


def test_clasifica_200_por_cabecera(tmp_path):
    from unittest.mock import patch, MagicMock
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "MODELO 200\nIMPUESTO SOBRE SOCIEDADES\nEjercicio 2024"
    with patch("pdfplumber.open") as mock_pdf:
        mock_pdf.return_value.__enter__.return_value.pages = [mock_page]
        resultado = clasificar_documento(tmp_path / "200.pdf")
    assert resultado.tipo == TipoDocOnboarding.IS_ANUAL_200


def test_clasifica_csv_facturas_emitidas(tmp_path):
    csv = tmp_path / "facturas_emitidas.csv"
    csv.write_text(
        "Fecha Expedicion;Serie;Numero;NIF Destinatario;Nombre Destinatario;"
        "Base Imponible;Cuota IVA;Total\n"
        "01/01/2024;A;1;B12345678;CLIENTE SL;1000;210;1210\n"
    )
    resultado = clasificar_documento(csv)
    assert resultado.tipo == TipoDocOnboarding.LIBRO_FACTURAS_EMITIDAS
    assert resultado.confianza >= 0.85


def test_clasifica_csv_facturas_recibidas(tmp_path):
    csv = tmp_path / "facturas_recibidas.csv"
    csv.write_text(
        "Fecha Expedicion;NIF Emisor;Nombre Emisor;Numero Factura;"
        "Base Imponible;Cuota IVA;Total\n"
        "01/01/2024;B87654321;PROVEEDOR SL;F001;500;105;605\n"
    )
    resultado = clasificar_documento(csv)
    assert resultado.tipo == TipoDocOnboarding.LIBRO_FACTURAS_RECIBIDAS


def test_desconocido_devuelve_tipo_desconocido(tmp_path):
    f = tmp_path / "random.pdf"
    from unittest.mock import patch, MagicMock
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "Documento sin cabecera reconocible"
    with patch("pdfplumber.open") as mock_pdf:
        mock_pdf.return_value.__enter__.return_value.pages = [mock_page]
        resultado = clasificar_documento(f)
    assert resultado.tipo == TipoDocOnboarding.DESCONOCIDO
    assert resultado.confianza < 0.5
