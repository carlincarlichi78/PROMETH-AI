"""Capa 4: Analisis de datos historicos para deteccion de anomalias."""

import json
from pathlib import Path
from typing import Optional
from .logger import crear_logger

logger = crear_logger("historico")


def cargar_historico(ruta_cliente: Path) -> Optional[dict]:
    """Carga resumen historico si existe.

    Busca en clientes/<cliente>/historico/<ano>/resumen.json
    Retorna None si no hay datos historicos.
    """
    ruta_historico = ruta_cliente / "historico"
    if not ruta_historico.exists():
        return None

    datos = {"ejercicios": {}}
    for subdir in sorted(ruta_historico.iterdir()):
        if subdir.is_dir() and subdir.name.isdigit():
            resumen_file = subdir / "resumen.json"
            if resumen_file.exists():
                with open(resumen_file, "r", encoding="utf-8") as f:
                    datos["ejercicios"][subdir.name] = json.load(f)

    if not datos["ejercicios"]:
        return None

    return datos


def check_anomalia_proveedor(proveedor: str, gasto_actual: float,
                             historico: dict) -> Optional[str]:
    """H1: Detecta si el gasto de un proveedor es anomalo vs historico."""
    gastos_previos = []
    for ej, datos in historico.get("ejercicios", {}).items():
        prov_data = datos.get("proveedores", {}).get(proveedor, {})
        if prov_data:
            gastos_previos.append(prov_data.get("gasto_anual", 0))

    if not gastos_previos:
        return None

    media = sum(gastos_previos) / len(gastos_previos)
    if media > 0 and gasto_actual > media * 3:
        return (
            f"Proveedor {proveedor}: gasto actual {gasto_actual:.2f} EUR es "
            f"{gasto_actual/media:.1f}x la media historica ({media:.2f} EUR)"
        )
    return None


def check_proveedor_nuevo(proveedor: str, importe: float,
                          historico: dict, umbral: float = 5000) -> Optional[str]:
    """H2: Alerta si proveedor nuevo con factura > umbral."""
    for ej, datos in historico.get("ejercicios", {}).items():
        if proveedor in datos.get("proveedores", {}):
            return None  # Existe en historico, no es nuevo

    if importe > umbral:
        return (
            f"Proveedor nuevo {proveedor} con factura de {importe:.2f} EUR "
            f"(> umbral {umbral:.2f} EUR)"
        )
    return None


def check_iva_trimestral(trimestre: str, iva_actual: float,
                         historico: dict) -> Optional[str]:
    """H3: Compara IVA trimestral con historico."""
    ivas_previos = []
    for ej, datos in historico.get("ejercicios", {}).items():
        trim_data = datos.get("trimestres", {}).get(trimestre, {})
        if trim_data:
            ivas_previos.append(trim_data.get("cuota_iva_sop", 0))

    if not ivas_previos:
        return None

    media = sum(ivas_previos) / len(ivas_previos)
    if media > 0:
        ratio = abs(iva_actual - media) / media
        if ratio > 0.5:
            return (
                f"IVA {trimestre}: {iva_actual:.2f} EUR difiere "
                f"{ratio*100:.0f}% de la media historica ({media:.2f} EUR)"
            )
    return None


def ejecutar_checks_historicos(ruta_cliente: Path, datos_actuales: dict) -> list:
    """Ejecuta todos los checks historicos disponibles.

    Retorna lista de alertas (strings). Lista vacia si no hay historico.
    """
    historico = cargar_historico(ruta_cliente)
    if historico is None:
        logger.info("Sin datos historicos — checks H1-H5 omitidos")
        return []

    alertas = []

    # H1: Anomalia por proveedor
    for prov, datos_prov in datos_actuales.get("proveedores", {}).items():
        gasto = datos_prov.get("gasto_total", 0)
        err = check_anomalia_proveedor(prov, gasto, historico)
        if err:
            alertas.append(f"[H1] {err}")

    # H2: Proveedor nuevo
    for prov, datos_prov in datos_actuales.get("proveedores", {}).items():
        importe = datos_prov.get("gasto_total", 0)
        err = check_proveedor_nuevo(prov, importe, historico)
        if err:
            alertas.append(f"[H2] {err}")

    # H3: IVA trimestral
    for trim in ["T1", "T2", "T3", "T4"]:
        iva = datos_actuales.get("trimestres", {}).get(trim, {}).get("iva_soportado", 0)
        if iva > 0:
            err = check_iva_trimestral(trim, iva, historico)
            if err:
                alertas.append(f"[H3] {err}")

    logger.info(f"Checks historicos: {len(alertas)} alertas")
    return alertas
