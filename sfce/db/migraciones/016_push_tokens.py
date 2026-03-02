"""Migración 016 — tabla push_tokens para Expo Push Notifications."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from sqlalchemy import text
from sfce.db.base import crear_motor


def ejecutar():
    motor = crear_motor()
    with motor.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS push_tokens (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id  INTEGER NOT NULL,
                empresa_id  INTEGER REFERENCES empresas(id),
                token       VARCHAR(200) NOT NULL UNIQUE,
                plataforma  VARCHAR(10),
                activo      INTEGER NOT NULL DEFAULT 1,
                fecha_registro DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                fecha_ultimo_uso DATETIME
            )
        """))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_push_usuario ON push_tokens(usuario_id)"
        ))
    print("Migración 016 — push_tokens: OK")


if __name__ == "__main__":
    ejecutar()
