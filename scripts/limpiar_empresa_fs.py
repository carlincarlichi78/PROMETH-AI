#!/usr/bin/env python3
"""
Limpia completamente una empresa de FacturaScripts y sus archivos locales.
Por defecto: empresa 4 (chiringuito-sol-arena).
"""

import os
import sys
import argparse
from pathlib import Path
import requests
from typing import List, Dict

# Setup
API_BASE = "https://contabilidad.lemonfresh-tuc.com/api/3"
API_TOKEN = os.getenv("FS_API_TOKEN", "iOXmrA1Bbn8RDWXLv91L")
HEADERS = {"Token": API_TOKEN}

# Raiz del proyecto
PROJECT_ROOT = Path(__file__).parent.parent


def obtener_todas_facturas_proveedor() -> List[Dict]:
    """Obtiene todas las facturas proveedor de la API (con paginacion)."""
    todas = []
    offset = 0
    try:
        while True:
            resp = requests.get(
                f"{API_BASE}/facturaproveedores",
                headers=HEADERS,
                params={"limit": 500, "offset": offset}
            )
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
        print(f"ERROR al obtener facturas proveedor: {e}")
        return []


def obtener_todas_facturas_cliente() -> List[Dict]:
    """Obtiene todas las facturas cliente de la API (con paginacion)."""
    todas = []
    offset = 0
    try:
        while True:
            resp = requests.get(
                f"{API_BASE}/facturaclientes",
                headers=HEADERS,
                params={"limit": 500, "offset": offset}
            )
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
        print(f"ERROR al obtener facturas cliente: {e}")
        return []


def obtener_todos_asientos() -> List[Dict]:
    """Obtiene todos los asientos de la API (con paginacion)."""
    todos = []
    offset = 0
    try:
        while True:
            resp = requests.get(
                f"{API_BASE}/asientos",
                headers=HEADERS,
                params={"limit": 500, "offset": offset}
            )
            resp.raise_for_status()
            lote = resp.json()
            if not lote:
                break
            todos.extend(lote)
            if len(lote) < 500:
                break
            offset += 500
        return todos
    except requests.RequestException as e:
        print(f"ERROR al obtener asientos: {e}")
        return []


def filtrar_por_empresa(items: List[Dict], idempresa: int) -> List[Dict]:
    """Filtra items por idempresa (post-filtrado manual)."""
    return [item for item in items if item.get("idempresa") == idempresa]


def eliminar_factura_cliente(idfactura: int, dry_run: bool = False) -> bool:
    """Elimina una factura cliente."""
    try:
        url = f"{API_BASE}/facturaclientes/{idfactura}"
        if dry_run:
            print(f"  [DRY-RUN] DELETE {url}")
            return True

        resp = requests.delete(url, headers=HEADERS)

        if resp.status_code in [200, 201, 204]:
            print(f"  OK FacturaCli {idfactura} eliminada")
            return True
        else:
            print(f"  FAIL FacturaCli {idfactura}: {resp.status_code}")
            return False
    except requests.RequestException as e:
        print(f"  ERROR FacturaCli {idfactura}: {e}")
        return False


def eliminar_factura_proveedor(idfactura: int, dry_run: bool = False) -> bool:
    """Elimina una factura proveedor."""
    try:
        url = f"{API_BASE}/facturaproveedores/{idfactura}"
        if dry_run:
            print(f"  [DRY-RUN] DELETE {url}")
            return True

        resp = requests.delete(url, headers=HEADERS)

        if resp.status_code in [200, 201, 204]:
            print(f"  OK Factura {idfactura} eliminada")
            return True
        else:
            print(f"  FAIL Factura {idfactura}: {resp.status_code}")
            return False
    except requests.RequestException as e:
        print(f"  ERROR Factura {idfactura}: {e}")
        return False


def eliminar_asiento(idasiento: int, dry_run: bool = False) -> bool:
    """Elimina un asiento."""
    try:
        url = f"{API_BASE}/asientos/{idasiento}"
        if dry_run:
            print(f"  [DRY-RUN] DELETE {url}")
            return True

        resp = requests.delete(url, headers=HEADERS)

        if resp.status_code in [200, 201, 204]:
            print(f"  OK Asiento {idasiento} eliminado")
            return True
        else:
            print(f"  FAIL Asiento {idasiento}: {resp.status_code}")
            return False
    except requests.RequestException as e:
        print(f"  ERROR Asiento {idasiento}: {e}")
        return False


def eliminar_archivos_cuarentena(empresa_nombre: str, dry_run: bool = False) -> int:
    """Elimina todos los PDFs de la carpeta cuarentena."""
    cuarentena_path = PROJECT_ROOT / "clientes" / empresa_nombre / "cuarentena"

    if not cuarentena_path.exists():
        print(f"  Carpeta {cuarentena_path} no existe")
        return 0

    pdfs = list(cuarentena_path.glob("*.pdf"))

    for pdf in pdfs:
        if dry_run:
            print(f"  [DRY-RUN] rm {pdf}")
        else:
            try:
                pdf.unlink()
                print(f"  OK {pdf.name} eliminado")
            except OSError as e:
                print(f"  ERROR eliminando {pdf.name}: {e}")

    return len(pdfs)


