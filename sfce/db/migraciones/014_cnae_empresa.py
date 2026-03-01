"""
Migración 014: campo cnae en tabla empresas (para Sector Brain / benchmarks sectoriales).

Idempotente: usa ALTER TABLE con try/except.
"""
from sqlalchemy import text


def ejecutar_migracion(engine) -> None:
    with engine.begin() as conn:
        try:
            conn.execute(text("ALTER TABLE empresas ADD COLUMN cnae VARCHAR(4)"))
        except Exception:
            pass  # Ya existe


if __name__ == "__main__":
    import os
    from sfce.db.base import crear_motor

    db_url = os.environ.get("SFCE_DB_URL", "sqlite:///sfce.db")
    eng = crear_motor(db_url)
    ejecutar_migracion(eng)
    print("Migración 014 ejecutada: campo cnae en empresas.")
