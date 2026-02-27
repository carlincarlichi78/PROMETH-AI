#!/usr/bin/env python3
"""
Corrige suplidos Primatransit empresa 1 (Pastorino).
Reclasifica suplidos aduaneros de 600 a 4709 en asientos 65-68.
"""

import os
import sys
from pathlib import Path
import requests
from typing import Dict, List, Optional

# Setup
API_BASE = "https://contabilidad.lemonfresh-tuc.com/api/3"
API_TOKEN = os.getenv("FS_API_TOKEN", "iOXmrA1Bbn8RDWXLv91L")
HEADERS = {"Token": API_TOKEN}

# Datos a corregir: {idasiento: [(id_partida, debe_nuevo), ...]}
CORRECCIONES = {
    65: [(165, 2302.50), (178, 4991.83)],
    66: [(169, 1801.25), (179, 5807.04)],
    67: [(173, 1783.75), (180, 5588.51)],
    68: [(177, 1232.29)],
}

# Nueva partida a crear en asiento 68
NUEVA_PARTIDA_68 = {
    "idasiento": 68,
    "codsubcuenta": "4709000000",
    "debe": 648.00,
    "haber": 0,
    "concepto": "Costes naviera Maersk — suplidos reclasificados de 600 a 4709"
}


def obtener_todas_partidas() -> List[Dict]:
    """Obtiene todas las partidas de la API (paginando)."""
    todas = []
    offset = 0
    try:
        while True:
            resp = requests.get(f"{API_BASE}/partidas", headers=HEADERS, params={"limit": 500, "offset": offset})
            resp.raise_for_status()
            lote = resp.json()
            if not lote:
                break
            todas.extend(lote)
            if len(lote) < 500:
                break
            offset += 500
        return todas
    except requests.RequestException as e:
        print(f"ERROR al obtener partidas: {e}")
        sys.exit(1)


def filtrar_partidas_por_asiento(partidas: List[Dict], idasiento: int) -> List[Dict]:
    """Filtra partidas por idasiento (post-filtrado manual)."""
    return [p for p in partidas if p.get("idasiento") == idasiento]


def mostrar_partidas_asiento(partidas: List[Dict], idasiento: int, titulo: str = ""):
    """Muestra las partidas de un asiento."""
    asiento_partidas = filtrar_partidas_por_asiento(partidas, idasiento)
    print(f"\n{titulo} - Asiento {idasiento}:")
    print(f"{'ID':<6} {'Cuenta':<15} {'Concepto':<40} {'Debe':<12} {'Haber':<12}")
    print("-" * 85)

    debe_total = 0
    haber_total = 0
    for p in asiento_partidas:
        pid = p.get("idpartida", "?")
        cuenta = p.get("codsubcuenta", "")
        concepto = p.get("concepto", "")[:40]
        debe = p.get("debe", 0)
        haber = p.get("haber", 0)
        print(f"{pid:<6} {cuenta:<15} {concepto:<40} {debe:>11.2f} {haber:>11.2f}")
        debe_total += debe
        haber_total += haber

    print("-" * 85)
    print(f"{'TOTAL':<37} {debe_total:>11.2f} {haber_total:>11.2f}")
    cuadra = "OK CUADRA" if abs(debe_total - haber_total) < 0.01 else "ERROR NO CUADRA"
    print(f"{cuadra} (diferencia: {abs(debe_total - haber_total):.2f})")


def corregir_partida(id_partida: int, debe_nuevo: float) -> bool:
    """Corrige una partida con PUT."""
    try:
        url = f"{API_BASE}/partidas/{id_partida}"
        data = {"debe": debe_nuevo}
        resp = requests.put(url, data=data, headers=HEADERS)

        if resp.status_code in [200, 201]:
            print(f"  OK Partida {id_partida}: debe={debe_nuevo:.2f}")
            return True
        else:
            print(f"  FAIL Partida {id_partida}: {resp.status_code} {resp.text}")
            return False
    except requests.RequestException as e:
        print(f"  ✗ ERROR Partida {id_partida}: {e}")
        return False


def crear_partida_nueva(nueva_partida: Dict) -> bool:
    """Crea una nueva partida con POST."""
    try:
        url = f"{API_BASE}/partidas"
        resp = requests.post(url, data=nueva_partida, headers=HEADERS)

        if resp.status_code in [200, 201]:
            result = resp.json()
            print(f"  OK Nueva partida creada: {result.get('idpartida', result.get('id', '?'))} en asiento {nueva_partida['idasiento']}")
            return True
        else:
            print(f"  FAIL crear partida: {resp.status_code} {resp.text}")
            return False
    except requests.RequestException as e:
        print(f"  ✗ ERROR crear partida: {e}")
        return False


def main():
    print("=" * 85)
    print("CORRECCION DE SUPLIDOS PASTORINO (empresa 1, asientos 65-68)")
    print("=" * 85)

    # 1. Obtener todas las partidas
    print("\n[1] Obteniendo partidas de FacturaScripts...")
    partidas = obtener_todas_partidas()
    print(f"  Total: {len(partidas)} partidas obtenidas")

    # 2. Mostrar estado ANTES
    print("\n[2] ESTADO ANTES DE CORRECCIONES:")
    for asiento in [65, 66, 67, 68]:
        mostrar_partidas_asiento(partidas, asiento, "ANTES")

    # 3. Ejecutar correcciones
    print("\n[3] EJECUTANDO CORRECCIONES:")
    exitosas = 0
    total = 0

    for idasiento, correcciones in CORRECCIONES.items():
        print(f"\n  Asiento {idasiento}:")
        for id_partida, debe_nuevo in correcciones:
            total += 1
            if corregir_partida(id_partida, debe_nuevo):
                exitosas += 1

    # 4. Crear nueva partida en asiento 68
    print(f"\n  Asiento 68 (nueva partida):")
    total += 1
    if crear_partida_nueva(NUEVA_PARTIDA_68):
        exitosas += 1

    # 5. Recargar partidas para verificar
    print("\n[4] RECARGANDO PARTIDAS...")
    partidas = obtener_todas_partidas()

    # 6. Mostrar estado DESPUÉS
    print("\n[5] ESTADO DESPUES DE CORRECCIONES:")
    for asiento in [65, 66, 67, 68]:
        mostrar_partidas_asiento(partidas, asiento, "DESPUES")

    # 7. Resumen
    print("\n[6] RESUMEN:")
    print(f"  Cambios exitosos: {exitosas}/{total}")
    if exitosas == total:
        print("  TODAS LAS CORRECCIONES COMPLETADAS CON EXITO")
    else:
        print(f"  FALLARON {total - exitosas} cambios")

    print("\n" + "=" * 85)


if __name__ == "__main__":
    main()
