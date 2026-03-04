"""Deteccion de facturas recurrentes faltantes (Task 44 Fase E).

Identifica proveedores con facturacion periodica y avisa cuando falta
una factura esperada. Util para detectar olvidos antes del cierre.

Funciones puras: sin IO, sin BD, sin efectos secundarios.
"""
from __future__ import annotations

import logging
import statistics
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

from sfce.core.nombres import _normalizar_fecha

logger = logging.getLogger("sfce.recurrentes")

# Umbral de desviacion estandar para considerar un patron recurrente
UMBRAL_DESVIACION_DIAS = 15.0


# ---------------------------------------------------------------------------
# Tipos
# ---------------------------------------------------------------------------

@dataclass
class PatronRecurrente:
    """Patron de facturacion periodica detectado para un proveedor."""
    proveedor_cif: str
    proveedor_nombre: str
    frecuencia_dias: int
    ultima_fecha: str       # ISO 8601: YYYY-MM-DD
    importe_tipico: float
    ocurrencias: int
    confianza: float        # 0.0 – 1.0


# ---------------------------------------------------------------------------
# Funciones auxiliares privadas
# ---------------------------------------------------------------------------

def _extraer_importe(factura: dict) -> float:
    """Extrae el importe de una factura soportando los campos 'total' e 'importe'."""
    if "total" in factura:
        return float(factura["total"])
    if "importe" in factura:
        return float(factura["importe"])
    return 0.0


def _calcular_confianza(desviacion: float) -> float:
    """Calcula confianza inversamente proporcional a la desviacion.

    - desviacion = 0 → confianza = 1.0
    - desviacion = UMBRAL (15 dias) → confianza ≈ 0.0
    - Se clampea entre 0 y 1.
    """
    confianza = 1.0 - (desviacion / UMBRAL_DESVIACION_DIAS)
    return max(0.0, min(1.0, confianza))


def _analizar_proveedor(
    cif: str,
    facturas_prov: list[dict],
    min_ocurrencias: int,
) -> Optional[PatronRecurrente]:
    """Analiza las facturas de un proveedor y retorna su patron si es recurrente.

    Retorna None si no cumple los criterios de recurrencia.
    """
    if len(facturas_prov) < min_ocurrencias:
        return None

    # Ordenar fechas cronologicamente (normalizar antes de parsear)
    fechas_raw = []
    for f in facturas_prov:
        fecha_norm = _normalizar_fecha(f.get("fecha", ""))
        if fecha_norm and fecha_norm != "SIN-FECHA" and len(fecha_norm) == 8:
            try:
                fechas_raw.append(date.fromisoformat(f"{fecha_norm[:4]}-{fecha_norm[4:6]}-{fecha_norm[6:]}"))
            except ValueError:
                pass
    fechas = sorted(fechas_raw)

    # Calcular intervalos entre facturas consecutivas
    intervalos = [
        (fechas[i + 1] - fechas[i]).days
        for i in range(len(fechas) - 1)
    ]

    if len(intervalos) < 1:
        return None

    frecuencia_media = statistics.mean(intervalos)

    # Para la desviacion necesitamos al menos 2 intervalos
    if len(intervalos) >= 2:
        desviacion = statistics.stdev(intervalos)
    else:
        # Con un solo intervalo no hay variabilidad: desviacion = 0
        desviacion = 0.0

    if desviacion >= UMBRAL_DESVIACION_DIAS:
        return None

    # Calcular importe tipico
    importes = [_extraer_importe(f) for f in facturas_prov]
    importe_tipico = statistics.mean(importes)

    # Tomar el nombre del proveedor de la factura mas reciente
    facturas_ord = sorted(facturas_prov, key=lambda f: f["fecha"])
    nombre = facturas_ord[-1].get("nombre_emisor", "")

    return PatronRecurrente(
        proveedor_cif=cif,
        proveedor_nombre=nombre,
        frecuencia_dias=round(frecuencia_media),
        ultima_fecha=fechas[-1].isoformat(),
        importe_tipico=importe_tipico,
        ocurrencias=len(facturas_prov),
        confianza=_calcular_confianza(desviacion),
    )


