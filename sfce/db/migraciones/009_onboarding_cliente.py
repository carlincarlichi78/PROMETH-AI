"""Migración 009: onboarding_cliente + estado_onboarding en empresas."""
import sqlite3
import os

DB_PATH = os.environ.get("SFCE_DB_PATH", "./sfce.db")


def ejecutar():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Añadir estado_onboarding a empresas (idempotente)
    cols = [row[1] for row in cur.execute("PRAGMA table_info(empresas)")]
    if "estado_onboarding" not in cols:
        cur.execute(
            "ALTER TABLE empresas ADD COLUMN estado_onboarding TEXT NOT NULL DEFAULT 'configurada'"
        )

    # Crear tabla onboarding_cliente
    cur.execute("""
        CREATE TABLE IF NOT EXISTS onboarding_cliente (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL UNIQUE REFERENCES empresas(id),
            iban TEXT,
            banco_nombre TEXT,
            email_facturas TEXT,
            proveedores_json TEXT NOT NULL DEFAULT '[]',
            completado_en TEXT,
            completado_por INTEGER REFERENCES usuarios(id)
        )
    """)

    conn.commit()
    conn.close()
    print("Migracion 009 completada.")


if __name__ == "__main__":
    ejecutar()
