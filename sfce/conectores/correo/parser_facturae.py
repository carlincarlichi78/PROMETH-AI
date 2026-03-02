"""Parser de FacturaE XML — extrae datos estructurados sin necesidad de OCR.

Soporta esquemas 3.2, 3.2.1 y 3.2.2 del formato FacturaE del Ministerio de Hacienda.
Referencia: https://www.facturae.gob.es
"""
import logging
import xml.etree.ElementTree as ET
from typing import Optional

logger = logging.getLogger(__name__)

_NAMESPACES = [
    "http://www.facturae.gob.es/formato/Version3.2/Facturae32",
    "http://www.facturae.gob.es/formato/Version3.2.1/Facturae32",
    "http://www.facturae.gob.es/formato/Version3.2.2/Facturae32",
    "http://www.facturae.es/Facturae/2009/v3.2/Facturae",
]


def es_facturae(contenido: bytes) -> bool:
    """Detecta si un bloque de bytes es un XML FacturaE."""
    try:
        root = ET.fromstring(contenido)
    except ET.ParseError:
        return False
    ns = root.tag.split("}")[0].lstrip("{") if "}" in root.tag else ""
    return any(ns == n for n in _NAMESPACES)


def parsear_facturae(contenido: bytes) -> Optional[dict]:
    """Extrae datos de un XML FacturaE.

    Returns:
        dict con cif_emisor, nombre_emisor, cif_receptor, importe_total,
        base_imponible, cuota_iva, fecha, numero_factura, tipo_doc.
        None si el XML es inválido o no es FacturaE.
    """
    try:
        root = ET.fromstring(contenido)
    except ET.ParseError as e:
        logger.warning("FacturaE parse error: %s", e)
        return None

    ns_uri = root.tag.split("}")[0].lstrip("{") if "}" in root.tag else ""
    if not any(ns_uri == n for n in _NAMESPACES):
        return None

    ns = {"f": ns_uri}

    def _txt(xpath: str) -> str:
        el = root.find(xpath, ns)
        return el.text.strip() if el is not None and el.text else ""

    def _float(xpath: str) -> float:
        try:
            return float(_txt(xpath))
        except (ValueError, TypeError):
            return 0.0

    return {
        "tipo_doc": "FV",
        "cif_emisor": _txt(".//f:SellerParty//f:TaxIdentificationNumber"),
        "nombre_emisor": _txt(".//f:SellerParty//f:CorporateName"),
        "cif_receptor": _txt(".//f:BuyerParty//f:TaxIdentificationNumber"),
        "nombre_receptor": _txt(".//f:BuyerParty//f:CorporateName"),
        "numero_factura": _txt(".//f:InvoiceNumber"),
        "fecha": _txt(".//f:InvoiceIssueDate"),
        "importe_total": _float(".//f:InvoiceTotal"),
        "base_imponible": _float(".//f:TotalGrossAmount"),
        "cuota_iva": _float(".//f:TotalTaxOutputs"),
        "fuente": "facturae_xml",
        "confianza": 1.0,  # datos estructurados = máxima confianza
    }