def resetear_pipeline_state(empresa_nombre: str, dry_run: bool = False) -> bool:
    """Resetea el archivo pipeline_state.json."""
    state_path = PROJECT_ROOT / "clientes" / empresa_nombre / "pipeline_state.json"

    if state_path.exists():
        if dry_run:
            print(f"  [DRY-RUN] resetear {state_path}")
            return True

        try:
            state_path.write_text("""{
  "hashes_procesados": [],
  "hashes_registrados_fs": [],
  "fases_completadas": [],
  "historial_confianza": [],
  "alertas_recurrentes": []
}
""")
            print(f"  OK pipeline_state.json reseteado")
            return True
        except OSError as e:
            print(f"  ERROR reseteando pipeline_state.json: {e}")
            return False
    else:
        print(f"  pipeline_state.json no existe")
        return True


def obtener_nombre_empresa(idempresa: int) -> str:
    """Obtiene el nombre de carpeta de la empresa."""
    mapping = {
        1: "pastorino-costa-del-sol",
        2: "gerardo-gonzalez-callejon",
        3: "EMPRESA PRUEBA",
        4: "chiringuito-sol-arena",
        5: "elena-navarro",
    }
    return mapping.get(idempresa, f"empresa_{idempresa}")


def main():
    parser = argparse.ArgumentParser(
        description="Limpia completamente una empresa de FacturaScripts y sus archivos locales"
    )
    parser.add_argument("--empresa", type=int, default=4, help="ID de empresa (default: 4)")
    parser.add_argument("--dry-run", action="store_true", help="Solo muestra que haria sin ejecutar")
    args = parser.parse_args()

    idempresa = args.empresa
    empresa_nombre = obtener_nombre_empresa(idempresa)
    dry_run = args.dry_run

    print("=" * 85)
    print(f"LIMPIAR EMPRESA {idempresa} ({empresa_nombre})")
    if dry_run:
        print("MODO DRY-RUN (no se ejecutan cambios)")
    print("=" * 85)

    # 1. Obtener y filtrar facturas proveedor
    print(f"\n[1] Eliminando facturas proveedor de empresa {idempresa}...")
    todas_facturas = obtener_todas_facturas_proveedor()
    print(f"  Total en FS: {len(todas_facturas)} facturas")
    facturas = filtrar_por_empresa(todas_facturas, idempresa)
    print(f"  Empresa {idempresa}: {len(facturas)} facturas")

    facturas_eliminadas = 0
    for factura in facturas:
        if eliminar_factura_proveedor(factura.get("idfactura"), dry_run=dry_run):
            facturas_eliminadas += 1

    # 1b. Obtener y filtrar facturas cliente
    print(f"\n[1b] Eliminando facturas cliente de empresa {idempresa}...")
    todas_facturas_cli = obtener_todas_facturas_cliente()
    print(f"  Total en FS: {len(todas_facturas_cli)} facturas cliente")
    facturas_cli = filtrar_por_empresa(todas_facturas_cli, idempresa)
    print(f"  Empresa {idempresa}: {len(facturas_cli)} facturas cliente")

    facturas_cli_eliminadas = 0
    for factura in facturas_cli:
        if eliminar_factura_cliente(factura.get("idfactura"), dry_run=dry_run):
            facturas_cli_eliminadas += 1

    # 2. Obtener y filtrar asientos
    print(f"\n[2] Eliminando asientos de empresa {idempresa}...")
    todos_asientos = obtener_todos_asientos()
    print(f"  Total en FS: {len(todos_asientos)} asientos")
    asientos = filtrar_por_empresa(todos_asientos, idempresa)
    print(f"  Empresa {idempresa}: {len(asientos)} asientos")

    asientos_eliminados = 0
    for asiento in asientos:
        if eliminar_asiento(asiento.get("idasiento"), dry_run=dry_run):
            asientos_eliminados += 1

    # 3. Eliminar archivos de cuarentena
    print(f"\n[3] Eliminando PDFs de cuarentena...")
    pdfs_eliminados = eliminar_archivos_cuarentena(empresa_nombre, dry_run=dry_run)
    print(f"  Encontrados y eliminados: {pdfs_eliminados} archivos")

    # 4. Resetear pipeline_state.json
    print(f"\n[4] Reseteando pipeline_state.json...")
    resetear_pipeline_state(empresa_nombre, dry_run=dry_run)

    # 5. Resumen
    print("\n" + "=" * 85)
    print("RESUMEN:")
    print(f"  Facturas proveedor eliminadas: {facturas_eliminadas}/{len(facturas)}")
    print(f"  Facturas cliente eliminadas: {facturas_cli_eliminadas}/{len(facturas_cli)}")
    print(f"  Asientos eliminados: {asientos_eliminados}/{len(asientos)}")
    print(f"  Archivos PDFs eliminados: {pdfs_eliminados}")
    print(f"  pipeline_state.json: reseteado")

    if dry_run:
        print("\n[DRY-RUN] Use sin --dry-run para ejecutar los cambios")

    print("=" * 85)


if __name__ == "__main__":
    main()
