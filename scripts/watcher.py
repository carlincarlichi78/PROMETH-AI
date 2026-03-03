# scripts/watcher.py
"""Daemon local que monitoriza clientes/*/inbox/ y sube PDFs al servidor SFCE."""
from __future__ import annotations

import hashlib
import logging
import os
import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests
import yaml

RAIZ = Path(__file__).parent.parent
CLIENTES_DIR = RAIZ / os.getenv("SFCE_CLIENTES_DIR", "clientes")
API_URL = os.getenv("SFCE_WATCHER_API_URL", "https://api.prometh-ai.es")
PIPELINE_TOKEN = os.getenv("SFCE_WATCHER_TOKEN", "")
DEBOUNCE = int(os.getenv("SFCE_WATCHER_DEBOUNCE", "2"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("watcher")


def _esperar_estabilidad(
    ruta: Path, segundos: float = DEBOUNCE, intentos: int = 5
) -> bool:
    """Espera hasta que el tamaño del archivo no cambie entre dos lecturas.

    Retorna False si el archivo no existe o si agota los intentos sin estabilizarse.
    Un archivo de tamaño 0 nunca se considera estable (puede estar en creación).
    """
    tamanyo_anterior = -1
    for _ in range(intentos):
        try:
            tamanyo_actual = ruta.stat().st_size
        except FileNotFoundError:
            return False
        if tamanyo_actual == tamanyo_anterior and tamanyo_actual > 0:
            return True
        tamanyo_anterior = tamanyo_actual
        time.sleep(segundos)
    return False
