"""Fase 3: Generacion y verificacion de asientos contables.

FS genera asientos automaticamente al crear facturas.
Esta fase verifica que cada factura registrada tiene su asiento vinculado
y obtiene todas las partidas para las fases posteriores.

Si los asientos no se generaron automaticamente (ej: requiere accion manual en UI),
el pipeline guarda estado y muestra instrucciones para --resume.

Entrada: registered.json
Salida: asientos_generados.json
"""
import json
from datetime import datetime
from pathlib import Path

from ..core.config import ConfigCliente
from ..core.errors import ResultadoFase
from ..core.fs_api import api_get, verificar_factura
from ..core.logger import crear_logger

logger = crear_logger("asientos")


def _obtener_asiento_factura(idfactura: int, tipo_doc: str,
                              config: ConfigCliente) -> dict | None:
    """Obtiene el asiento vinculado a una factura.

    Returns:
        dict con datos del asiento, o None si no existe
    """
    tipo_fs = "proveedor" if tipo_doc in ("FC", "NC", "ANT") else "cliente"

    try:
        factura = verificar_factura(idfactura, tipo=tipo_fs)
        idasiento = factura.get("idasiento")

        if not idasiento:
            return None

        # Obtener asiento completo
        asientos = api_get(f"asientos/{idasiento}")
        if isinstance(asientos, list) and asientos:
            return asientos[0]
        elif isinstance(asientos, dict):
            return asientos
        return None
    except Exception as e:
        logger.error(f"Error obteniendo asiento de factura {idfactura}: {e}")
        return None


def _obtener_partidas_asiento(idasiento: int) -> list:
    """Obtiene todas las partidas (lineas) de un asiento.

    Returns:
        Lista de partidas con subcuenta, debe, haber, concepto, etc.
    """
    try:
        partidas = api_get("partidas", params={"idasiento": idasiento})
        return partidas
    except Exception as e:
        logger.error(f"Error obteniendo partidas del asiento {idasiento}: {e}")
        return []


def ejecutar_asientos(
    config: ConfigCliente,
    ruta_cliente: Path,
    auditoria=None
) -> ResultadoFase:
    """Ejecuta la fase 3 de generacion/verificacion de asientos.

    Args:
        config: configuracion del cliente
        ruta_cliente: ruta a la carpeta del cliente
        auditoria: AuditoriaLogger opcional

    Returns:
        ResultadoFase con asientos y partidas obtenidos
    """
    resultado = ResultadoFase("asientos")

    # Cargar registered.json
    ruta_registrados = ruta_cliente / "registered.json"
    if not ruta_registrados.exists():
        resultado.error("No existe registered.json (ejecutar fase 2 primero)")
        return resultado

    with open(ruta_registrados, "r", encoding="utf-8") as f:
        registro_data = json.load(f)

    registrados = registro_data.get("registrados", [])
    if not registrados:
        resultado.aviso("No hay facturas registradas")
        resultado.datos["asientos"] = []
        return resultado

    logger.info(f"Verificando asientos de {len(registrados)} facturas...")

    asientos_obtenidos = []
    sin_asiento = []

    for reg in registrados:
        archivo = reg.get("archivo", "?")
        idfactura = reg.get("idfactura")
        tipo_doc = reg.get("tipo", "FC")

        if not idfactura:
            logger.warning(f"  {archivo}: sin idfactura, saltando")
            continue

        logger.info(f"Verificando asiento: {archivo} (factura ID {idfactura})")

        # Obtener asiento
        asiento = _obtener_asiento_factura(idfactura, tipo_doc, config)

        if not asiento:
            logger.warning(f"  {archivo}: SIN ASIENTO vinculado")
            sin_asiento.append(reg)
            continue

        idasiento = asiento.get("idasiento")
        logger.info(f"  Asiento ID {idasiento} encontrado")

        # Obtener partidas
        partidas = _obtener_partidas_asiento(idasiento)
        logger.info(f"  {len(partidas)} partidas obtenidas")

        # Calcular totales
        total_debe = sum(float(p.get("debe", 0)) for p in partidas)
        total_haber = sum(float(p.get("haber", 0)) for p in partidas)
        cuadra = abs(total_debe - total_haber) < 0.01

        if not cuadra:
            logger.warning(f"  DESCUADRE: DEBE={total_debe:.2f} HABER={total_haber:.2f}")

        asiento_completo = {
            **reg,
            "idasiento": idasiento,
            "asiento": asiento,
            "partidas": partidas,
            "total_debe": total_debe,
            "total_haber": total_haber,
            "cuadra": cuadra,
        }
        asientos_obtenidos.append(asiento_completo)

        if auditoria:
            auditoria.registrar(
                "asientos", "verificacion",
                f"{archivo}: asiento {idasiento}, "
                f"DEBE={total_debe:.2f} HABER={total_haber:.2f}",
                {"cuadra": cuadra, "partidas": len(partidas)}
            )

    # Si hay facturas sin asiento, pausar pipeline
    if sin_asiento:
        logger.warning(f"\n{'='*60}")
        logger.warning(f"  {len(sin_asiento)} facturas SIN ASIENTO generado.")
        logger.warning(f"  Generacion manual necesaria en FacturaScripts UI:")
        logger.warning(f"  Contabilidad > Facturas > Generar asientos contables")
        logger.warning(f"  Tras generar, reanudar con: --resume")
        logger.warning(f"{'='*60}\n")

        for reg in sin_asiento:
            logger.warning(f"  - {reg.get('archivo', '?')} "
                           f"(factura ID {reg.get('idfactura', '?')})")

        resultado.aviso(
            f"{len(sin_asiento)} facturas sin asiento (requiere generacion manual)",
            {"facturas_sin_asiento": [r.get("idfactura") for r in sin_asiento]}
        )

        # Guardar estado parcial para --resume
        estado_parcial = {
            "fase": "asientos",
            "completado": False,
            "sin_asiento": [r.get("idfactura") for r in sin_asiento],
            "con_asiento": len(asientos_obtenidos),
        }
        ruta_estado = ruta_cliente / "pipeline_state.json"
        if ruta_estado.exists():
            with open(ruta_estado, "r", encoding="utf-8") as f:
                estado = json.load(f)
        else:
            estado = {}
        estado["fase_asientos"] = estado_parcial
        with open(ruta_estado, "w", encoding="utf-8") as f:
            json.dump(estado, f, ensure_ascii=False, indent=2)

        # No es error bloqueante si al menos algunos tienen asiento
        if not asientos_obtenidos:
            resultado.error("Ninguna factura tiene asiento generado")

    # Guardar asientos_generados.json
    ruta_asientos = ruta_cliente / "asientos_generados.json"
    asientos_json = {
        "fecha_verificacion": datetime.now().isoformat(),
        "total_facturas": len(registrados),
        "total_con_asiento": len(asientos_obtenidos),
        "total_sin_asiento": len(sin_asiento),
        "asientos": asientos_obtenidos,
    }
    with open(ruta_asientos, "w", encoding="utf-8") as f:
        json.dump(asientos_json, f, ensure_ascii=False, indent=2)

    resultado.datos["asientos"] = asientos_obtenidos
    resultado.datos["sin_asiento"] = sin_asiento
    resultado.datos["ruta_asientos"] = str(ruta_asientos)

    logger.info(f"Asientos verificados: {len(asientos_obtenidos)} OK, "
                f"{len(sin_asiento)} pendientes")

    return resultado
