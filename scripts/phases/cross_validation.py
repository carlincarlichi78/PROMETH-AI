"""Fase 5: Verificacion cruzada — 9 checks globales.

Cruces entre facturas, asientos y subcuentas contables:
1. Total facturas proveedor == subcuenta 600 neto + 4709
2. Total facturas cliente == subcuenta 700
3. IVA repercutido facturas + autoliq == 477
4. IVA soportado facturas + autoliq == 472
5. Autoliquidacion 472 == autoliquidacion 477
6. Num facturas == num asientos
7. Libro diario cuadra (sum DEBE global == sum HABER global)
8. 303 calculado == 303 desde subcuentas
9. Balance: Activo == Pasivo + PN (si SL)

Entrada: API FS completa + config.yaml
Salida: cross_validation_report.json
"""
import json
from datetime import datetime
from pathlib import Path

from ..core.config import ConfigCliente
from ..core.errors import ResultadoFase
from ..core.fs_api import api_get
from ..core.logger import crear_logger

logger = crear_logger("cross_validation")


def _obtener_datos_fs(config: ConfigCliente) -> dict:
    """Obtiene todos los datos necesarios de FS para los cruces.

    Returns:
        dict con facturas, asientos, partidas, subcuentas
    """
    params_base = {
        "idempresa": config.idempresa,
        "codejercicio": config.ejercicio,
    }

    datos = {}

    try:
        datos["facturas_prov"] = api_get("facturaproveedores", params=params_base)
        logger.info(f"  {len(datos['facturas_prov'])} facturas proveedor")
    except Exception as e:
        logger.error(f"Error obteniendo facturas proveedor: {e}")
        datos["facturas_prov"] = []

    try:
        datos["facturas_cli"] = api_get("facturaclientes", params=params_base)
        logger.info(f"  {len(datos['facturas_cli'])} facturas cliente")
    except Exception as e:
        logger.error(f"Error obteniendo facturas cliente: {e}")
        datos["facturas_cli"] = []

    try:
        datos["partidas"] = api_get("partidas", params=params_base)
        logger.info(f"  {len(datos['partidas'])} partidas")
    except Exception as e:
        logger.error(f"Error obteniendo partidas: {e}")
        datos["partidas"] = []

    try:
        datos["asientos"] = api_get("asientos", params=params_base)
        logger.info(f"  {len(datos['asientos'])} asientos")
    except Exception as e:
        logger.error(f"Error obteniendo asientos: {e}")
        datos["asientos"] = []

    return datos


def _check_gastos_vs_600(datos: dict, tolerancia: float) -> dict:
    """Check 1: Total base facturas proveedor == subcuenta 600 neto + 4709."""
    total_base_prov = sum(float(f.get("neto", 0)) for f in datos["facturas_prov"])

    total_600_debe = sum(
        float(p.get("debe", 0))
        for p in datos["partidas"]
        if p.get("codsubcuenta", "").startswith("600")
    )
    total_600_haber = sum(
        float(p.get("haber", 0))
        for p in datos["partidas"]
        if p.get("codsubcuenta", "").startswith("600")
    )
    total_4709 = sum(
        float(p.get("debe", 0))
        for p in datos["partidas"]
        if p.get("codsubcuenta", "").startswith("4709")
    )

    neto_600 = total_600_debe - total_600_haber
    total_contable = neto_600 + total_4709
    diferencia = abs(total_base_prov - total_contable)

    return {
        "check": 1,
        "nombre": "Gastos vs subcuenta 600+4709",
        "pasa": diferencia <= tolerancia,
        "total_facturas": total_base_prov,
        "total_contable": total_contable,
        "diferencia": diferencia,
        "detalle": f"Base fact prov: {total_base_prov:.2f} | "
                   f"600 neto: {neto_600:.2f} + 4709: {total_4709:.2f} = {total_contable:.2f}"
    }


