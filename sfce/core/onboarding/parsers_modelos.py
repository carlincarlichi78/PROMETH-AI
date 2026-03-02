"""Parsers para modelos fiscales AEAT: 200, 303, 390, 130, 100, 111."""
from __future__ import annotations
import re
from pathlib import Path
from typing import Optional

import pdfplumber


def _extraer_texto_pdf(ruta: Path) -> str:
    try:
        with pdfplumber.open(str(ruta)) as pdf:
            return "\n".join(p.extract_text() or "" for p in pdf.pages)
    except Exception:
        return ""


def _buscar_importe(texto: str, patron: str) -> Optional[float]:
    m = re.search(patron, texto, re.IGNORECASE)
    if not m:
        return None
    val = m.group(1).replace(".", "").replace(",", ".")
    try:
        return float(val)
    except ValueError:
        return None


def _buscar_si_no(texto: str, patron: str) -> Optional[bool]:
    m = re.search(patron, texto, re.IGNORECASE)
    if not m:
        return None
    return "si" in m.group(1).lower() or "yes" in m.group(1).lower()


def parsear_modelo_200(ruta: Path) -> dict:
    texto = _extraer_texto_pdf(ruta)
    resultado: dict = {}

    tipo_is = _buscar_importe(texto, r"tipo\s+de\s+gravamen[:\s]+(\d+[\.,]?\d*)")
    if tipo_is:
        resultado["tipo_is"] = tipo_is

    es_erd = _buscar_si_no(texto, r"empresa\s+de\s+reducida\s+dimensi[oó]n[:\s]+(si|no|yes)")
    if es_erd is not None:
        resultado["es_erd"] = es_erd

    bins = _buscar_importe(texto, r"base\s+imponible\s+negativa[^\d]+([\d\.,]+)")
    if bins:
        resultado["bins_total"] = bins

    ejercicio = re.search(r"ejercicio\s+(\d{4})", texto, re.IGNORECASE)
    if ejercicio:
        resultado["ejercicio"] = ejercicio.group(1)

    return resultado


def parsear_modelo_303(ruta: Path) -> dict:
    texto = _extraer_texto_pdf(ruta)
    resultado: dict = {}

    recc = _buscar_si_no(texto, r"criterio\s+de\s+caja[:\s]+(si|no)")
    if recc is not None:
        resultado["recc"] = recc

    trim = re.search(r"\b([1-4]T)\b|\btrimestre\s+([1-4])\b", texto, re.IGNORECASE)
    if trim:
        resultado["trimestre"] = trim.group(1) or f"{trim.group(2)}T"

    prorrata = _buscar_importe(texto, r"porcentaje\s+de\s+prorrata[:\s]+([\d\.,]+)")
    if prorrata:
        resultado["prorrata_pct"] = prorrata

    return resultado


def parsear_modelo_390(ruta: Path) -> dict:
    texto = _extraer_texto_pdf(ruta)
    resultado: dict = {}

    prorrata_def = _buscar_importe(
        texto, r"prorrata\s+definitiva[:\s]+([\d\.,]+)")
    if prorrata_def:
        resultado["prorrata_definitiva"] = prorrata_def

    ejercicio = re.search(r"ejercicio\s+(\d{4})", texto, re.IGNORECASE)
    if ejercicio:
        resultado["ejercicio"] = ejercicio.group(1)

    return resultado


def parsear_modelo_130(ruta: Path) -> dict:
    texto = _extraer_texto_pdf(ruta)
    resultado: dict = {}

    trim = re.search(r"\b([1-4]T)\b|\btrimestre\s+([1-4])\b", texto, re.IGNORECASE)
    if trim:
        resultado["trimestre"] = trim.group(1) or f"{trim.group(2)}T"

    pago = _buscar_importe(texto, r"pago\s+fraccionado[:\s]+([\d\.,]+)")
    if pago:
        resultado["pago_fraccionado"] = pago

    rendimiento = _buscar_importe(
        texto, r"rendimiento\s+neto[^\d]+([\d\.,]+)")
    if rendimiento:
        resultado["rendimiento_neto"] = rendimiento

    return resultado


def parsear_modelo_100(ruta: Path) -> dict:
    texto = _extraer_texto_pdf(ruta)
    resultado: dict = {}

    retencion = _buscar_importe(
        texto, r"tipo\s+de\s+retenci[oó]n[^:\d]{0,20}[:\s]+([\d\.,]+)")
    if retencion:
        resultado["retencion_pct"] = retencion

    pagos = _buscar_importe(
        texto, r"pagos\s+fraccionados\s+realizados[:\s]+([\d\.,]+)")
    if pagos:
        resultado["pagos_fraccionados_total"] = pagos

    return resultado


def parsear_modelo_111(ruta: Path) -> dict:
    texto = _extraer_texto_pdf(ruta)
    resultado: dict = {}
    trim = re.search(r"\b([1-4]T)\b", texto, re.IGNORECASE)
    if trim:
        resultado["trimestre"] = trim.group(1)
    retenciones = _buscar_importe(
        texto, r"retenciones\s+e\s+ingresos\s+a\s+cuenta[:\s]+([\d\.,]+)")
    if retenciones:
        resultado["retenciones_total"] = retenciones
        resultado["tiene_trabajadores"] = True
    return resultado


def parsear_modelo_115(ruta: Path) -> dict:
    """Retenciones e ingresos a cuenta — arrendamientos (trimestral)."""
    texto = _extraer_texto_pdf(ruta)
    resultado: dict = {}
    trim = re.search(r"\b([1-4]T)\b", texto, re.IGNORECASE)
    if trim:
        resultado["trimestre"] = trim.group(1)
    retenciones = _buscar_importe(
        texto, r"retenciones\s+e\s+ingresos\s+a\s+cuenta[:\s]+([\d\.,]+)")
    if retenciones is None:
        retenciones = _buscar_importe(texto, r"resultado\s+a\s+ingresar[:\s]+([\d\.,]+)")
    if retenciones:
        resultado["retenciones_total"] = retenciones
        resultado["tiene_arrendamientos"] = True
    return resultado


def parsear_modelo_180(ruta: Path) -> dict:
    """Resumen anual retenciones e ingresos a cuenta — arrendamientos."""
    texto = _extraer_texto_pdf(ruta)
    resultado: dict = {}
    retenciones = _buscar_importe(
        texto, r"retenciones\s+e\s+ingresos\s+a\s+cuenta[:\s]+([\d\.,]+)")
    if retenciones is None:
        retenciones = _buscar_importe(texto, r"importe\s+a\s+ingresar[:\s]+([\d\.,]+)")
    if retenciones:
        resultado["retenciones_total_anual"] = retenciones
        resultado["tiene_arrendamientos"] = True
    ejercicio = re.search(r"ejercicio\s+(\d{4})", texto, re.IGNORECASE)
    if ejercicio:
        resultado["ejercicio"] = ejercicio.group(1)
    return resultado
