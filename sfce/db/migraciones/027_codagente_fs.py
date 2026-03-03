"""
Migración 027: codagente_fs en tabla empresas

Añade el campo codagente_fs (VARCHAR 10) a la tabla empresas.
Almacena el código del agente FacturaScripts asignado a cada empresa,
usado por el pipeline al crear documentos para respetar el filtro
'mostrar solamente registros del usuario' por grupo.

Mapeo por instancia FS:
  fs-uralde:    PASTORINO→FRANC, GERARDO→MGARC, CHIRINGUITO→MGARC, ELENA→LLUPI
  fs-gestoriaa: MARCOS→GEST1, LAMAREA→GEST2, AURORA→GEST1, CATERING→GEST2, DISTRIB→GEST1
  fs-javier:    sin asignación (javier es usuario único, sin restricción de grupo)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))


def migrar(motor):
    from sqlalchemy import text

    dialect = motor.dialect.name

    with motor.begin() as conn:
        if dialect == "postgresql":
            conn.execute(text(
                "ALTER TABLE empresas ADD COLUMN IF NOT EXISTS "
                "codagente_fs VARCHAR(10) DEFAULT NULL"
            ))
        else:
            # SQLite no soporta ADD COLUMN IF NOT EXISTS — verificar antes
            cols = [r[1] for r in conn.execute(text("PRAGMA table_info(empresas)")).fetchall()]
            if "codagente_fs" not in cols:
                conn.execute(text(
                    "ALTER TABLE empresas ADD COLUMN codagente_fs VARCHAR(10) DEFAULT NULL"
                ))

    print("OK Columna codagente_fs añadida (o ya existía)")


if __name__ == "__main__":
    import os
    from sqlalchemy import create_engine
    dsn = os.environ.get("DATABASE_URL", "sqlite:///sfce.db")
    motor = create_engine(dsn)
    migrar(motor)
    print("Migración 027 completada")