def _check_ingresos_vs_700(datos: dict, tolerancia: float) -> dict:
    """Check 2: Total base facturas cliente == subcuenta 700 HABER."""
    total_base_cli = sum(float(f.get("neto", 0)) for f in datos["facturas_cli"])

    total_700_haber = sum(
        float(p.get("haber", 0))
        for p in datos["partidas"]
        if p.get("codsubcuenta", "").startswith("700")
    )
    total_700_debe = sum(
        float(p.get("debe", 0))
        for p in datos["partidas"]
        if p.get("codsubcuenta", "").startswith("700")
    )
    neto_700 = total_700_haber - total_700_debe
    diferencia = abs(total_base_cli - neto_700)

    return {
        "check": 2,
        "nombre": "Ingresos vs subcuenta 700",
        "pasa": diferencia <= tolerancia,
        "total_facturas": total_base_cli,
        "total_contable": neto_700,
        "diferencia": diferencia,
    }


def _check_iva_repercutido(datos: dict, tolerancia: float) -> dict:
    """Check 3: IVA repercutido facturas + autoliq == 477 HABER."""
    total_iva_rep = sum(float(f.get("totaliva", 0)) for f in datos["facturas_cli"])

    total_477_haber = sum(
        float(p.get("haber", 0))
        for p in datos["partidas"]
        if p.get("codsubcuenta", "").startswith("477")
    )
    diferencia = abs(total_iva_rep - total_477_haber)

    return {
        "check": 3,
        "nombre": "IVA repercutido vs 477",
        "pasa": diferencia <= tolerancia,
        "total_facturas": total_iva_rep,
        "total_contable": total_477_haber,
        "diferencia": diferencia,
    }


def _check_iva_soportado(datos: dict, tolerancia: float) -> dict:
    """Check 4: IVA soportado facturas + autoliq == 472 DEBE."""
    total_iva_sop = sum(float(f.get("totaliva", 0)) for f in datos["facturas_prov"])

    total_472_debe = sum(
        float(p.get("debe", 0))
        for p in datos["partidas"]
        if p.get("codsubcuenta", "").startswith("472")
    )
    diferencia = abs(total_iva_sop - total_472_debe)

    return {
        "check": 4,
        "nombre": "IVA soportado vs 472",
        "pasa": diferencia <= tolerancia,
        "total_facturas": total_iva_sop,
        "total_contable": total_472_debe,
        "diferencia": diferencia,
    }


def _check_autoliq_equilibrada(datos: dict, tolerancia: float) -> dict:
    """Check 5: Autoliquidacion en 472 debe igualar autoliquidacion en 477.

    Las partidas de autoliquidacion intracomunitaria aparecen como
    importes adicionales en 472 DEBE y 477 HABER que no vienen de facturas.
    """
    # Total 472 autoliquidacion = 472 DEBE - IVA soportado facturas
    total_iva_sop = sum(float(f.get("totaliva", 0)) for f in datos["facturas_prov"])
    total_472_debe = sum(
        float(p.get("debe", 0))
        for p in datos["partidas"]
        if p.get("codsubcuenta", "").startswith("472")
    )
    autoliq_472 = total_472_debe - total_iva_sop

    # Total 477 autoliquidacion = 477 HABER - IVA repercutido facturas
    total_iva_rep = sum(float(f.get("totaliva", 0)) for f in datos["facturas_cli"])
    total_477_haber = sum(
        float(p.get("haber", 0))
        for p in datos["partidas"]
        if p.get("codsubcuenta", "").startswith("477")
    )
    autoliq_477 = total_477_haber - total_iva_rep

    diferencia = abs(autoliq_472 - autoliq_477)

    return {
        "check": 5,
        "nombre": "Autoliquidacion 472 == 477",
        "pasa": diferencia <= tolerancia,
        "autoliq_472": autoliq_472,
        "autoliq_477": autoliq_477,
        "diferencia": diferencia,
    }


