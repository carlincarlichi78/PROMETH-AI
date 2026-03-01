"""Tests del renombrador post-OCR de adjuntos."""
from sfce.conectores.correo.renombrador import generar_nombre_renombrado


def test_nombre_factura_completa():
    nombre = generar_nombre_renombrado(
        tipo_documento="FACTURA_PROVEEDOR",
        nombre_emisor="Iberdrola SA",
        total=254.30,
        fecha_documento="2025-01-15",
        nombre_original="factura.pdf",
    )
    assert nombre == "2025-01-15_FACTURA_PROVEEDOR_Iberdrola_SA_254.30EUR.pdf"


def test_caracteres_invalidos_eliminados():
    nombre = generar_nombre_renombrado(
        tipo_documento="FACTURA_PROVEEDOR",
        nombre_emisor="Empresa/Con:Caracteres*Raros",
        total=100.0,
        fecha_documento="2025-02-01",
        nombre_original="doc.pdf",
    )
    assert "/" not in nombre
    assert ":" not in nombre
    assert "*" not in nombre


def test_sin_total_omite_importe():
    nombre = generar_nombre_renombrado(
        tipo_documento="OTRO",
        nombre_emisor="Emisor",
        total=None,
        fecha_documento="2025-01-01",
        nombre_original="archivo.pdf",
    )
    assert "EUR" not in nombre


def test_extension_preservada():
    nombre = generar_nombre_renombrado(
        tipo_documento="EXTRACTO",
        nombre_emisor="BBVA",
        total=0,
        fecha_documento="2025-01-01",
        nombre_original="extracto.xlsx",
    )
    assert nombre.endswith(".xlsx")


def test_total_cero_omite_importe():
    nombre = generar_nombre_renombrado(
        tipo_documento="NOMINA",
        nombre_emisor="Empresa SL",
        total=0,
        fecha_documento="2025-03-01",
        nombre_original="nomina.pdf",
    )
    assert "EUR" not in nombre
