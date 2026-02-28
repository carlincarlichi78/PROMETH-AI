"""
Migracion 002: tabla gestorias + columnas multi-tenant en usuarios.
Ejecutar UNA sola vez: python sfce/db/migraciones/002_multi_tenant.py
"""
import sqlite3
import os

DB_PATH = os.environ.get("SFCE_DB_PATH", "./sfce.db")


def ejecutar():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Tabla gestorias
    cur.execute("""
        CREATE TABLE IF NOT EXISTS gestorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            email_contacto TEXT NOT NULL,
            cif TEXT,
            modulos TEXT NOT NULL DEFAULT '[]',
            plan_asesores INTEGER NOT NULL DEFAULT 1,
            plan_clientes_tramo TEXT NOT NULL DEFAULT '1-10',
            activa INTEGER NOT NULL DEFAULT 1,
            fecha_alta TEXT NOT NULL DEFAULT (datetime('now')),
            fecha_vencimiento TEXT
        )
    """)

    # Columnas multi-tenant en usuarios (idempotente)
    columnas_existentes = [row[1] for row in cur.execute("PRAGMA table_info(usuarios)")]
    if "gestoria_id" not in columnas_existentes:
        cur.execute("ALTER TABLE usuarios ADD COLUMN gestoria_id INTEGER REFERENCES gestorias(id)")
    if "empresas_asignadas" not in columnas_existentes:
        cur.execute("ALTER TABLE usuarios ADD COLUMN empresas_asignadas TEXT NOT NULL DEFAULT '[]'")

    # Tabla cuentas_bancarias
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cuentas_bancarias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            gestoria_id INTEGER NOT NULL,
            banco_codigo TEXT NOT NULL,
            banco_nombre TEXT NOT NULL,
            iban TEXT NOT NULL,
            alias TEXT NOT NULL DEFAULT '',
            divisa TEXT NOT NULL DEFAULT 'EUR',
            activa INTEGER NOT NULL DEFAULT 1,
            email_c43 TEXT,
            UNIQUE(empresa_id, iban)
        )
    """)

    # Extender movimientos_bancarios con campos nuevos
    col_mov = [row[1] for row in cur.execute("PRAGMA table_info(movimientos_bancarios)")]
    nuevas_columnas_mov = [
        ("cuenta_id", "INTEGER"),
        ("fecha_valor", "TEXT"),
        ("divisa", "TEXT NOT NULL DEFAULT 'EUR'"),
        ("importe_eur", "REAL"),
        ("tipo_cambio", "REAL"),
        ("signo", "TEXT NOT NULL DEFAULT 'D'"),
        ("concepto_comun", "TEXT NOT NULL DEFAULT ''"),
        ("referencia_1", "TEXT NOT NULL DEFAULT ''"),
        ("referencia_2", "TEXT NOT NULL DEFAULT ''"),
        ("nombre_contraparte", "TEXT NOT NULL DEFAULT ''"),
        ("tipo_clasificado", "TEXT"),
        ("estado_conciliacion", "TEXT NOT NULL DEFAULT 'pendiente'"),
        ("hash_unico", "TEXT"),
    ]
    for nombre_col, tipo_col in nuevas_columnas_mov:
        if nombre_col not in col_mov:
            cur.execute(f"ALTER TABLE movimientos_bancarios ADD COLUMN {nombre_col} {tipo_col}")

    # Rellenar hash_unico para movimientos existentes (valor temporal unico)
    cur.execute("""
        UPDATE movimientos_bancarios
        SET hash_unico = 'legacy_' || id
        WHERE hash_unico IS NULL
    """)
    try:
        cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_movbanco_hash ON movimientos_bancarios(hash_unico)")
    except Exception as e:
        print(f"Indice hash ya existia o error: {e}")

    # Tabla archivos_ingestados
    cur.execute("""
        CREATE TABLE IF NOT EXISTS archivos_ingestados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hash_archivo TEXT NOT NULL UNIQUE,
            nombre_original TEXT NOT NULL,
            fuente TEXT NOT NULL,
            tipo TEXT NOT NULL,
            empresa_id INTEGER NOT NULL,
            gestoria_id INTEGER NOT NULL,
            fecha_proceso TEXT NOT NULL,
            movimientos_totales INTEGER NOT NULL DEFAULT 0,
            movimientos_nuevos INTEGER NOT NULL DEFAULT 0,
            movimientos_duplicados INTEGER NOT NULL DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()
    print("Migracion 002 completada.")


if __name__ == "__main__":
    ejecutar()
