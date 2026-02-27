"""Deteccion de documentos duplicados antes del registro contable.

Tres niveles de coincidencia:
- seguro:  mismo CIF + mismo numero_factura + misma fecha → rechazo automatico
- posible: mismo CIF + mismo importe (tolerancia 0.01) + fecha +-5 dias → cuarentena
- ninguno: no hay coincidencia suficiente → procesar normalmente

Funciones puras, sin mutaciones, sin efectos secundarios.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional

logger = logging.getLogger("sfce.duplicados")

# Tolerancias configurables
TOLERANCIA_IMPORTE = 0.01   # euros
VENTANA_DIAS = 5            # dias hacia cada lado para "posible"


# ---------------------------------------------------------------------------
# Tipos
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ResultadoDuplicado:
    """Resultado de la comprobacion de duplicado para un documento."""

    es_duplicado: bool
    tipo: str               # "seguro" | "posible" | "ninguno"
    documento_original: Optional[dict]
    razon: str


# ---------------------------------------------------------------------------
# Helpers privados
# ---------------------------------------------------------------------------

def _extraer_importe(doc: dict) -> Optional[float]:
    """Extrae el importe del documento; acepta 'total' o 'importe'."""
    valor = doc.get("total") if doc.get("total") is not None else doc.get("importe")
    if valor is None:
        return None
    try:
        return float(valor)
    except (ValueError, TypeError):
        return None


def _parsear_fecha(valor: Optional[str]) -> Optional[date]:
    """Convierte cadena de fecha a objeto date. Acepta ISO 8601 (YYYY-MM-DD)."""
    if not valor:
        return None
    try:
        if isinstance(valor, date) and not isinstance(valor, datetime):
            return valor
        if isinstance(valor, datetime):
            return valor.date()
        return datetime.strptime(str(valor)[:10], "%Y-%m-%d").date()
    except (ValueError, AttributeError):
        return None


def _coincide_seguro(nuevo: dict, existente: dict) -> bool:
    """Comprueba coincidencia exacta: CIF + numero_factura + fecha."""
    cif_nuevo = nuevo.get("cif_emisor")
    cif_existente = existente.get("cif_emisor")
    if not cif_nuevo or not cif_existente:
        return False

    num_nuevo = nuevo.get("numero_factura")
    num_existente = existente.get("numero_factura")
    if not num_nuevo or not num_existente:
        return False

    fecha_nueva = _parsear_fecha(nuevo.get("fecha"))
    fecha_existente = _parsear_fecha(existente.get("fecha"))
    if fecha_nueva is None or fecha_existente is None:
        return False

    return (
        cif_nuevo == cif_existente
        and num_nuevo == num_existente
        and fecha_nueva == fecha_existente
    )


def _coincide_posible(nuevo: dict, existente: dict) -> bool:
    """Comprueba coincidencia aproximada: CIF + importe (tolerancia) + fecha (ventana)."""
    cif_nuevo = nuevo.get("cif_emisor")
    cif_existente = existente.get("cif_emisor")
    if not cif_nuevo or not cif_existente or cif_nuevo != cif_existente:
        return False

    importe_nuevo = _extraer_importe(nuevo)
    importe_existente = _extraer_importe(existente)
    if importe_nuevo is None or importe_existente is None:
        return False
    if abs(importe_nuevo - importe_existente) > TOLERANCIA_IMPORTE:
        return False

    fecha_nueva = _parsear_fecha(nuevo.get("fecha"))
    fecha_existente = _parsear_fecha(existente.get("fecha"))
    if fecha_nueva is None or fecha_existente is None:
        return False

    delta = abs((fecha_nueva - fecha_existente).days)
    return delta <= VENTANA_DIAS


# ---------------------------------------------------------------------------
# API publica
# ---------------------------------------------------------------------------

def detectar_duplicado(
    datos_ocr: dict,
    documentos_existentes: list[dict],
) -> ResultadoDuplicado:
    """Analiza si datos_ocr es duplicado de algun documento existente.

    Prioridad: duplicado seguro > duplicado posible > ninguno.

    Args:
        datos_ocr: campos extraidos del documento nuevo (cif_emisor, numero_factura, fecha, total/importe).
        documentos_existentes: lista de documentos ya registrados con los mismos campos.

    Returns:
        ResultadoDuplicado con tipo y referencia al documento original si coincide.
    """
    if not datos_ocr.get("cif_emisor"):
        logger.debug("Sin CIF en datos_ocr — no se puede comprobar duplicado")
        return ResultadoDuplicado(
            es_duplicado=False,
            tipo="ninguno",
            documento_original=None,
            razon="CIF emisor ausente en el documento nuevo",
        )

    # --- Prioridad 1: duplicado seguro ---
    for existente in documentos_existentes:
        if _coincide_seguro(datos_ocr, existente):
            razon = (
                f"CIF={datos_ocr['cif_emisor']} + "
                f"numero={datos_ocr.get('numero_factura')} + "
                f"fecha={datos_ocr.get('fecha')} identicos"
            )
            logger.info("Duplicado seguro detectado: %s", razon)
            return ResultadoDuplicado(
                es_duplicado=True,
                tipo="seguro",
                documento_original=existente,
                razon=razon,
            )

    # --- Prioridad 2: duplicado posible ---
    for existente in documentos_existentes:
        if _coincide_posible(datos_ocr, existente):
            importe = _extraer_importe(datos_ocr)
            delta_dias = abs(
                (_parsear_fecha(datos_ocr.get("fecha")) - _parsear_fecha(existente.get("fecha"))).days
            )
            razon = (
                f"CIF={datos_ocr['cif_emisor']} + "
                f"importe≈{importe:.2f} EUR + "
                f"fecha a {delta_dias} dias"
            )
            logger.info("Duplicado posible detectado: %s", razon)
            return ResultadoDuplicado(
                es_duplicado=True,
                tipo="posible",
                documento_original=existente,
                razon=razon,
            )

    return ResultadoDuplicado(
        es_duplicado=False,
        tipo="ninguno",
        documento_original=None,
        razon="",
    )


def filtrar_duplicados_batch(
    documentos_nuevos: list[dict],
    documentos_existentes: list[dict],
) -> tuple[list[dict], list[dict], list[dict]]:
    """Clasifica una lista de documentos nuevos en tres categorias.

    Args:
        documentos_nuevos: lista de documentos a clasificar.
        documentos_existentes: documentos ya registrados como referencia.

    Returns:
        Tupla (unicos, duplicados_seguros, posibles_duplicados).
        Las listas originales no se modifican.
    """
    unicos: list[dict] = []
    duplicados_seguros: list[dict] = []
    posibles_duplicados: list[dict] = []

    for doc in documentos_nuevos:
        resultado = detectar_duplicado(doc, documentos_existentes)
        if resultado.tipo == "seguro":
            duplicados_seguros = duplicados_seguros + [doc]
        elif resultado.tipo == "posible":
            posibles_duplicados = posibles_duplicados + [doc]
        else:
            unicos = unicos + [doc]

    logger.info(
        "Batch duplicados: %d unicos, %d seguros, %d posibles",
        len(unicos), len(duplicados_seguros), len(posibles_duplicados),
    )
    return unicos, duplicados_seguros, posibles_duplicados


def generar_informe_duplicados(resultados: list[ResultadoDuplicado]) -> str:
    """Genera un informe de texto con estadisticas de duplicados.

    Args:
        resultados: lista de ResultadoDuplicado obtenidos del proceso de deteccion.

    Returns:
        Cadena de texto formateada con resumen y detalle.
    """
    total = len(resultados)
    seguros = [r for r in resultados if r.tipo == "seguro"]
    posibles = [r for r in resultados if r.tipo == "posible"]
    ningunos = [r for r in resultados if r.tipo == "ninguno"]

    lineas = [
        "=== INFORME DE DUPLICADOS ===",
        f"Total documentos analizados : {total}",
        f"  Duplicados seguros        : {len(seguros)}",
        f"  Duplicados posibles       : {len(posibles)}",
        f"  Sin duplicado             : {len(ningunos)}",
    ]

    if seguros:
        lineas.append("")
        lineas.append("-- Duplicados seguros (rechazo automatico) --")
        for r in seguros:
            lineas.append(f"  {r.razon}")

    if posibles:
        lineas.append("")
        lineas.append("-- Duplicados posibles (revisar en cuarentena) --")
        for r in posibles:
            lineas.append(f"  {r.razon}")

    return "\n".join(lineas)
