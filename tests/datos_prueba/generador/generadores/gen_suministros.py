"""
Generador de facturas de suministros (electricidad, agua, gas, telefono)
para el generador de datos de prueba contable.
Produce DocGenerado listos para renderizar a PDF via Jinja2 + weasyprint.
"""

import random
import sys
from datetime import date
from pathlib import Path
from typing import List, Optional

DIR_GENERADOR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DIR_GENERADOR))

from generadores.gen_facturas import DocGenerado, _slug
from utils.fechas import generar_fecha_en_mes, _ultimo_dia_mes
from utils.importes import _redondear


# ---------------------------------------------------------------------------
# Constantes de estacionalidad
# ---------------------------------------------------------------------------

# Factores de variacion estacional por tipo de suministro y mes
# Valor 1.0 = sin variacion; >1.0 = aumento; <1.0 = reduccion
_ESTACIONALIDAD: dict[str, dict[str, dict[int, float]]] = {
    "electricidad": {
        # Restaurantes: pico en verano por aire acondicionado y mayor actividad
        "restaurante": {
            1: 0.90, 2: 0.90, 3: 0.95, 4: 1.00, 5: 1.05,
            6: 1.30, 7: 1.30, 8: 1.30, 9: 1.30, 10: 1.00,
            11: 0.95, 12: 0.90,
        },
        # Oficinas: pico en invierno por calefaccion electrica
        "default": {
            1: 1.20, 2: 1.20, 3: 1.00, 4: 0.90, 5: 0.90,
            6: 1.00, 7: 1.05, 8: 0.80, 9: 0.90, 10: 1.00,
            11: 1.10, 12: 1.20,
        },
    },
    "gas": {
        # Gas: pico en invierno para calefaccion y agua caliente
        "default": {
            1: 1.50, 2: 1.50, 3: 1.20, 4: 0.80, 5: 0.70,
            6: 0.70, 7: 0.70, 8: 0.70, 9: 0.80, 10: 1.00,
            11: 1.50, 12: 1.50,
        },
    },
    "agua": {
        # Agua: ligero pico en verano por riego, limpieza y mayor ocupacion
        "default": {
            1: 0.85, 2: 0.85, 3: 0.90, 4: 0.95, 5: 1.00,
            6: 1.10, 7: 1.20, 8: 1.20, 9: 1.10, 10: 1.00,
            11: 0.90, 12: 0.85,
        },
    },
    "telefono": {
        # Telefono: tarifa plana, sin variacion estacional
        "default": {m: 1.0 for m in range(1, 13)},
    },
}

# IVA por tipo de suministro (segun normativa espanola 2025)
_IVA_SUMINISTRO: dict[str, int] = {
    "electricidad": 21,
    "gas": 21,
    "agua": 10,
    "telefono": 21,
}

# Contador global de facturas por proveedor para numerar correlativas
_contadores_suministro: dict[str, int] = {}


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _factor_estacional(tipo: str, mes: int, tipo_entidad: str) -> float:
    """Devuelve el factor de variacion estacional para un suministro y mes."""
    tabla_tipo = _ESTACIONALIDAD.get(tipo, {})
    if tipo_entidad == "restaurante" and "restaurante" in tabla_tipo:
        return tabla_tipo["restaurante"].get(mes, 1.0)
    return tabla_tipo.get("default", {}).get(mes, 1.0)


def _generar_numero_suministro(slug_proveedor: str, anio: int, mes: int) -> str:
    """Genera un numero de factura realista para un recibo de suministro."""
    clave = f"{slug_proveedor}-{anio}"
    _contadores_suministro[clave] = _contadores_suministro.get(clave, 0) + 1
    seq = _contadores_suministro[clave]
    return f"REC-{anio}{mes:02d}-{seq:04d}"


def _conceptos_suministro(
    tipo: str,
    importe_base: float,
    iva_tipo: int,
    rng: random.Random,
) -> tuple[list[dict], float, float, float]:
    """
    Genera los conceptos desglosados de un recibo de suministro.

    Retorna: (conceptos, subtotal, iva_cuota, total)
    Los conceptos incluyen termino fijo, termino variable y, si aplica,
    impuesto electrico (electricidad y gas).
    """
    conceptos = []

    if tipo == "electricidad":
        # Desglose tipico de factura electrica
        termino_fijo = _redondear(importe_base * 0.30)
        termino_variable = _redondear(importe_base * 0.55)
        impuesto_electrico = _redondear(importe_base * 0.05)  # ~5.11% sobre potencia
        subtotal = _redondear(termino_fijo + termino_variable + impuesto_electrico)
        conceptos = [
            {"concepto": "Termino de potencia (termino fijo)", "importe": termino_fijo},
            {"concepto": "Termino de energia (consumo kWh)", "importe": termino_variable},
            {"concepto": "Impuesto sobre electricidad (5,11%)", "importe": impuesto_electrico},
        ]
    elif tipo == "gas":
        termino_fijo = _redondear(importe_base * 0.25)
        termino_variable = _redondear(importe_base * 0.75)
        subtotal = _redondear(termino_fijo + termino_variable)
        conceptos = [
            {"concepto": "Cuota fija de suministro", "importe": termino_fijo},
            {"concepto": "Consumo de gas (m3)", "importe": termino_variable},
        ]
    elif tipo == "agua":
        termino_fijo = _redondear(importe_base * 0.20)
        termino_variable = _redondear(importe_base * 0.65)
        canon_saneamiento = _redondear(importe_base * 0.15)
        subtotal = _redondear(termino_fijo + termino_variable + canon_saneamiento)
        conceptos = [
            {"concepto": "Cuota de servicio (termino fijo)", "importe": termino_fijo},
            {"concepto": "Consumo de agua (m3)", "importe": termino_variable},
            {"concepto": "Canon de saneamiento", "importe": canon_saneamiento},
        ]
    else:
        # Telefono: linea y datos
        linea_movil = _redondear(importe_base * 0.60)
        datos_internet = _redondear(importe_base * 0.40)
        subtotal = _redondear(linea_movil + datos_internet)
        conceptos = [
            {"concepto": "Cuota tarifa plana movil y datos", "importe": linea_movil},
            {"concepto": "Servicio de internet y fibra optica", "importe": datos_internet},
        ]

    iva_cuota = _redondear(subtotal * iva_tipo / 100)
    total = _redondear(subtotal + iva_cuota)
    return conceptos, subtotal, iva_cuota, total


