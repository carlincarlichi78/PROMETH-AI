"""Migración 006: campos de invitación en usuarios + índice token."""
import sqlite3
from pathlib import Path

BD_RUTA = Path("sfce.db")


def migrar(ruta_bd: str = str(BD_RUTA)) -> None:
    conn = sqlite3.connect(ruta_bd)
    cur = conn.cursor()

    columnas = {r[1] for r in cur.execute("PRAGMA table_info(usuarios)")}

    if "invitacion_token" not in columnas:
        cur.execute("ALTER TABLE usuarios ADD COLUMN invitacion_token TEXT")
    if "invitacion_expira" not in columnas:
        cur.execute("ALTER TABLE usuarios ADD COLUMN invitacion_expira TEXT")
    if "forzar_cambio_password" not in columnas:
        cur.execute(
            "ALTER TABLE usuarios ADD COLUMN forzar_cambio_password INTEGER DEFAULT 0"
        )

    cur.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_usuarios_invitacion_token "
        "ON usuarios(invitacion_token) WHERE invitacion_token IS NOT NULL"
    )

    conn.commit()
    conn.close()
    print("Migración 006 completada.")


if __name__ == "__main__":
    migrar()
