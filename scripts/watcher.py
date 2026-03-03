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
from watchdog.events import FileSystemEventHandler, FileCreatedEvent
from watchdog.observers import Observer

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


_en_vuelo: set[str] = set()  # SHA256 de archivos siendo procesados


def _procesar_archivo(ruta: Path) -> None:
    """Procesa un único archivo PDF: verifica estabilidad, sube y reubica."""
    if not ruta.exists():
        return

    slug = _slug_desde_ruta(ruta)
    if slug is None:
        return  # archivo en subido/ o error/ — ignorar

    if not _esperar_estabilidad(ruta):
        logger.warning("Archivo inestable o desaparecido: %s", ruta.name)
        return

    try:
        sha = hashlib.sha256(ruta.read_bytes()).hexdigest()
    except OSError:
        return

    if sha in _en_vuelo:
        logger.debug("Ya en proceso (hash duplicado): %s", ruta.name)
        return

    _en_vuelo.add(sha)
    try:
        empresa_id = _cargar_empresa_id(slug)
        if empresa_id is None:
            logger.warning(
                "sfce.empresa_id ausente en config de '%s'. Ignorando %s",
                slug,
                ruta.name,
            )
            return

        resultado = _subir_con_reintentos(ruta, empresa_id)

        # Mover a subido/YYYY-MM-DD/
        fecha = datetime.now().strftime("%Y-%m-%d")
        destino_dir = ruta.parent / "subido" / fecha
        destino_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(ruta), str(destino_dir / ruta.name))
        logger.info("[%s] %s → %s/inbox/subido/%s/", resultado, ruta.name, slug, fecha)

    except Exception as e:
        logger.error("Error procesando %s: %s", ruta.name, e)
        error_dir = ruta.parent / "error"
        error_dir.mkdir(exist_ok=True)
        try:
            shutil.move(str(ruta), str(error_dir / ruta.name))
        except OSError:
            pass
    finally:
        _en_vuelo.discard(sha)


def startup_scan(callback=None) -> None:
    """Escanea inbox/ de todos los clientes al arrancar y procesa PDFs existentes.

    El parámetro callback se usa en tests para interceptar los archivos encontrados.
    En producción, cada PDF se envía a _procesar_archivo.
    """
    fn = callback if callback is not None else _procesar_archivo
    for inbox_dir in CLIENTES_DIR.glob("*/inbox"):
        for pdf in inbox_dir.glob("*.pdf"):
            # Solo archivos directamente en inbox/, no en subdirectorios
            if pdf.parent == inbox_dir:
                fn(pdf)


class InboxEventHandler(FileSystemEventHandler):
    """Watchdog handler: procesa PDFs creados en inbox/."""

    def __init__(self, executor: ThreadPoolExecutor):
        self._executor = executor

    def on_created(self, event: FileCreatedEvent) -> None:
        if event.is_directory:
            return
        ruta = Path(event.src_path)
        if ruta.suffix.lower() != ".pdf":
            return
        # Solo archivos en inbox/ directo (no en subdirectorios subido/error/)
        slug = _slug_desde_ruta(ruta)
        if slug is None:
            return
        logger.info("Nuevo archivo detectado: %s", ruta.name)
        self._executor.submit(_procesar_archivo, ruta)


def main() -> None:
    """Punto de entrada del daemon. Ctrl+C para detener."""
    logger.info("=" * 60)
    logger.info("SFCE Inbox Watcher arrancando")
    logger.info("Monitorizando: %s", CLIENTES_DIR)
    logger.info("API URL: %s", API_URL)
    logger.info("=" * 60)

    if not PIPELINE_TOKEN:
        logger.error("SFCE_WATCHER_TOKEN no configurado. Saliendo.")
        raise SystemExit(1)

    if not CLIENTES_DIR.exists():
        logger.error("Directorio clientes no encontrado: %s", CLIENTES_DIR)
        raise SystemExit(1)

    executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="watcher")

    # Procesar PDFs que ya estaban al arrancar
    logger.info("Startup scan...")
    startup_scan()

    handler = InboxEventHandler(executor)
    observer = Observer()
    observer.schedule(handler, str(CLIENTES_DIR), recursive=True)
    observer.start()
    logger.info("Observer iniciado. Esperando cambios...")

    try:
        while observer.is_alive():
            observer.join(timeout=5)
    except KeyboardInterrupt:
        logger.info("Señal de parada recibida")
    finally:
        observer.stop()
        observer.join()
        executor.shutdown(wait=False)
        logger.info("Watcher detenido")


if __name__ == "__main__":
    main()
