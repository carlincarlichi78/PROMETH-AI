"""Arranca la API SFCE cargando .env correctamente."""
import os
from pathlib import Path

# Cargar .env antes de importar nada
env_path = Path(__file__).parent / ".env"
for line in env_path.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

import uvicorn
uvicorn.run("sfce.api.app:crear_app", factory=True, host="0.0.0.0", port=8000, reload=False)