# ---------------------------------------------------------------------------
# API publica
# ---------------------------------------------------------------------------

def detectar_patrones_recurrentes(
    facturas: list[dict],
    min_ocurrencias: int = 3,
) -> list[PatronRecurrente]:
    """Detecta patrones de facturacion periodica a partir de una lista de facturas.

    Args:
        facturas: Lista de dicts con campos cif_emisor, fecha (YYYY-MM-DD),
                  total o importe, nombre_emisor.
        min_ocurrencias: Minimo de facturas para considerar un patron.

    Returns:
        Lista de PatronRecurrente ordenada por confianza descendente.
    """
    if not facturas:
        return []

    # Agrupar por CIF
    por_cif: dict[str, list[dict]] = {}
    for factura in facturas:
        cif = factura.get("cif_emisor", "")
        if cif not in por_cif:
            por_cif[cif] = []
        por_cif[cif].append(factura)

    patrones: list[PatronRecurrente] = []
    for cif, facturas_prov in por_cif.items():
        patron = _analizar_proveedor(cif, facturas_prov, min_ocurrencias)
        if patron is not None:
            patrones.append(patron)

    # Ordenar por confianza descendente
    return sorted(patrones, key=lambda p: p.confianza, reverse=True)


def detectar_faltantes(
    patrones: list[PatronRecurrente],
    fecha_corte: Optional[str] = None,
) -> list[dict]:
    """Detecta facturas esperadas que aun no han llegado.

    Para cada patron, calcula la proxima fecha esperada
    (ultima_fecha + frecuencia_dias). Si esa fecha ya paso respecto
    a fecha_corte, la factura se considera faltante.

    Args:
        patrones: Lista de PatronRecurrente detectados.
        fecha_corte: Fecha de referencia ISO 8601. Default: hoy.

    Returns:
        Lista de dicts con: proveedor_cif, proveedor_nombre, fecha_esperada,
        dias_retraso, importe_estimado, confianza.
    """
    if not patrones:
        return []

    corte = (
        date.fromisoformat(fecha_corte) if fecha_corte else date.today()
    )

    faltantes: list[dict] = []
    for patron in patrones:
        ultima = date.fromisoformat(patron.ultima_fecha)
        proxima = ultima + timedelta(days=patron.frecuencia_dias)

        if proxima < corte:
            dias_retraso = (corte - proxima).days
            faltantes.append({
                "proveedor_cif": patron.proveedor_cif,
                "proveedor_nombre": patron.proveedor_nombre,
                "fecha_esperada": proxima.isoformat(),
                "dias_retraso": dias_retraso,
                "importe_estimado": patron.importe_tipico,
                "confianza": patron.confianza,
            })

    return faltantes


def generar_alertas_recurrentes(
    facturas: list[dict],
    fecha_corte: Optional[str] = None,
    min_ocurrencias: int = 3,
) -> dict:
    """Orquesta la deteccion de patrones y facturas faltantes.

    Args:
        facturas: Lista de facturas (misma estructura que detectar_patrones_recurrentes).
        fecha_corte: Fecha de referencia ISO 8601. Default: hoy.
        min_ocurrencias: Minimo de facturas para considerar un patron.

    Returns:
        Dict con: patrones (list), faltantes (list),
                  total_patrones (int), total_faltantes (int).
    """
    patrones = detectar_patrones_recurrentes(facturas, min_ocurrencias=min_ocurrencias)
    faltantes = detectar_faltantes(patrones, fecha_corte=fecha_corte)

    return {
        "patrones": patrones,
        "faltantes": faltantes,
        "total_patrones": len(patrones),
        "total_faltantes": len(faltantes),
    }
