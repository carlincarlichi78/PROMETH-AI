"""Migración 017 — reset_token en usuarios."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def ejecutar():
    from sfce.db.base import crear_motor
    from sqlalchemy import text

    engine = crear_motor()
    with engine.begin() as conn:
        # Columnas idempotentes
        for col, definicion in [
            ("reset_token", "VARCHAR(128)"),
            ("reset_token_expira", "TIMESTAMP"),
        ]:
            if engine.dialect.name == "postgresql":
                conn.execute(text(f"""
                    ALTER TABLE usuarios
                    ADD COLUMN IF NOT EXISTS {col} {definicion}
                """))
            else:
                # SQLite: verificar si ya existe
                cols = [r[1] for r in conn.execute(text("PRAGMA table_info(usuarios)"))]
                if col not in cols:
                    conn.execute(text(f"ALTER TABLE usuarios ADD COLUMN {col} {definicion}"))

    print("Migración 017 — reset_password: OK")


if __name__ == "__main__":
    ejecutar()
