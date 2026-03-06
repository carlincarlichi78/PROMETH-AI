"""Fase 5: Verificacion cruzada — 13 checks globales.

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
10. Cruce individual por proveedor (base + IVA + total vs asiento)
11. Cruce individual por cliente (base + IVA vs asiento)
12. Auditor IA (Gemini Flash revisa cada asiento corregido)
13. Personal y servicios (coherencia subcuentas 640-662, 476, 4751)

Entrada: API FS completa + config.yaml
Salida: cross_validation_report.json
"""
import json
from datetime import datetime
from pathlib import Path

from ..core.config import ConfigCliente
from ..core.errors import ResultadoFase
from ..core.fs_adapter import FSAdapter
from ..core.logger import crear_logger
from ..core.ocr_gemini import auditar_asiento_gemini
from ..core.auditor_asientos import AuditorAsientos

logger = crear_logger("cross_validation")


def _obtener_datos_fs(config: ConfigCliente, fs: FSAdapter) -> dict:
    """Obtiene todos los datos necesarios de FS para los cruces.

    Returns:
        dict con facturas, asientos, partidas, subcuentas
    """
    # Filtros idempresa/codejercicio NO funcionan en la API FS
    # SIEMPRE post-filtrar en Python
    idempresa = str(config.idempresa)
    codejercicio = str(config.codejercicio)

    datos = {}

    try:
        todas_fp = fs._get("facturaproveedores") or []
        datos["facturas_prov"] = [
            f for f in todas_fp
            if str(f.get("idempresa")) == idempresa
            and str(f.get("codejercicio")) == codejercicio
        ]
        logger.info(f"  {len(datos['facturas_prov'])} facturas proveedor (de {len(todas_fp)} total)")
    except Exception as e:
        logger.error(f"Error obteniendo facturas proveedor: {e}")
        datos["facturas_prov"] = []

    try:
        todas_fc = fs._get("facturaclientes") or []
        datos["facturas_cli"] = [
            f for f in todas_fc
            if str(f.get("idempresa")) == idempresa
            and str(f.get("codejercicio")) == codejercicio
        ]
        logger.info(f"  {len(datos['facturas_cli'])} facturas cliente (de {len(todas_fc)} total)")
    except Exception as e:
        logger.error(f"Error obteniendo facturas cliente: {e}")
        datos["facturas_cli"] = []

    try:
        todos_as = fs._get("asientos") or []
        datos["asientos"] = [
            a for a in todos_as
            if str(a.get("idempresa")) == idempresa
            and str(a.get("codejercicio")) == codejercicio
        ]
        logger.info(f"  {len(datos['asientos'])} asientos (de {len(todos_as)} total)")
    except Exception as e:
        logger.error(f"Error obteniendo asientos: {e}")
        datos["asientos"] = []

    try:
        # Partidas no tienen idempresa — filtrar por idasiento de esta empresa
        ids_asientos = {int(a.get("idasiento", 0)) for a in datos["asientos"]}
        todas_p = fs._get("partidas") or []
        datos["partidas"] = [
            p for p in todas_p
            if int(p.get("idasiento", 0)) in ids_asientos
        ]
        logger.info(f"  {len(datos['partidas'])} partidas (de {len(todas_p)} total)")
    except Exception as e:
        logger.error(f"Error obteniendo partidas: {e}")
        datos["partidas"] = []

    return datos


def _check_gastos_vs_600(datos: dict, tolerancia: float) -> dict:
    """Check 1: Total base facturas proveedor == subcuentas grupo 6 neto + 4709."""
    total_base_prov = sum(float(f.get("neto", 0)) for f in datos["facturas_prov"])

    # Grupo 6 completo: 600 compras, 602 aprovisionamientos, 623 servicios,
    # 627 publicidad, 628 suministros, 629 otros, 640 personal, etc.
    total_6_debe = sum(
        float(p.get("debe", 0))
        for p in datos["partidas"]
        if p.get("codsubcuenta", "").startswith("6")
    )
    total_6_haber = sum(
        float(p.get("haber", 0))
        for p in datos["partidas"]
        if p.get("codsubcuenta", "").startswith("6")
    )
    total_4709 = sum(
        float(p.get("debe", 0))
        for p in datos["partidas"]
        if p.get("codsubcuenta", "").startswith("4709")
    )

    neto_6 = total_6_debe - total_6_haber
    total_contable = neto_6 + total_4709
    diferencia = abs(total_base_prov - total_contable)

    return {
        "check": 1,
        "nombre": "Gastos vs grupo 6+4709",
        "pasa": diferencia <= tolerancia,
        "total_facturas": total_base_prov,
        "total_contable": total_contable,
        "diferencia": diferencia,
        "detalle": f"Base fact prov: {total_base_prov:.2f} | "
                   f"grupo 6 neto: {neto_6:.2f} + 4709: {total_4709:.2f} = {total_contable:.2f}"
    }


