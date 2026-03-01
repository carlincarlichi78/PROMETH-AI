"""Utilidades de seguridad para manejo de archivos."""
import re
import os

_CARACTERES_PELIGROSOS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_LONGITUD_MAX = 200


def sanitizar_nombre_archivo(nombre: str) -> str:
    """Sanitiza un nombre de archivo para evitar path traversal y caracteres invalidos."""
    if not nombre or not nombre.strip():
        return "adjunto"
    # Extraer solo el nombre base (elimina cualquier componente de ruta)
    nombre = os.path.basename(nombre.replace("\\", "/"))
    # Eliminar caracteres peligrosos
    nombre = _CARACTERES_PELIGROSOS.sub("_", nombre)
    # Eliminar puntos al inicio (archivos ocultos / path traversal residual)
    nombre = nombre.lstrip(".")
    # Si quedo vacio tras la limpieza
    if not nombre or not nombre.strip("_"):
        return "adjunto"
    # Limitar longitud preservando extension
    if len(nombre) > _LONGITUD_MAX:
        partes = nombre.rsplit(".", 1)
        if len(partes) == 2:
            ext = partes[1][:10]
            base = partes[0][: _LONGITUD_MAX - len(ext) - 1]
            nombre = f"{base}.{ext}"
        else:
            nombre = nombre[:_LONGITUD_MAX]
    return nombre
