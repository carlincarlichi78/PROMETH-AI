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