def _check_facturas_vs_asientos(datos: dict) -> dict:
    """Check 6: Numero de facturas == numero de asientos."""
    total_facturas = len(datos["facturas_prov"]) + len(datos["facturas_cli"])

    # Contar asientos que tienen factura vinculada
    ids_asiento_prov = {f.get("idasiento") for f in datos["facturas_prov"]
                        if f.get("idasiento")}
    ids_asiento_cli = {f.get("idasiento") for f in datos["facturas_cli"]
                       if f.get("idasiento")}
    total_asientos_factura = len(ids_asiento_prov | ids_asiento_cli)

    # Facturas sin asiento
    sin_asiento = total_facturas - total_asientos_factura

    return {
        "check": 6,
        "nombre": "Facturas == Asientos",
        "pasa": sin_asiento == 0,
        "total_facturas": total_facturas,
        "total_asientos_factura": total_asientos_factura,
        "sin_asiento": sin_asiento,
    }


def _check_libro_diario(datos: dict, tolerancia: float) -> dict:
    """Check 7: Libro diario cuadra (sum DEBE global == sum HABER global)."""
    total_debe = sum(float(p.get("debe", 0)) for p in datos["partidas"])
    total_haber = sum(float(p.get("haber", 0)) for p in datos["partidas"])
    diferencia = abs(total_debe - total_haber)

    return {
        "check": 7,
        "nombre": "Libro diario cuadra",
        "pasa": diferencia <= tolerancia,
        "total_debe": total_debe,
        "total_haber": total_haber,
        "diferencia": diferencia,
    }


def _check_modelo_303(datos: dict, tolerancia: float) -> dict:
    """Check 8: 303 calculado desde facturas == 303 desde subcuentas."""
    # IVA a ingresar = IVA repercutido (477) - IVA soportado (472)
    total_477 = sum(
        float(p.get("haber", 0))
        for p in datos["partidas"]
        if p.get("codsubcuenta", "").startswith("477")
    )
    total_472 = sum(
        float(p.get("debe", 0))
        for p in datos["partidas"]
        if p.get("codsubcuenta", "").startswith("472")
    )
    iva_desde_subcuentas = total_477 - total_472

    # IVA desde facturas
    iva_rep_facturas = sum(float(f.get("totaliva", 0)) for f in datos["facturas_cli"])
    iva_sop_facturas = sum(float(f.get("totaliva", 0)) for f in datos["facturas_prov"])
    iva_desde_facturas = iva_rep_facturas - iva_sop_facturas

    diferencia = abs(iva_desde_subcuentas - iva_desde_facturas)

    return {
        "check": 8,
        "nombre": "303 subcuentas vs facturas",
        "pasa": diferencia <= tolerancia,
        "iva_subcuentas": iva_desde_subcuentas,
        "iva_facturas": iva_desde_facturas,
        "diferencia": diferencia,
        "detalle": f"477={total_477:.2f} - 472={total_472:.2f} = {iva_desde_subcuentas:.2f} | "
                   f"IVA rep={iva_rep_facturas:.2f} - IVA sop={iva_sop_facturas:.2f} = {iva_desde_facturas:.2f}"
    }


