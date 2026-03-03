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


def _cargar_empresa_id(slug: str) -> Optional[int]:
    """Lee sfce.empresa_id del config.yaml del cliente. Retorna None si no existe."""
    config_path = CLIENTES_DIR / slug / "config.yaml"
    if not config_path.exists():
        return None
    with open(config_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return cfg.get("sfce", {}).get("empresa_id")


def _slug_desde_ruta(ruta: Path) -> Optional[str]:
    """Extrae el slug del cliente desde la ruta.

    Solo considera rutas en clientes/{slug}/inbox/{archivo}.
    Ignora archivos en subido/ o error/ (ya procesados).
    """
    try:
        rel = ruta.relative_to(CLIENTES_DIR)
    except ValueError:
        return None
    parts = rel.parts
    # Estructura esperada: (slug, "inbox", archivo.pdf)
    if len(parts) != 3:
        return None
    slug, carpeta, _ = parts
    if carpeta != "inbox":
        return None
    return slug


def _subir_pdf(ruta: Path, empresa_id: int) -> str:
    """Sube el PDF al servidor SFCE.

    Retorna 'subido' (201) o 'duplicado' (200 con estado duplicado).
    Lanza excepción en cualquier otro caso.
    """
    with open(ruta, "rb") as f:
        resp = requests.post(
            f"{API_URL}/api/pipeline/documentos/subir",
            headers={"X-Pipeline-Token": PIPELINE_TOKEN},
            data={"empresa_id": empresa_id},
            files={"archivo": (ruta.name, f, "application/pdf")},
            timeout=60,
        )
    if resp.status_code == 201:
        return "subido"
    if resp.status_code == 200 and resp.json().get("estado") == "duplicado":
        return "duplicado"
    resp.raise_for_status()
    return "subido"  # unreachable


def _subir_con_reintentos(
    ruta: Path,
    empresa_id: int,
    max_reintentos: int = 3,
    backoff: tuple = (5, 15, 30),
) -> str:
    """Intenta subir el PDF con reintentos y backoff exponencial.

    Lanza la última excepción si agota todos los reintentos.
    """
    ultimo_error: Exception = RuntimeError("sin intentos")
    for intento in range(max_reintentos):
        try:
            return _subir_pdf(ruta, empresa_id)
        except Exception as e:
            ultimo_error = e
            if intento < len(backoff):
                espera = backoff[intento]
                logger.warning(
                    "Intento %d/%d fallido para %s: %s. Reintentando en %ds",
                    intento + 1,
                    max_reintentos,
                    ruta.name,
                    e,
                    espera,
                )
                time.sleep(espera)
    raise ultimo_error
