"""Añade columnas faltantes a cola_procesamiento."""
import os, sys
from pathlib import Path

env_path = Path(__file__).parent.parent / ".env"
for line in env_path.read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

sys.path.insert(0, str(Path(__file__).parent.parent))
from sfce.db.base import crear_motor
from sfce.api.app import _leer_config_bd
from sqlalchemy import inspect, text

engine = crear_motor(_leer_config_bd())
cols = {c['name'] for c in inspect(engine).get_columns('cola_procesamiento')}

with engine.begin() as conn:
    if 'worker_inicio' not in cols:
        conn.execute(text("ALTER TABLE cola_procesamiento ADD COLUMN worker_inicio DATETIME"))
        print("OK worker_inicio")
    if 'reintentos' not in cols:
        conn.execute(text("ALTER TABLE cola_procesamiento ADD COLUMN reintentos INTEGER DEFAULT 0"))
        print("OK reintentos")

print("Listo.")
