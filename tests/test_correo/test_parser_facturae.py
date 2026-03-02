import pytest
from sfce.conectores.correo.parser_facturae import es_facturae, parsear_facturae

FACTURAE_VALIDA = b"""<?xml version="1.0" encoding="UTF-8"?>
<Facturae xmlns="http://www.facturae.gob.es/formato/Version3.2.2/Facturae32">
  <FileHeader>
    <SchemaVersion>3.2.2</SchemaVersion>
    <Modality>I</Modality>
    <InvoiceIssuerType>EM</InvoiceIssuerType>
  </FileHeader>
  <Parties>
    <SellerParty>
      <TaxIdentification>
        <PersonTypeCode>J</PersonTypeCode>
        <TaxIdentificationNumber>B12345678</TaxIdentificationNumber>
      </TaxIdentification>
      <LegalEntity>
        <CorporateName>Proveedor Test SL</CorporateName>
      </LegalEntity>
    </SellerParty>
    <BuyerParty>
      <TaxIdentification>
        <TaxIdentificationNumber>B87654321</TaxIdentificationNumber>
      </TaxIdentification>
      <LegalEntity>
        <CorporateName>Comprador Test SL</CorporateName>
      </LegalEntity>
    </BuyerParty>
  </Parties>
  <Invoices>
    <Invoice>
      <InvoiceHeader>
        <InvoiceNumber>2025/001</InvoiceNumber>
        <InvoiceIssueDate>2025-01-15</InvoiceIssueDate>
      </InvoiceHeader>
      <InvoiceTotals>
        <TotalGrossAmount>1000.00</TotalGrossAmount>
        <TotalTaxOutputs>210.00</TotalTaxOutputs>
        <InvoiceTotal>1210.00</InvoiceTotal>
      </InvoiceTotals>
    </Invoice>
  </Invoices>
</Facturae>"""

XML_NO_FACTURAE = b"""<?xml version="1.0"?>
<root><item>no es facturae</item></root>"""


def test_detecta_facturae_valida():
    assert es_facturae(FACTURAE_VALIDA) is True


def test_detecta_xml_no_facturae():
    assert es_facturae(XML_NO_FACTURAE) is False


def test_detecta_pdf_como_no_facturae():
    assert es_facturae(b"%PDF-1.4 contenido") is False


def test_parsea_cif_emisor():
    datos = parsear_facturae(FACTURAE_VALIDA)
    assert datos["cif_emisor"] == "B12345678"


def test_parsea_nombre_emisor():
    datos = parsear_facturae(FACTURAE_VALIDA)
    assert datos["nombre_emisor"] == "Proveedor Test SL"


def test_parsea_cif_receptor():
    datos = parsear_facturae(FACTURAE_VALIDA)
    assert datos["cif_receptor"] == "B87654321"


def test_parsea_importe_total():
    datos = parsear_facturae(FACTURAE_VALIDA)
    assert datos["importe_total"] == 1210.00


def test_parsea_base_imponible():
    datos = parsear_facturae(FACTURAE_VALIDA)
    assert datos["base_imponible"] == 1000.00


def test_parsea_cuota_iva():
    datos = parsear_facturae(FACTURAE_VALIDA)
    assert datos["cuota_iva"] == 210.00


def test_parsea_fecha():
    datos = parsear_facturae(FACTURAE_VALIDA)
    assert datos["fecha"] == "2025-01-15"


def test_parsea_numero_factura():
    datos = parsear_facturae(FACTURAE_VALIDA)
    assert datos["numero_factura"] == "2025/001"


def test_tipo_doc_siempre_fv():
    datos = parsear_facturae(FACTURAE_VALIDA)
    assert datos["tipo_doc"] == "FV"


def test_xml_invalido_retorna_none():
    resultado = parsear_facturae(b"<roto>")
    assert resultado is None
