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

    conn.commit()
    conn.close()
    print("Migracion 002 completada.")


if __name__ == "__main__":
    ejecutar()