def _periodo_factura(anio: int, mes: int) -> dict[str, str]:
    """Genera el periodo de facturacion (desde primer dia hasta ultimo dia del mes)."""
    primer_dia = date(anio, mes, 1)
    ultimo_dia = _ultimo_dia_mes(anio, mes)
    return {
        "desde": primer_dia.isoformat(),
        "hasta": date(anio, mes, ultimo_dia).isoformat(),
    }


# ---------------------------------------------------------------------------
# Generador principal
# ---------------------------------------------------------------------------

def generar_suministros(
    entidad: dict,
    anio: int,
    rng: random.Random,
) -> List[DocGenerado]:
    """
    Genera facturas mensuales de suministros segun entidad["gastos_recurrentes"]["suministros"].

    Para cada suministro definido (electricidad, agua, gas, telefono) genera 12 facturas
    mensuales, aplicando variacion estacional segun tipo y sector de la entidad.
    Las entidades con meses_activos reducidos (ej: chiringuito) solo generan facturas
    en sus meses de actividad.
    """
    docs: List[DocGenerado] = []
    suministros = entidad.get("gastos_recurrentes", {}).get("suministros", [])
    if not suministros:
        return docs

    tipo_entidad = entidad.get("tipo", "sl")
    meses_activos: Optional[List[int]] = entidad.get("meses_activos")
    # Si meses_activos es la lista completa (1-12), tratar como sin restriccion
    if meses_activos and set(meses_activos) == set(range(1, 13)):
        meses_activos = None

    nombre_entidad = entidad.get("nombre", "")
    cif_entidad = entidad.get("cif", "")
    direccion_entidad = entidad.get("direccion", "")

    for suministro in suministros:
        tipo = suministro.get("tipo", "")
        nombre_proveedor = suministro.get("proveedor", "")
        importe_rango = suministro.get("importe_rango", [50, 100])
        # IVA: usar el del YAML si existe, si no el por defecto segun tipo
        iva_tipo = suministro.get("iva", _IVA_SUMINISTRO.get(tipo, 21))

        importe_min = float(importe_rango[0])
        importe_max = float(importe_rango[1])
        slug_proveedor = _slug(nombre_proveedor)

        meses = meses_activos if meses_activos else list(range(1, 13))

        for mes in meses:
            # Importe base con variacion estacional
            factor = _factor_estacional(tipo, mes, tipo_entidad)
            base_mes_min = importe_min * factor
            base_mes_max = importe_max * factor

            # Variacion aleatoria ±10%
            variacion = rng.uniform(0.90, 1.10)
            importe_base = _redondear(
                rng.uniform(base_mes_min, base_mes_max) * variacion
            )

            # Generar fecha de factura (entre dia 5 y 28 del mes siguiente para
            # simular fecha de emision real del proveedor; usamos mes actual
            # con dia 28 para simplicidad)
            fecha = generar_fecha_en_mes(anio, mes, rng)
            numero = _generar_numero_suministro(slug_proveedor, anio, mes)
            periodo = _periodo_factura(anio, mes)

            conceptos, subtotal, iva_cuota, total = _conceptos_suministro(
                tipo, importe_base, iva_tipo, rng
            )

            nombre_archivo = f"{anio}-{mes:02d}_suministro_{tipo}_{slug_proveedor}.pdf"

            datos_plantilla = {
                "numero_factura": numero,
                "fecha_factura": fecha.isoformat(),
                "proveedor": {
                    "nombre": nombre_proveedor,
                    "slug": slug_proveedor,
                },
                "cliente": {
                    "nombre": nombre_entidad,
                    "cif": cif_entidad,
                    "direccion": direccion_entidad,
                },
                "tipo": tipo,
                "periodo": periodo,
                "conceptos": conceptos,
                "subtotal": subtotal,
                "iva_tipo": iva_tipo,
                "iva_cuota": iva_cuota,
                "total": total,
            }

            metadatos = {
                "tipo": "recibo_suministro",
                "subtipo": tipo,
                "fecha": fecha.isoformat(),
                "mes": mes,
                "anio": anio,
                "proveedor": nombre_proveedor,
                "base": subtotal,
                "iva_tipo": iva_tipo,
                "iva_cuota": iva_cuota,
                "total": total,
            }

            docs.append(DocGenerado(
                archivo=nombre_archivo,
                tipo="recibo_suministro",
                subtipo=tipo,
                plantilla="recibo_suministro.html",
                css_variante="corporativo",
                datos_plantilla=datos_plantilla,
                metadatos=metadatos,
                error_inyectado=None,
                edge_case=None,
            ))

    return docs
