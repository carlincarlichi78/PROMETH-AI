"""Logger unificado para SFCE con salida a consola y archivo."""
import json
import logging
import sys
from pathlib import Path
from datetime import datetime


def crear_logger(nombre: str, ruta_log: Path = None, nivel: int = logging.INFO) -> logging.Logger:
    """Crea logger con formato consistente para consola + archivo.

    Args:
        nombre: nombre del logger (ej: 'pipeline', 'intake')
        ruta_log: ruta al archivo .log (si None, solo consola)
        nivel: nivel de logging (default INFO)

    Returns:
        Logger configurado con handlers consola + archivo
    """
    logger = logging.getLogger(f"sfce.{nombre}")
    logger.setLevel(nivel)

    # Evitar duplicar handlers si se llama multiples veces
    if logger.handlers:
        return logger

    formato = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Consola
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(nivel)
    ch.setFormatter(formato)
    logger.addHandler(ch)

    # Archivo (si se especifica ruta)
    if ruta_log:
        ruta_log.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(ruta_log, encoding="utf-8")
        fh.setLevel(logging.DEBUG)  # Archivo siempre DEBUG
        fh.setFormatter(formato)
        logger.addHandler(fh)

    return logger


class AuditoriaLogger:
    """Registra cada accion del pipeline para auditoria."""

    def __init__(self, ruta_auditoria: Path):
        self.ruta = ruta_auditoria
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        self.registros = []
        self.inicio = datetime.now()

    def registrar(self, fase: str, tipo: str, detalle: str, datos: dict = None):
        """Registra una accion/verificacion/error."""
        registro = {
            "timestamp": datetime.now().isoformat(),
            "fase": fase,
            "tipo": tipo,  # "verificacion", "correccion", "error", "info"
            "detalle": detalle,
            "datos": datos or {}
        }
        self.registros.append(registro)

    def guardar(self):
        """Guarda la auditoria como JSON."""
        resultado = {
            "inicio": self.inicio.isoformat(),
            "fin": datetime.now().isoformat(),
            "total_registros": len(self.registros),
            "registros": self.registros
        }
        with open(self.ruta, "w", encoding="utf-8") as f:
            json.dump(resultado, f, ensure_ascii=False, indent=2)

    def resumen(self) -> dict:
        """Devuelve resumen de la auditoria."""
        por_tipo = {}
        for r in self.registros:
            por_tipo[r["tipo"]] = por_tipo.get(r["tipo"], 0) + 1
        return {
            "total": len(self.registros),
            "por_tipo": por_tipo,
            "errores": [r for r in self.registros if r["tipo"] == "error"]
        }
