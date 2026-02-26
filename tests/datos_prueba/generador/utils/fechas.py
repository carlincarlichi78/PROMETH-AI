"""
Utilidades de distribucion temporal para el generador de datos de prueba contable.
Permite distribuir documentos a lo largo del ano con pesos estacionales realistas.
"""

import random
from datetime import date, timedelta
from typing import List, Optional


# Pesos de actividad economica por mes (suma ~1.0)
PESOS_MES: dict[int, float] = {
    1: 0.08,   # enero: inicio de ano, menos actividad
    2: 0.06,   # febrero: mes corto, menor actividad
    3: 0.10,   # marzo: cierre T1, repunte
    4: 0.08,   # abril: inicio T2
    5: 0.08,   # mayo
    6: 0.10,   # junio: cierre T2
    7: 0.07,   # julio: verano, menos facturacion B2B
    8: 0.05,   # agosto: vacaciones, minimo
    9: 0.08,   # septiembre: vuelta, cierre T3
    10: 0.10,  # octubre: inicio T4
    11: 0.09,  # noviembre
    12: 0.11,  # diciembre: cierre anual, maximo
}


def _ultimo_dia_mes(anio: int, mes: int) -> int:
    """Devuelve el ultimo dia del mes dado."""
    if mes == 12:
        return 31
    return (date(anio, mes + 1, 1) - timedelta(days=1)).day


def generar_fecha_en_mes(anio: int, mes: int, rng: Optional[random.Random] = None) -> date:
    """
    Genera una fecha aleatoria laborable dentro del mes indicado.
    Evita sabados (weekday=5) y domingos (weekday=6).
    Hasta 50 intentos; si no encuentra dia laborable, devuelve el dia 15.
    """
    generador = rng or random
    ultimo_dia = _ultimo_dia_mes(anio, mes)

    for _ in range(50):
        dia = generador.randint(1, ultimo_dia)
        fecha = date(anio, mes, dia)
        if fecha.weekday() < 5:
            return fecha

    # Fallback: dia 15 (casi siempre laborable salvo festivos puntuales)
    return date(anio, mes, 15)


def distribuir_fechas(
    anio: int,
    total_docs: int,
    rng: Optional[random.Random] = None,
    pesos: Optional[dict] = None,
    meses_activos: Optional[List[int]] = None,
) -> List[date]:
    """
    Distribuye N fechas a lo largo del ano usando pesos por mes.

    Parametros:
        anio: ano de los documentos
        total_docs: numero total de documentos a distribuir
        rng: instancia de Random para reproducibilidad
        pesos: dict mes->peso personalizado (usa PESOS_MES si es None)
        meses_activos: lista de meses habilitados (ej. [4,5,6,7,8,9,10] para chiringuito).
                       Si es None, usa todos los meses.

    Retorna lista ordenada de fechas.
    """
    generador = rng or random
    pesos_base = pesos or PESOS_MES

    # Filtrar por meses activos
    if meses_activos:
        meses_validos = [m for m in range(1, 13) if m in meses_activos]
    else:
        meses_validos = list(range(1, 13))

    # Extraer y renormalizar pesos para los meses validos
    pesos_filtrados = {m: pesos_base.get(m, 0.0) for m in meses_validos}
    suma_pesos = sum(pesos_filtrados.values())

    if suma_pesos == 0:
        raise ValueError(f"Los meses activos {meses_activos} tienen peso total 0")

    pesos_norm = {m: p / suma_pesos for m, p in pesos_filtrados.items()}

    # Asignar documentos por mes proporcionalmente
    docs_por_mes: dict[int, int] = {}
    asignados = 0
    meses_lista = list(meses_validos)

    for i, mes in enumerate(meses_lista[:-1]):
        cantidad = round(pesos_norm[mes] * total_docs)
        docs_por_mes[mes] = cantidad
        asignados += cantidad

    # El ultimo mes recibe el resto para que el total sea exacto
    ultimo_mes = meses_lista[-1]
    docs_por_mes[ultimo_mes] = total_docs - asignados

    # Generar fechas para cada mes
    todas_fechas: List[date] = []
    for mes, cantidad in docs_por_mes.items():
        for _ in range(cantidad):
            fecha = generar_fecha_en_mes(anio, mes, generador)
            todas_fechas.append(fecha)

    # Mezclar para romper el orden por mes antes de ordenar
    generador.shuffle(todas_fechas)
    todas_fechas.sort()

    return todas_fechas


def trimestre_de_fecha(fecha: date) -> str:
    """Devuelve el trimestre ('T1'-'T4') al que pertenece la fecha."""
    trimestre = (fecha.month - 1) // 3 + 1
    return f"T{trimestre}"


def fechas_mensuales(
    anio: int,
    meses: Optional[List[int]] = None,
    dia: int = 28,
) -> List[date]:
    """
    Genera una fecha fija por mes, util para documentos recurrentes
    (nominas, suministros, cuotas). Por defecto dia 28 de cada mes.

    Parametros:
        anio: ano
        meses: lista de meses (default 1-12)
        dia: dia del mes (se ajusta al ultimo dia si el mes es mas corto)
    """
    meses_seleccionados = meses or list(range(1, 13))
    resultado: List[date] = []

    for mes in meses_seleccionados:
        ultimo = _ultimo_dia_mes(anio, mes)
        dia_real = min(dia, ultimo)
        resultado.append(date(anio, mes, dia_real))

    return resultado
