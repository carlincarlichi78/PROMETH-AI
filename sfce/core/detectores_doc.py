"""Detectores de tipo documental pre-OCR.

Identifican documentos con estructura conocida ANTES de enviarlos a LLMs,
permitiendo extraer datos con regex (coste $0) en vez de modelos de pago.

Tipos soportados:
  - Adeudos bancarios ING (notificaciones de cargo emitidas por ING Bank NV)
"""
import logging
import re
from typing import Optional

logger = logging.getLogger("sfce.detectores_doc")


# ---------------------------------------------------------------------------
# Adeudo bancario ING
# ---------------------------------------------------------------------------

# Patrones inequívocos presentes en todos los adeudos ING
_PATRONES_ADEUDO_ING = [
    "adeudo recibido",   # título del documento
    "ing",               # membrete emisor
    "entidad emisora",   # campo clave con proveedor real
]


def detectar_tipo_adeudo_ing(texto_raw: str) -> bool:
    """Detecta si un documento es un adeudo bancario ING.

    Criterio: presencia simultánea de los tres patrones inequívocos.
    Retorna True si es adeudo ING, False en caso contrario.
    """
    texto_lower = texto_raw.lower()
    return all(p in texto_lower for p in _PATRONES_ADEUDO_ING)


def extraer_emisor_adeudo_ing(texto_raw: str) -> dict:
    """Extrae los campos relevantes de un adeudo ING mediante regex.

    Retorna dict compatible con DatosExtraidos (campos opcionales: None si no encontrado).
    El emisor_nombre es el proveedor real (campo 'Entidad emisora'), no ING.
    """
    resultado: dict = {
        "emisor_nombre": None,
        "total": None,
        "fecha": None,
        "numero_factura": None,   # referencia bancaria SEPA
        "info_adicional": None,
        "_fuente": "detector_adeudo_ing",
        "_tipo_doc_detectado": "adeudo_bancario_ing",
    }

    # Nombre del proveedor real (la línea siguiente a "Entidad emisora")
    m = re.search(r"Entidad\s+emisora\s*\n\s*(.+?)(?:\n|$)", texto_raw, re.IGNORECASE)
    if m:
        resultado["emisor_nombre"] = m.group(1).strip()

    # Importe (la línea siguiente a "Importe euros")
    m = re.search(r"Importe\s+euros\s*\n\s*([\d.,]+)", texto_raw, re.IGNORECASE)
    if m:
        try:
            resultado["total"] = float(m.group(1).replace(".", "").replace(",", "."))
        except ValueError:
            resultado["total"] = m.group(1).strip()

    # Fecha de operación
    m = re.search(r"Fecha\s+operaci[oó]n\s*\n\s*(\d{2}/\d{2}/\d{4})", texto_raw, re.IGNORECASE)
    if m:
        resultado["fecha"] = m.group(1).strip()

    # Referencia SEPA → número de factura
    m = re.search(r"Referencia\s*\n\s*(.+?)(?:\n|$)", texto_raw, re.IGNORECASE)
    if m:
        resultado["numero_factura"] = m.group(1).strip()

    # Información adicional (puede contener número de factura del emisor real)
    m = re.search(
        r"Informaci[oó]n\s+adicional\s*\n\s*(.+?)(?:\n\n|\Z)",
        texto_raw,
        re.IGNORECASE | re.DOTALL,
    )
    if m:
        resultado["info_adicional"] = m.group(1).strip()

    return resultado


def procesar_adeudo_ing(texto_raw: str) -> Optional[dict]:
    """Punto de entrada unificado: detecta y extrae si es adeudo ING.

    Retorna dict de campos si es adeudo ING, None si no lo es.
    El llamador puede usar el resultado directamente en vez de invocar LLMs.
    """
    if not detectar_tipo_adeudo_ing(texto_raw):
        return None

    datos = extraer_emisor_adeudo_ing(texto_raw)
    logger.info(
        "Adeudo ING detectado. Emisor real: %s | Importe: %s",
        datos.get("emisor_nombre"),
        datos.get("total"),
    )
    return datos
