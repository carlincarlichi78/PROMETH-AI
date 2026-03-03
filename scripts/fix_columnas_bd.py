"""Añade todas las columnas faltantes en BD local."""
import os, sys
from pathlib import Path

env_path = Path(__file__).parent.parent / ".env"
for line in env_path.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

sys.path.insert(0, str(Path(__file__).parent.parent))
from sfce.db.base import crear_motor
from sfce.api.app import _leer_config_bd
from sqlalchemy import inspect, text

engine = crear_motor(_leer_config_bd())

fixes = [
    ("cola_procesamiento", "datos_ocr_json",           "TEXT"),
    ("cola_procesamiento", "coherencia_score",          "REAL"),
    ("cola_procesamiento", "empresa_origen_correo_id",  "INTEGER"),
    ("empresas",           "cnae",                      "TEXT"),
]

for tabla, col, tipo in fixes:
    cols = {c['name'] for c in inspect(engine).get_columns(tabla)}
    if col not in cols:
        with engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE {tabla} ADD COLUMN {col} {tipo}"))
        print(f"OK {tabla}.{col}")
    else:
        print(f"Ya existe {tabla}.{col}")

print("Listo.")
