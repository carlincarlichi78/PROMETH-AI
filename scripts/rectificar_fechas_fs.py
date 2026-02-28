"""
Script one-shot: rectifica fechas erróneas en BD local consultando FS API.

Las fechas se guardaron como 2026-02-28 (fecha de migración) porque _parsear_fecha
no soportaba el formato DD-MM-YYYY de FS. Este script las corrige leyendo la API.

Uso:
    export $(grep -v '^#' .env | xargs)
    python scripts/rectificar_fechas_fs.py --dry-run
    python scripts/rectificar_fechas_fs.py --empresa 4
    python scripts/rectificar_fechas_fs.py  # todas las empresas
"""
import argparse
import os
import sqlite3
from datetime import datetime, date
from pathlib import Path

import requests

FS_BASE = "https://contabilidad.lemonfresh-tuc.com/api/3"
TOKEN = os.environ.get("FS_API_TOKEN", "")
HEADERS = {"Token": TOKEN}
DB_PATH = Path(__file__).parent.parent / "sfce.db"


def _parsear_fecha(fecha_str: str) -> date | None:
    if not fecha_str:
        return None
    s = str(fecha_str).strip()[:10]
    for fmt in ("%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _fetch_todos(endpoint: str) -> list[dict]:
    """Descarga todos los registros paginando de 500 en 500."""
    resultados = []
    offset = 0
    while True:
        url = f"{FS_BASE}/{endpoint}?limit=500&offset={offset}"
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        datos = r.json()
        if not datos:
            break
        resultados.extend(datos)
        if len(datos) < 500:
            break
        offset += 500
    return resultados


def rectificar_asientos(conn: sqlite3.Connection, dry_run: bool, empresa_id: int | None) -> int:
    """Actualiza fechas de la tabla asientos."""
    print("Descargando asientos desde FS API...")
    datos = _fetch_todos("asientos")
    print(f"  {len(datos)} asientos recibidos")

    # Construir dict {idasiento_fs: fecha_real}
    mapa: dict[int, date] = {}
    for a in datos:
        idasiento = a.get("idasiento")
        fecha = _parsear_fecha(a.get("fecha", ""))
        if idasiento and fecha:
            mapa[int(idasiento)] = fecha

    # Filtrar solo los que tienen idasiento_fs en BD
    where = "WHERE idasiento_fs IS NOT NULL AND fecha = '2026-02-28'"
    if empresa_id:
        where += f" AND empresa_id = {empresa_id}"

    filas = conn.execute(f"SELECT id, idasiento_fs FROM asientos {where}").fetchall()
    print(f"  {len(filas)} asientos con fecha incorrecta en BD")

    actualizados = 0
    batch = []
    for row_id, idasiento_fs in filas:
        fecha_real = mapa.get(idasiento_fs)
        if fecha_real:
            batch.append((fecha_real.isoformat(), row_id))
            actualizados += 1

    if not dry_run and batch:
        conn.executemany("UPDATE asientos SET fecha = ? WHERE id = ?", batch)
        conn.commit()
        print(f"  OK: {actualizados} asientos actualizados")
    else:
        print(f"  [dry-run] {actualizados} asientos se actualizarían")

    return actualizados


def rectificar_facturas(conn: sqlite3.Connection, dry_run: bool, empresa_id: int | None) -> int:
    """Actualiza fechas y nombres de facturas emitidas y recibidas."""
    total = 0

    for endpoint, tipo in [("facturaclientes", "emitida"), ("facturaproveedores", "recibida")]:
        print(f"Descargando {endpoint} desde FS API...")
        datos = _fetch_todos(endpoint)
        print(f"  {len(datos)} {tipo} recibidas")

        mapa_fecha: dict[int, date] = {}
        mapa_nombre: dict[int, str] = {}
        for f in datos:
            id_fs = f.get("idfactura")
            fecha = _parsear_fecha(f.get("fecha", ""))
            if id_fs and fecha:
                mapa_fecha[int(id_fs)] = fecha
            # Nombre receptor (solo FC emitidas — cliente)
            if tipo == "emitida":
                nombre = f.get("nombrecliente", "")
                if id_fs and nombre:
                    mapa_nombre[int(id_fs)] = nombre

        where = f"WHERE idfactura_fs IS NOT NULL AND tipo = '{tipo}' AND fecha_factura = '2026-02-28'"
        if empresa_id:
            where += f" AND empresa_id = {empresa_id}"

        filas = conn.execute(f"SELECT id, idfactura_fs FROM facturas {where}").fetchall()
        print(f"  {len(filas)} {tipo} con fecha incorrecta en BD")

        batch_fecha = []
        batch_nombre = []
        for row_id, idfactura_fs in filas:
            fecha_real = mapa_fecha.get(idfactura_fs)
            if fecha_real:
                batch_fecha.append((fecha_real.isoformat(), row_id))
            nombre = mapa_nombre.get(idfactura_fs)
            if nombre and tipo == "emitida":
                batch_nombre.append((nombre, row_id))

        if not dry_run:
            if batch_fecha:
                conn.executemany("UPDATE facturas SET fecha_factura = ? WHERE id = ?", batch_fecha)
            if batch_nombre:
                conn.executemany("UPDATE facturas SET nombre_receptor = ? WHERE id = ?", batch_nombre)
            conn.commit()
            print(f"  OK: {len(batch_fecha)} fechas, {len(batch_nombre)} nombres actualizados")
        else:
            print(f"  [dry-run] {len(batch_fecha)} fechas, {len(batch_nombre)} nombres se actualizarían")

        total += len(batch_fecha)

    return total


def main():
    parser = argparse.ArgumentParser(description="Rectificar fechas en BD desde FS API")
    parser.add_argument("--dry-run", action="store_true", help="Mostrar cambios sin aplicar")
    parser.add_argument("--empresa", type=int, default=None, help="Filtrar por empresa_id")
    args = parser.parse_args()

    if not TOKEN:
        print("ERROR: FS_API_TOKEN no configurado. Ejecuta: export $(grep -v '^#' .env | xargs)")
        return 1

    conn = sqlite3.connect(DB_PATH)
    try:
        print(f"BD: {DB_PATH}")
        print(f"Modo: {'DRY RUN' if args.dry_run else 'APLICAR CAMBIOS'}")
        print()

        n_asientos = rectificar_asientos(conn, args.dry_run, args.empresa)
        n_facturas = rectificar_facturas(conn, args.dry_run, args.empresa)

        print()
        print(f"Total: {n_asientos} asientos + {n_facturas} facturas")

        if not args.dry_run:
            # Verificación final
            incorrectas = conn.execute(
                "SELECT COUNT(*) FROM asientos WHERE fecha = '2026-02-28'"
            ).fetchone()[0]
            print(f"Asientos con fecha 2026-02-28 restantes: {incorrectas}")
            if incorrectas == 0:
                print("OK: Rectificación completa")
            else:
                print(f"AVISO: Quedan {incorrectas} asientos sin rectificar (sin idasiento_fs)")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    exit(main())
