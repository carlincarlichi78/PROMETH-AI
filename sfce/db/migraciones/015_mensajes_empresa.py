"""Migración 015 — tabla mensajes_empresa para comunicación contextual."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from sqlalchemy import text
from sfce.db.base import crear_motor


def ejecutar():
    motor = crear_motor()
    with motor.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS mensajes_empresa (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id  INTEGER NOT NULL REFERENCES empresas(id),
                autor_id    INTEGER NOT NULL,
                contenido   TEXT NOT NULL,
                contexto_tipo VARCHAR(20),
                contexto_id   INTEGER,
                contexto_desc VARCHAR(200),
                leido_cliente INTEGER NOT NULL DEFAULT 0,
                leido_gestor  INTEGER NOT NULL DEFAULT 0,
                fecha_creacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_mensaje_empresa ON mensajes_empresa(empresa_id)"
        ))
    print("Migración 015 — mensajes_empresa: OK")


if __name__ == "__main__":
    ejecutar()
