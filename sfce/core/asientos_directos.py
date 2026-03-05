"""Creacion de asientos directos (sin factura) en FacturaScripts.

Soporta: nominas, bancarios, RLC (seguros sociales), impuestos/tasas.
Usa POST asientos + POST partidas en lugar de crearFactura*.
"""
from pathlib import Path
from typing import Any

import yaml

from .fs_api import api_post
from .logger import crear_logger

logger = crear_logger("asientos_directos")

# Ruta al YAML con plantillas de partidas por tipo
RUTA_SUBCUENTAS_TIPOS = Path(__file__).parent.parent.parent / "reglas" / "subcuentas_tipos.yaml"

# Mapeo tipo documento -> clave YAML por defecto
_TIPO_A_YAML = {
    "NOM": "nomina_devengo",
    "RLC": "rlc_devengo",
    "IMP": "impuesto_tasa",
}

# Subtipos bancarios validos
_SUBTIPOS_BANCARIOS = {"comision", "seguro", "renting", "intereses",
                       "transferencia", "impuesto_tasa", "tasa", "cuota"}


def _cargar_plantillas() -> dict:
    """Carga las plantillas de subcuentas desde YAML."""
    with open(RUTA_SUBCUENTAS_TIPOS, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolver_tipo_asiento(doc: dict) -> str:
    """Determina la clave YAML del tipo de asiento a partir del documento.

    Args:
        doc: documento con 'tipo' (NOM/BAN/RLC/IMP) y 'datos_extraidos'

    Returns:
        Clave del YAML (ej: 'nomina_devengo', 'bancario_comision')

    Raises:
        ValueError: si el tipo de documento no esta soportado
    """
    tipo = doc.get("tipo", "")

    if tipo == "BAN":
        subtipo = doc.get("datos_extraidos", {}).get("subtipo", "comision")
        clave = f"bancario_{subtipo}"
        if subtipo not in _SUBTIPOS_BANCARIOS:
            raise ValueError(f"Subtipo bancario no soportado: {subtipo}")
        return clave

    clave = _TIPO_A_YAML.get(tipo)
    if not clave:
        raise ValueError(f"Tipo documento no soportado para asiento directo: {tipo}")

    return clave


def _construir_partidas_desde_plantilla(plantilla: list[dict], datos: dict) -> list[dict]:
    """Construye partidas a partir de una plantilla YAML y los datos extraidos.

    Args:
        plantilla: lista de dicts con subcuenta, lado, campo_importe, concepto
        datos: dict con los importes reales

    Returns:
        Lista de partidas con codsubcuenta, debe, haber, concepto
    """
    partidas = []
    for p in plantilla:
        importe = datos.get(p["campo_importe"], 0)
        partida = {
            "codsubcuenta": p["subcuenta"],
            "debe": round(importe, 2) if p["lado"] == "debe" else 0,
            "haber": round(importe, 2) if p["lado"] == "haber" else 0,
            "concepto": p["concepto"],
        }
        partidas.append(partida)
    return partidas


def construir_partidas_nomina(datos: dict) -> list[dict]:
    """Construye partidas para devengo de nomina.

    Compatible con esquema V3.2 (campos en metadata{}) y legacy (campos en raiz).
    Patron is not None para no perder valores cero (ej: empleado exento de IRPF).

    Args:
        datos: dict con campos de nomina en metadata{} (V3.2) o en raiz (legacy)

    Returns:
        Lista de 4 partidas (6400 DEBE / 4751+4760+4650 HABER)

    Raises:
        ValueError: si bruto != irpf + ss_trabajador + neto
    """
    meta = datos.get("metadata") or {}

    def _resolver(campo_meta: str, campo_legacy: str) -> float:
        v = meta.get(campo_meta)
        if v is not None:
            return round(float(v), 2)
        v = datos.get(campo_legacy)
        return round(float(v), 2) if v is not None else 0.0

    bruto = _resolver("bruto", "bruto")
    irpf  = _resolver("irpf_importe", "retenciones_irpf")
    ss    = _resolver("ss_trabajador", "aportaciones_ss_trabajador")
    neto  = _resolver("neto", "neto")

    suma_haber = round(irpf + ss + neto, 2)
    if abs(bruto - suma_haber) > 0.01:
        raise ValueError(
            f"Nomina no cuadra: bruto={bruto} != irpf({irpf}) + ss({ss}) + neto({neto}) = {suma_haber}"
        )

    # Normalizar a nombres legacy que usa la plantilla YAML
    datos_normalizados = {
        **datos,
        "bruto": bruto,
        "retenciones_irpf": irpf,
        "aportaciones_ss_trabajador": ss,
        "neto": neto,
    }
    plantillas = _cargar_plantillas()
    return _construir_partidas_desde_plantilla(
        plantillas["nomina_devengo"]["partidas"], datos_normalizados
    )


def construir_partidas_bancario(datos: dict, subtipo: str) -> list[dict]:
    """Construye partidas para recibo bancario.

    Args:
        datos: dict con importe (y base_imponible/iva_importe para renting)
        subtipo: comision, seguro, renting, intereses

    Returns:
        Lista de partidas segun subtipo

    Raises:
        ValueError: si el subtipo no esta soportado
    """
    if subtipo not in _SUBTIPOS_BANCARIOS:
        raise ValueError(f"Subtipo bancario no soportado: {subtipo}")

    # Renting: OCR extrae importe=base y total=base+IVA,
    # pero plantilla espera base_imponible, iva_importe, importe(=total)
    if subtipo == "renting":
        importe_raw = datos.get("importe", 0)
        total_raw = datos.get("total", 0)
        if not datos.get("base_imponible") and importe_raw and total_raw:
            datos = {**datos}
            datos["base_imponible"] = importe_raw
            datos["iva_importe"] = round(total_raw - importe_raw, 2)
            datos["importe"] = total_raw

    clave = f"bancario_{subtipo}"
    plantillas = _cargar_plantillas()
    return _construir_partidas_desde_plantilla(plantillas[clave]["partidas"], datos)


def construir_partidas_rlc(datos: dict) -> list[dict]:
    """Construye partidas para devengo SS empresa (RLC).

    Compatible con esquema V3.2 (campos en metadata{}) y legacy (campos en raiz).
    Patron is not None para no perder valores cero.

    Args:
        datos: dict con cuota_empresarial en metadata{} (V3.2) o en raiz (legacy)

    Returns:
        Lista de 2 partidas (6420 DEBE / 4760 HABER)
    """
    meta = datos.get("metadata") or {}

    def _resolver(campo: str):
        v = meta.get(campo)
        if v is not None:
            return v
        return datos.get(campo)

    datos_normalizados = {
        **datos,
        "base_cotizacion": _resolver("base_cotizacion"),
        "cuota_empresarial": _resolver("cuota_empresarial"),
        "cuota_obrera": _resolver("cuota_obrera"),
    }
    plantillas = _cargar_plantillas()
    return _construir_partidas_desde_plantilla(
        plantillas["rlc_devengo"]["partidas"], datos_normalizados
    )


def construir_partidas_impuesto(datos: dict) -> list[dict]:
    """Construye partidas para impuesto/tasa.

    Args:
        datos: dict con importe

    Returns:
        Lista de 2 partidas (6310 DEBE / 5720 HABER)
    """
    plantillas = _cargar_plantillas()
    return _construir_partidas_desde_plantilla(plantillas["impuesto_tasa"]["partidas"], datos)


def crear_asiento_directo(
    concepto: str,
    fecha: str,
    codejercicio: str,
    idempresa: int,
    partidas: list[dict],
    motor=None,
) -> dict:
    """Crea un asiento contable directo via API (POST asientos + POST partidas).

    Args:
        concepto: descripcion del asiento
        fecha: fecha en formato YYYY-MM-DD
        codejercicio: codigo del ejercicio en FS (ej: '2025', '0003')
        idempresa: ID de la empresa en FS
        partidas: lista de dicts con codsubcuenta, debe, haber, concepto
        motor: MotorReglas opcional para validacion pre-envio

    Returns:
        dict con idasiento y num_partidas

    Raises:
        HTTPError: si falla alguna llamada a la API
    """
    # 1. Crear asiento cabecera
    datos_asiento = {
        "concepto": concepto,
        "fecha": fecha,
        "codejercicio": codejercicio,
        "idempresa": idempresa,
    }
    logger.info(f"Creando asiento: {concepto} ({fecha})")
    resp_asiento = api_post("asientos", datos_asiento)

    # FS API devuelve {"ok": "...", "data": {"idasiento": "456", ...}}
    idasiento = (
        resp_asiento.get("data", {}).get("idasiento")
        or resp_asiento.get("idasiento")
    )
    if not idasiento:
        raise ValueError(f"Respuesta sin idasiento: {resp_asiento}")
    idasiento = int(idasiento)
    logger.info(f"Asiento creado: idasiento={idasiento}")

    # 2. Crear cada partida vinculada al asiento
    num_partidas = 0
    for partida in partidas:
        datos_partida = {
            "idasiento": idasiento,
            "codsubcuenta": partida["codsubcuenta"],
            "debe": partida["debe"],
            "haber": partida["haber"],
            "concepto": partida.get("concepto", concepto),
        }
        api_post("partidas", datos_partida)
        num_partidas += 1
        logger.debug(f"  Partida: {partida['codsubcuenta']} D={partida['debe']} H={partida['haber']}")

    logger.info(f"Asiento {idasiento} completado con {num_partidas} partidas")
    return {"idasiento": idasiento, "num_partidas": num_partidas}