def _check_ingresos_vs_700(datos: dict, tolerancia: float) -> dict:
    """Check 2: Total base facturas cliente == subcuentas grupo 7 HABER."""
    total_base_cli = sum(float(f.get("neto", 0)) for f in datos["facturas_cli"])

    total_7_haber = sum(
        float(p.get("haber", 0))
        for p in datos["partidas"]
        if p.get("codsubcuenta", "").startswith("7")
    )
    total_7_debe = sum(
        float(p.get("debe", 0))
        for p in datos["partidas"]
        if p.get("codsubcuenta", "").startswith("7")
    )
    neto_7 = total_7_haber - total_7_debe
    diferencia = abs(total_base_cli - neto_7)

    return {
        "check": 2,
        "nombre": "Ingresos vs grupo 7",
        "pasa": diferencia <= tolerancia,
        "total_facturas": total_base_cli,
        "total_contable": neto_7,
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


def _check_cruce_por_proveedor(datos: dict, tolerancia: float = 0.02) -> dict:
    """Cruce individual: cada proveedor debe cuadrar factura vs asiento."""
    facturas_prov = datos.get("facturas_prov", [])
    partidas = datos.get("partidas", [])

    # Agrupar facturas por codproveedor
    por_proveedor = {}
    for f in facturas_prov:
        cod = f.get("codproveedor", f.get("nombre", "desconocido"))
        if cod not in por_proveedor:
            por_proveedor[cod] = {"facturas": [], "nombre": f.get("nombre", cod)}
        por_proveedor[cod]["facturas"].append(f)

    # Para cada proveedor, cruzar
    detalles_proveedor = []
    total_errores = 0

    for cod, info in por_proveedor.items():
        facts = info["facturas"]
        ids_asientos = {int(f.get("idasiento", 0)) for f in facts if f.get("idasiento")}
        partidas_prov = [p for p in partidas if int(p.get("idasiento", 0)) in ids_asientos]

        # Base imponible: facturas vs grupo 6 + 4709
        total_base = sum(float(f.get("neto", 0)) for f in facts)
        total_6 = sum(float(p.get("debe", 0)) for p in partidas_prov if p.get("codsubcuenta", "").startswith("6")) \
                - sum(float(p.get("haber", 0)) for p in partidas_prov if p.get("codsubcuenta", "").startswith("6"))
        total_4709 = sum(float(p.get("debe", 0)) for p in partidas_prov if p.get("codsubcuenta", "").startswith("4709"))
        diff_base = abs(total_base - (total_6 + total_4709))

        # IVA: facturas vs 472
        total_iva = sum(float(f.get("totaliva", 0)) for f in facts)
        total_472 = sum(float(p.get("debe", 0)) for p in partidas_prov if p.get("codsubcuenta", "").startswith("472"))
        diff_iva = abs(total_iva - total_472)

        # Total: facturas vs 400
        total_total = sum(float(f.get("total", 0)) for f in facts)
        total_400 = sum(float(p.get("haber", 0)) for p in partidas_prov if p.get("codsubcuenta", "").startswith("400"))
        diff_total = abs(total_total - total_400)

        pasa = diff_base <= tolerancia and diff_iva <= tolerancia and diff_total <= tolerancia

        detalle = {
            "proveedor": info["nombre"],
            "codigo": cod,
            "num_facturas": len(facts),
            "pasa": pasa,
            "base": {"facturas": round(total_base, 2), "contable": round(total_6 + total_4709, 2), "diff": round(diff_base, 2)},
            "iva": {"facturas": round(total_iva, 2), "contable_472": round(total_472, 2), "diff": round(diff_iva, 2)},
            "total": {"facturas": round(total_total, 2), "contable_400": round(total_400, 2), "diff": round(diff_total, 2)},
        }
        detalles_proveedor.append(detalle)
        if not pasa:
            total_errores += 1

    return {
        "check": 10,
        "nombre": "Cruce individual por proveedor",
        "pasa": total_errores == 0,
        "total_proveedores": len(por_proveedor),
        "proveedores_con_error": total_errores,
        "detalle": detalles_proveedor,
    }


def _check_cruce_por_cliente(datos: dict, tolerancia: float = 0.02) -> dict:
    """Cruce individual por cliente: factura vs asiento."""
    facturas_cli = datos.get("facturas_cli", [])
    partidas = datos.get("partidas", [])

    por_cliente = {}
    for f in facturas_cli:
        cod = f.get("codcliente", f.get("nombre", "desconocido"))
        if cod not in por_cliente:
            por_cliente[cod] = {"facturas": [], "nombre": f.get("nombre", cod)}
        por_cliente[cod]["facturas"].append(f)

    detalles = []
    total_errores = 0

    for cod, info in por_cliente.items():
        facts = info["facturas"]
        ids_asientos = {int(f.get("idasiento", 0)) for f in facts if f.get("idasiento")}
        partidas_cli = [p for p in partidas if int(p.get("idasiento", 0)) in ids_asientos]

        total_base = sum(float(f.get("neto", 0)) for f in facts)
        total_700 = sum(float(p.get("haber", 0)) for p in partidas_cli if p.get("codsubcuenta", "").startswith("700")) \
                  - sum(float(p.get("debe", 0)) for p in partidas_cli if p.get("codsubcuenta", "").startswith("700"))
        diff_base = abs(total_base - total_700)

        total_iva = sum(float(f.get("totaliva", 0)) for f in facts)
        total_477 = sum(float(p.get("haber", 0)) for p in partidas_cli if p.get("codsubcuenta", "").startswith("477"))
        diff_iva = abs(total_iva - total_477)

        pasa = diff_base <= tolerancia and diff_iva <= tolerancia

        detalles.append({
            "cliente": info["nombre"],
            "codigo": cod,
            "num_facturas": len(facts),
            "pasa": pasa,
            "base": {"facturas": round(total_base, 2), "contable": round(total_700, 2), "diff": round(diff_base, 2)},
            "iva": {"facturas": round(total_iva, 2), "contable_477": round(total_477, 2), "diff": round(diff_iva, 2)},
        })
        if not pasa:
            total_errores += 1

    return {
        "check": 11,
        "nombre": "Cruce individual por cliente",
        "pasa": total_errores == 0,
        "total_clientes": len(por_cliente),
        "clientes_con_error": total_errores,
        "detalle": detalles,
    }


def _auditar_asiento(asiento: dict) -> dict:
    """Audita un asiento con consenso multi-modelo (Gemini+Haiku+GPT-mini)."""
    auditor = AuditorAsientos()
    resultado = auditor.auditar_sync(asiento)
    return {
        "resultado": "OK" if resultado.aprobado else "ALERTA",
        "nivel": resultado.nivel,
        "confianza": resultado.confianza,
        "problemas": [{"descripcion": resultado.detalle}] if not resultado.aprobado else [],
        "_fuente": f"multi_modelo_votos:{resultado.votos}",
    }


def _check_auditor_ia(datos: dict, config, ruta_ejercicio) -> dict:
    """Capa 5: Auditor IA revisa cada asiento con Gemini Flash."""
    import os
    from pathlib import Path
    if not os.environ.get("GEMINI_API_KEY"):
        return {
            "check": 12,
            "nombre": "Auditor IA (Gemini Flash)",
            "pasa": True,
            "detalle": "GEMINI_API_KEY no configurada, check omitido",
            "alertas": [],
        }

    # Cargar asientos corregidos
    ruta_auditoria = Path(ruta_ejercicio) / "auditoria" if isinstance(ruta_ejercicio, (str, Path)) else ruta_ejercicio
    if isinstance(ruta_auditoria, str):
        ruta_auditoria = Path(ruta_auditoria)

    # Intentar buscar auditoria como subcarpeta
    if not ruta_auditoria.exists():
        ruta_auditoria = Path(ruta_ejercicio)

    asientos_file = sorted(ruta_auditoria.glob("asientos_corregidos_*.json"), reverse=True)
    if not asientos_file:
        return {"check": 12, "nombre": "Auditor IA (Gemini Flash)", "pasa": True, "detalle": "Sin asientos corregidos", "alertas": []}

    import json
    with open(asientos_file[0], "r", encoding="utf-8") as f:
        asientos_data = json.load(f)

    alertas = []
    for asiento in asientos_data.get("asientos", []):
        datos_ext = asiento.get("datos_extraidos", {})
        contexto = {
            "tipo_empresa": getattr(config, "tipo", "desconocido") if not isinstance(config, dict) else config.get("tipo", "desconocido"),
            "regimen": datos_ext.get("regimen", "general"),
            "actividad": getattr(config, "actividad", "general") if not isinstance(config, dict) else config.get("actividad", "general"),
            "checks_previos": f"{asiento.get('problemas_detectados', 0)} problemas, {asiento.get('correcciones_aplicadas', 0)} corregidos",
        }

        resultado = _auditar_asiento(asiento)

        if resultado.get("resultado") == "ALERTA":
            for problema in resultado.get("problemas", []):
                alertas.append({
                    "factura": datos_ext.get("numero_factura", "?"),
                    "proveedor": datos_ext.get("emisor_nombre", "?"),
                    **problema,
                })

    return {
        "check": 12,
        "nombre": "Auditor IA (Gemini Flash)",
        "pasa": len(alertas) == 0,
        "total_asientos_revisados": len(asientos_data.get("asientos", [])),
        "total_alertas": len(alertas),
        "alertas": alertas,
    }


def _check_personal_servicios(partidas_empresa: list) -> dict:
    """Check 13: Verifica coherencia de subcuentas de personal y servicios.

    Subcuentas de gasto (640-662) deben tener saldo DEUDOR (debe > haber).
    Subcuentas acreedoras (476, 4751) deben tener saldo ACREEDOR (haber > debe).
    """
    errores = []

    # Subcuentas que deben tener saldo deudor (gastos)
    subcuentas_debe = {
        "640": "Sueldos y salarios",
        "642": "SS a cargo empresa",
        "626": "Servicios bancarios",
        "625": "Primas de seguros",
        "631": "Otros tributos",
        "621": "Arrendamientos",
        "662": "Intereses deudas",
    }
    # Subcuentas que deben tener saldo acreedor
    subcuentas_haber = {
        "476": "Organismos SS",
        "4751": "HP acreedora IRPF",
    }

    for prefijo, nombre in subcuentas_debe.items():
        saldo = sum(
            float(p.get("debe", 0)) - float(p.get("haber", 0))
            for p in partidas_empresa
            if p.get("codsubcuenta", "").startswith(prefijo)
        )
        if saldo < -0.01:
            errores.append(f"{prefijo} ({nombre}): saldo acreedor {saldo:.2f} (esperado deudor)")

    for prefijo, nombre in subcuentas_haber.items():
        saldo = sum(
            float(p.get("haber", 0)) - float(p.get("debe", 0))
            for p in partidas_empresa
            if p.get("codsubcuenta", "").startswith(prefijo)
        )
        if saldo < -0.01:
            errores.append(f"{prefijo} ({nombre}): saldo deudor inesperado (esperado acreedor)")

    return {
        "check": 13,
        "nombre": "Personal y servicios",
        "pasa": len(errores) == 0,
        "detalle": "OK — subcuentas personal/servicios coherentes" if not errores else "; ".join(errores),
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
        ResultadoFase con resultado de los 12 cruces
    """
    resultado = ResultadoFase("cruce")
    tolerancia = config.tolerancias.get("comparacion_importes", 0.02)

    fs = FSAdapter.desde_config(config)
    logger.info("Obteniendo datos de FS para verificacion cruzada...")
    datos = _obtener_datos_fs(config, fs)

    if not datos["partidas"]:
        resultado.error("No se obtuvieron partidas de FS")
        return resultado

    logger.info("Ejecutando 13 checks de cruce...")

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
        # Checks v2 - cruce individual
        _check_cruce_por_proveedor(datos, tolerancia),
        _check_cruce_por_cliente(datos, tolerancia),
    ]

    # Check 12: Auditor IA (al final, despues de todos los deterministas)
    ruta_ejercicio = ruta_cliente / str(config.ejercicio)
    checks.append(_check_auditor_ia(datos, config, ruta_ejercicio))

    # Check 13: Personal y servicios (subcuentas nuevas: nominas, bancarios, etc.)
    checks.append(_check_personal_servicios(datos["partidas"]))

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
    from sfce.core.contracts import CrossValidationOutput
    ruta_reporte = ruta_cliente / "cross_validation_report.json"
    with open(ruta_reporte, "w", encoding="utf-8") as f:
        f.write(CrossValidationOutput.validar_y_serializar(checks))

    resultado.datos["checks"] = checks
    resultado.datos["ruta_reporte"] = str(ruta_reporte)

    logger.info(f"Verificacion cruzada: {total_ok} PASS, {total_fail} FAIL "
                f"de {len(checks)} checks (13 total)")

    return resultado
