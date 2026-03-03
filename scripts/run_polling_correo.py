"""Ejecuta el polling de correo manualmente para debug."""
import os, sys, logging
from pathlib import Path

logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(name)s: %(message)s")

env_path = Path(__file__).parent.parent / ".env"
for line in env_path.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

sys.path.insert(0, str(Path(__file__).parent.parent))
from sfce.db.base import crear_motor
from sfce.api.app import _leer_config_bd
from sfce.conectores.correo.ingesta_correo import ejecutar_polling_todas_las_cuentas

engine = crear_motor(_leer_config_bd())
print("Ejecutando polling...")
ejecutar_polling_todas_las_cuentas(engine)
print("Polling completado.")
