"""Renombrado de adjuntos post-OCR.

Patrón: {FECHA}_{TIPO}_{EMISOR}_{IMPORTE}EUR.{EXT}
Ejemplo: 2025-01-15_FACTURA_PROVEEDOR_Iberdrola_SA_254.30EUR.pdf
"""
import re
from pathlib import Path


def _limpiar(texto: str) -> str:
    """Elimina caracteres no válidos para nombres de archivo."""
    return re.sub(r"[^\w\-]", "_", texto).strip("_")


def generar_nombre_renombrado(
    tipo_documento: str,
    nombre_emisor: str,
    total: float | None,
    fecha_documento: str,
    nombre_original: str,
) -> str:
    """Genera el nombre renombrado según el patrón estándar SFCE."""
    ext = Path(nombre_original).suffix.lower() or ".pdf"
    tipo = _limpiar(tipo_documento)
    emisor = _limpiar(nombre_emisor)
    fecha = fecha_documento[:10] if fecha_documento else "sin-fecha"

    if total is not None and total != 0:
        importe = f"_{total:.2f}EUR"
    else:
        importe = ""

    return f"{fecha}_{tipo}_{emisor}{importe}{ext}"
