"""
Migración 001: crear tabla audit_log.
Ejecutar UNA sola vez: python sfce/db/migraciones/001_seguridad_base.py
Idempotente: usa CREATE TABLE IF NOT EXISTS.
"""
import os
import sqlite3

DB_PATH = os.environ.get("SFCE_DB_PATH", "./sfce.db")


def ejecutar():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS audit_log_seguridad (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            usuario_id INTEGER,
            email_usuario TEXT,
            rol TEXT,
            gestoria_id INTEGER,
            accion TEXT NOT NULL,
            recurso TEXT NOT NULL,
            recurso_id TEXT,
            ip_origen TEXT,
            resultado TEXT NOT NULL DEFAULT 'ok',
            detalles TEXT
        )
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS ix_audit_log_seg_timestamp
        ON audit_log_seguridad(timestamp)
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS ix_audit_log_seg_gestoria
        ON audit_log_seguridad(gestoria_id, timestamp)
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS ix_audit_log_seg_usuario
        ON audit_log_seguridad(email_usuario, timestamp)
    """)

    conn.commit()
    conn.close()
    print("Migracion 001 (audit_log) completada.")


if __name__ == "__main__":
    ejecutar()
