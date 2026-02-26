"""Catalogo evolutivo de errores conocidos."""
import yaml
from pathlib import Path
from datetime import datetime
from typing import Optional
from .logger import crear_logger

logger = crear_logger("errors")


class CatalogoErrores:
    """Gestiona el catalogo de errores conocidos (YAML)."""

    def __init__(self, ruta_yaml: Path):
        self.ruta = ruta_yaml
        self.errores = []
        self._cargar()

    def _cargar(self):
        """Carga errores desde YAML."""
        if self.ruta.exists():
            with open(self.ruta, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            self.errores = data.get("errores", [])
        else:
            self.errores = []

    def guardar(self):
        """Guarda catalogo actualizado."""
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        data = {"errores": self.errores, "actualizado": datetime.now().isoformat()}
        with open(self.ruta, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    def buscar(self, tipo: str, condicion_extra: dict = None) -> Optional[dict]:
        """Busca un error conocido por tipo."""
        for error in self.errores:
            if error.get("tipo") == tipo:
                if condicion_extra:
                    deteccion = error.get("deteccion", {})
                    if all(deteccion.get(k) == v for k, v in condicion_extra.items()):
                        return error
                else:
                    return error
        return None

    def registrar_ocurrencia(self, error_id: str):
        """Incrementa contador de ocurrencias de un error."""
        for error in self.errores:
            if error.get("id") == error_id:
                error["ocurrencias"] = error.get("ocurrencias", 0) + 1
                error["ultima_ocurrencia"] = datetime.now().isoformat()
                self.guardar()
                return

    def agregar_error(self, tipo: str, descripcion: str, deteccion: dict,
                      correccion: dict = None, cliente: str = "todos") -> str:
        """Agrega un nuevo error al catalogo.

        Returns:
            ID del error creado
        """
        nuevo_id = f"ERR{len(self.errores) + 1:03d}"
        nuevo = {
            "id": nuevo_id,
            "descubierto": datetime.now().strftime("%Y-%m-%d"),
            "cliente": cliente,
            "tipo": tipo,
            "descripcion": descripcion,
            "deteccion": deteccion,
            "correccion": correccion or {"automatica": False},
            "aplicable_a": cliente,
            "ocurrencias": 1,
            "ultima_ocurrencia": datetime.now().isoformat()
        }
        self.errores.append(nuevo)
        self.guardar()
        logger.info(f"Nuevo error registrado: {nuevo_id} - {descripcion}")
        return nuevo_id

    def es_auto_corregible(self, error_id: str) -> bool:
        """Verifica si un error tiene correccion automatica."""
        for error in self.errores:
            if error.get("id") == error_id:
                return error.get("correccion", {}).get("automatica", False)
        return False


class ResultadoFase:
    """Resultado de ejecutar una fase del pipeline."""

    def __init__(self, fase: str):
        self.fase = fase
        self.exitoso = True
        self.errores = []      # Errores bloqueantes
        self.avisos = []       # Avisos no bloqueantes
        self.correcciones = [] # Correcciones auto-aplicadas
        self.datos = {}        # Datos de salida de la fase

    def error(self, mensaje: str, datos: dict = None):
        """Registra error bloqueante."""
        self.exitoso = False
        self.errores.append({"mensaje": mensaje, "datos": datos or {}})

    def aviso(self, mensaje: str, datos: dict = None):
        """Registra aviso no bloqueante."""
        self.avisos.append({"mensaje": mensaje, "datos": datos or {}})

    def correccion(self, mensaje: str, datos: dict = None):
        """Registra correccion auto-aplicada."""
        self.correcciones.append({"mensaje": mensaje, "datos": datos or {}})

    def resumen(self) -> str:
        """Resumen legible del resultado."""
        estado = "OK" if self.exitoso else "FALLO"
        partes = [f"[{estado}] Fase {self.fase}"]
        if self.errores:
            partes.append(f"  {len(self.errores)} errores")
        if self.correcciones:
            partes.append(f"  {len(self.correcciones)} correcciones auto-aplicadas")
        if self.avisos:
            partes.append(f"  {len(self.avisos)} avisos")
        return " | ".join(partes)
