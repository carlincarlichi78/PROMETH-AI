"""Utilidades de seguridad para manejo de archivos."""
import re
import unicodedata


def sanitizar_nombre_archivo(nombre: str) -> str:
    """Elimina caracteres peligrosos y normaliza el nombre del archivo."""
    # Normalizar unicode
    nombre = unicodedata.normalize("NFKC", nombre)
    # Eliminar separadores de ruta (path traversal)
    nombre = nombre.replace("/", "_").replace("\\", "_")
    # Conservar solo chars seguros: alfanumericos, guion, guion_bajo, punto
    nombre = re.sub(r"[^\w.\-]", "_", nombre)
    # Colapsar underscores multiples
    nombre = re.sub(r"_+", "_", nombre)
    # Quitar puntos al inicio (archivos ocultos)
    nombre = nombre.lstrip(".")
    return nombre or "archivo"
