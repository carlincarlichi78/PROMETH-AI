#!/usr/bin/env python3
"""
Migración one-time: SQLite → PostgreSQL.

IMPORTANTE: Ejecutar SOLO UNA VEZ antes del primer deploy a producción.

Uso:
    # Primero probar sin escribir:
    python scripts/migrar_sqlite_a_postgres.py --dry-run

    # Migrar (conectando a PostgreSQL del servidor via túnel SSH):
    # ssh -L 5434:127.0.0.1:5433 carli@65.108.60.69 -N &
    SFCE_DB_HOST=localhost SFCE_DB_PORT=5434 \\
    SFCE_DB_USER=sfce_user SFCE_DB_PASSWORD=xxx SFCE_DB_NAME=sfce_prod \\
    SFCE_DB_PATH=sfce.db python scripts/migrar_sqlite_a_postgres.py

Variables de entorno:
    SFCE_DB_PATH      Ruta al sfce.db local (default: sfce.db en cwd)
    SFCE_DB_HOST      Host PostgreSQL destino
    SFCE_DB_PORT      Puerto PostgreSQL (default: 5432)
    SFCE_DB_USER      Usuario PostgreSQL
    SFCE_DB_PASSWORD  Contraseña PostgreSQL
    SFCE_DB_NAME      Nombre de base de datos PostgreSQL
"""
import argparse
import os
import sqlite3
import sys
from pathlib import Path

# Añadir raíz del proyecto al path
sys.path.insert(0, str(Path(__file__).parent.parent))


def _dsn_postgres() -> str:
    host = os.environ.get("SFCE_DB_HOST")
    port = os.environ.get("SFCE_DB_PORT", "5432")
    user = os.environ.get("SFCE_DB_USER")
    password = os.environ.get("SFCE_DB_PASSWORD")
    name = os.environ.get("SFCE_DB_NAME")

    if not all([host, user, password, name]):
        print("ERROR: Faltan variables de entorno para PostgreSQL.")
        print("  Requeridas: SFCE_DB_HOST, SFCE_DB_USER, SFCE_DB_PASSWORD, SFCE_DB_NAME")
        sys.exit(1)

    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}"


