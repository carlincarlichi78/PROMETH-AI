"""Sector Brain — benchmarks anónimos colectivos de empresas del mismo CNAE.

Solo se muestran percentiles cuando hay al menos MIN_EMPRESAS activas con el mismo
CNAE (anonimato colectivo). Nunca se exponen datos individuales.
"""
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from sfce.analytics.modelos_analiticos import FactCaja, FactCompra
from sfce.db.modelos import Empresa


MIN_EMPRESAS = 5  # mínimo para mostrar benchmarks anónimos

KPI_SOPORTADOS = {"ticket_medio"}


def _percentil(valores_ordenados: list[float], p: float) -> float:
    """Percentil con interpolación lineal (equivalente a numpy.percentile).

    Usa el método estándar estadístico: índice real = p/100 * (n-1), luego
    interpolación lineal entre los dos valores adyacentes. Con n=5 y P25,
    idx=1.0 → devuelve valores_ordenados[1] exacto (no valores_ordenados[1]
    como antes, que era correcto en ese caso, pero con p=50 e n=5 devolvía
    valores_ordenados[2] en lugar del interpolado entre índices 2 y 3).
    """
    n = len(valores_ordenados)
    if n == 0:
        return 0.0
    if n == 1:
        return valores_ordenados[0]
    idx = p / 100.0 * (n - 1)
    lower = int(idx)
    upper = min(lower + 1, n - 1)
    fraccion = idx - lower
    return valores_ordenados[lower] * (1 - fraccion) + valores_ordenados[upper] * fraccion


def calcular_percentiles_sector(sesion: Session, cnae: str, kpi: str) -> dict | None:
    """Calcula percentiles P25/P50/P75 del KPI para todas las empresas del mismo CNAE.

    Retorna None si el KPI no está soportado o no hay suficientes datos para garantizar anonimato.
    """
    if kpi not in KPI_SOPORTADOS:
        return None  # KPI no soportado

    empresas = sesion.execute(
        select(Empresa.id).where(Empresa.cnae == cnae).where(Empresa.activa == True)  # noqa: E712
    ).scalars().all()

    if len(empresas) < MIN_EMPRESAS:
        return None  # no hay suficientes datos para anonimato

    valores = []
    for emp_id in empresas:
        val = _calcular_kpi_empresa(sesion, emp_id, kpi)
        if val is not None:
            valores.append(val)

    if len(valores) < MIN_EMPRESAS:
        return None

    valores.sort()
    return {
        "p25": _percentil(valores, 25),
        "p50": _percentil(valores, 50),
        "p75": _percentil(valores, 75),
        "n_empresas": len(valores),
    }


def posicion_en_sector(valor: float, percentiles: dict) -> dict:
    """Calcula en qué percentil está el valor dado y asigna color semáforo."""
    if valor <= percentiles["p25"]:
        return {"percentil": 25, "etiqueta": "cuartil inferior", "color": "rojo"}
    if valor <= percentiles["p50"]:
        return {"percentil": 50, "etiqueta": "segunda mitad", "color": "amarillo"}
    if valor <= percentiles["p75"]:
        return {"percentil": 75, "etiqueta": "tercer cuartil", "color": "verde"}
    return {"percentil": 90, "etiqueta": "cuartil superior", "color": "verde"}


def calcular_kpi_empresa(sesion: Session, empresa_id: int, kpi: str) -> float | None:
    """Calcula un KPI concreto para una empresa (interfaz pública para el endpoint)."""
    return _calcular_kpi_empresa(sesion, empresa_id, kpi)


def _calcular_kpi_empresa(sesion: Session, empresa_id: int, kpi: str) -> float | None:
    """Implementación interna del cálculo de KPI por empresa."""
    if kpi == "ticket_medio":
        resultado = sesion.execute(
            select(func.avg(FactCaja.ticket_medio)).where(FactCaja.empresa_id == empresa_id)
        ).scalar()
        return float(resultado) if resultado else None
    return None