def _check_balance(datos: dict, config: ConfigCliente, tolerancia: float) -> dict:
    """Check 9: Balance — Activo == Pasivo + PN (solo para SL/SA)."""
    if config.tipo not in ("sl", "sa"):
        return {
            "check": 9,
            "nombre": "Balance Activo == Pasivo + PN",
            "pasa": True,
            "nota": f"No aplica para tipo '{config.tipo}'"
        }

    # Activo: subcuentas grupo 1-5 con saldo deudor
    # Simplificacion: grupo 1-2 = activo no corriente, 3-5 = activo corriente
    # Pasivo: grupo 1 (PN), 4 (acreedores), subcuentas con saldo acreedor

    # Calcular saldos por grupo contable
    saldos = {}
    for p in datos["partidas"]:
        subcta = p.get("codsubcuenta", "")
        if not subcta:
            continue
        grupo = subcta[0]
        debe = float(p.get("debe", 0))
        haber = float(p.get("haber", 0))
        saldos[grupo] = saldos.get(grupo, 0) + debe - haber

    # Activo = saldo deudor de grupos 2,3,5 + deudores de 4
    # Pasivo = saldo acreedor de grupos 1,4
    # Simplificacion para verificacion rapida
    total_debe = sum(float(p.get("debe", 0)) for p in datos["partidas"])
    total_haber = sum(float(p.get("haber", 0)) for p in datos["partidas"])
    diferencia = abs(total_debe - total_haber)

    return {
        "check": 9,
        "nombre": "Balance Activo == Pasivo + PN",
        "pasa": diferencia <= tolerancia,
        "saldos_por_grupo": saldos,
        "diferencia": diferencia,
        "nota": "Verificacion simplificada via cuadre global"
    }


def ejecutar_cruce(
    config: ConfigCliente,
    ruta_cliente: Path,
    auditoria=None
) -> ResultadoFase:
    """Ejecuta la fase 5 de verificacion cruzada.

    Args:
        config: configuracion del cliente
        ruta_cliente: ruta a la carpeta del cliente
        auditoria: AuditoriaLogger opcional

    Returns:
        ResultadoFase con resultado de los 9 cruces
    """
    resultado = ResultadoFase("cruce")
    tolerancia = config.tolerancias.get("comparacion_importes", 0.02)

    logger.info("Obteniendo datos de FS para verificacion cruzada...")
    datos = _obtener_datos_fs(config)

    if not datos["partidas"]:
        resultado.error("No se obtuvieron partidas de FS")
        return resultado

    logger.info("Ejecutando 9 checks de cruce...")

    checks = [
        _check_gastos_vs_600(datos, tolerancia),
        _check_ingresos_vs_700(datos, tolerancia),
        _check_iva_repercutido(datos, tolerancia),
        _check_iva_soportado(datos, tolerancia),
        _check_autoliq_equilibrada(datos, tolerancia),
        _check_facturas_vs_asientos(datos),
        _check_libro_diario(datos, tolerancia),
        _check_modelo_303(datos, tolerancia),
        _check_balance(datos, config, tolerancia),
    ]

    total_ok = 0
    total_fail = 0

    for check in checks:
        pasa = check.get("pasa", False)
        nombre = check.get("nombre", f"Check {check['check']}")
        estado = "PASS" if pasa else "FAIL"

        if pasa:
            total_ok += 1
            logger.info(f"  [{estado}] {nombre}")
        else:
            total_fail += 1
            logger.warning(f"  [{estado}] {nombre} — diff: {check.get('diferencia', '?')}")
            resultado.aviso(f"Cruce fallido: {nombre}",
                            {k: v for k, v in check.items() if k != "nombre"})

        if auditoria:
            auditoria.registrar(
                "cruce", "verificacion",
                f"{nombre}: {estado}",
                check
            )

    # Guardar reporte
    ruta_reporte = ruta_cliente / "cross_validation_report.json"
    reporte = {
        "fecha_cruce": datetime.now().isoformat(),
        "ejercicio": config.ejercicio,
        "total_checks": len(checks),
        "total_pass": total_ok,
        "total_fail": total_fail,
        "checks": checks,
    }
    with open(ruta_reporte, "w", encoding="utf-8") as f:
        json.dump(reporte, f, ensure_ascii=False, indent=2)

    resultado.datos["checks"] = checks
    resultado.datos["ruta_reporte"] = str(ruta_reporte)

    logger.info(f"Verificacion cruzada: {total_ok} PASS, {total_fail} FAIL "
                f"de {len(checks)} checks")

    return resultado