def migrar(dry_run: bool = False) -> None:
    sqlite_path = Path(os.environ.get("SFCE_DB_PATH", "sfce.db"))

    if not sqlite_path.exists():
        print(f"ERROR: '{sqlite_path}' no encontrado")
        print("  Ejecutar desde la raíz del proyecto o definir SFCE_DB_PATH.")
        sys.exit(1)

    host = os.environ.get("SFCE_DB_HOST")
    port = os.environ.get("SFCE_DB_PORT", "5432")
    name = os.environ.get("SFCE_DB_NAME")

    # En dry-run sin vars PG, solo analizar SQLite
    if not dry_run:
        dsn = _dsn_postgres()
    else:
        dsn = None

    print(f"Origen:      SQLite {sqlite_path} ({sqlite_path.stat().st_size / 1024:.0f} KB)")
    print(f"Destino:     PostgreSQL {host}:{port}/{name}")
    print(f"Modo:        {'DRY RUN (sin escrituras)' if dry_run else 'MIGRACIÓN REAL'}")
    print()

    from sqlalchemy import create_engine, text

    # Importar modelos para registrarlos en metadata de SQLAlchemy
    from sfce.db.base import Base
    import sfce.db.modelos       # noqa: F401
    import sfce.db.modelos_auth  # noqa: F401

    # Conectar SQLite
    sqlite_conn = sqlite3.connect(str(sqlite_path))
    sqlite_conn.row_factory = sqlite3.Row

    if not dry_run:
        # Conectar PostgreSQL y crear esquema
        pg_engine = create_engine(dsn, echo=False)
        try:
            with pg_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("✓ Conexión PostgreSQL OK")
        except Exception as e:
            print(f"ERROR: No se puede conectar a PostgreSQL: {e}")
            sys.exit(1)
        print("Creando esquema en PostgreSQL...")
        Base.metadata.create_all(pg_engine)
        print("✓ Esquema creado")
    else:
        pg_engine = None

    # Orden topológico de SQLAlchemy (padres antes que hijos por FKs)
    tablas_orm_orden = [t.name for t in Base.metadata.sorted_tables]

    # Tablas SQLite (excluyendo internas)
    cursor = sqlite_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )
    tablas_sqlite = {row[0] for row in cursor.fetchall()}

    # Priorizar orden topológico; las tablas no en el ORM van al final
    tablas = [t for t in tablas_orm_orden if t in tablas_sqlite]
    tablas += [t for t in tablas_sqlite if t not in tablas_orm_orden]
    print(f"\nTablas a migrar ({len(tablas)}): {tablas}\n")

    resumen = {}

    for tabla in tablas:
        try:
            filas = sqlite_conn.execute(f"SELECT * FROM {tabla}").fetchall()  # noqa: S608
        except sqlite3.Error as e:
            print(f"  {tabla}: SKIP (error lectura: {e})")
            continue

        if not filas:
            print(f"  {tabla}: vacía, skip")
            resumen[tabla] = 0
            continue

        if dry_run:
            print(f"  {tabla}: {len(filas)} filas (dry run)")
            resumen[tabla] = len(filas)
            continue

        # Nombres de columnas
        cols = [d[0] for d in sqlite_conn.execute(f"SELECT * FROM {tabla} LIMIT 0").description]  # noqa: S608
        col_list = ", ".join(f'"{c}"' for c in cols)
        placeholders = ", ".join(f":{c}" for c in cols)

        # Detectar columnas boolean en el modelo SQLAlchemy para castear 0/1 → bool
        from sqlalchemy import Boolean as SABoolean, inspect as sa_inspect
        bool_cols: set[str] = set()
        try:
            orm_table = Base.metadata.tables.get(tabla)
            if orm_table is not None:
                for col in orm_table.columns:
                    if isinstance(col.type, SABoolean):
                        bool_cols.add(col.name)
        except Exception:
            pass

        def _preparar_fila(row_dict: dict) -> dict:
            """Castea 0/1 → bool para columnas boolean (SQLite → PostgreSQL)."""
            if not bool_cols:
                return row_dict
            return {
                k: bool(v) if k in bool_cols and v is not None else v
                for k, v in row_dict.items()
            }

        # Insert con ON CONFLICT DO NOTHING (idempotente — seguro re-ejecutar)
        sql = text(
            f'INSERT INTO "{tabla}" ({col_list}) VALUES ({placeholders}) '  # noqa: S608
            f"ON CONFLICT DO NOTHING"
        )

        insertados = 0
        errores = 0
        with pg_engine.connect() as pg_conn:
            for fila in filas:
                sp = pg_conn.begin_nested()  # savepoint por fila
                try:
                    pg_conn.execute(sql, _preparar_fila(dict(zip(cols, fila))))
                    sp.commit()
                    insertados += 1
                except Exception as e:
                    sp.rollback()
                    errores += 1
                    if errores <= 3:  # mostrar solo los primeros errores
                        print(f"    WARN fila {tabla}: {e}")
            pg_conn.commit()

        estado = f"{insertados}/{len(filas)} filas"
        if errores:
            estado += f" ({errores} errores)"
        print(f"  {tabla}: {estado}")
        resumen[tabla] = insertados

    print("\n" + "=" * 50)
    print("RESUMEN:")
    total = sum(resumen.values())
    for tabla, n in resumen.items():
        print(f"  {tabla:40s} {n:>6} filas")
    print(f"  {'TOTAL':40s} {total:>6} filas")
    print()

    if dry_run:
        print("Dry run completado. Ejecutar sin --dry-run para migrar.")
    else:
        print("✓ Migración completada.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migra sfce.db SQLite → PostgreSQL")
    parser.add_argument("--dry-run", action="store_true",
                        help="Solo leer SQLite, no escribir en PostgreSQL")
    args = parser.parse_args()
    migrar(dry_run=args.dry_run)
