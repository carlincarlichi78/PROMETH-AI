"""Cache OCR reutilizable para el pipeline SFCE.

Permite reutilizar resultados OCR de ejecuciones anteriores evitando
llamadas costosas a APIs externas (Mistral, GPT, Gemini) cuando el PDF
no ha cambiado desde el ultimo procesamiento.

Mecanismo: junto a cada PDF se guarda un archivo .ocr.json con:
- hash SHA256 del PDF (para detectar cambios)
- timestamp de cuando se genero el cache
- motor y tier OCR usados
- datos OCR extraidos

Si el hash del PDF actual coincide con el del cache, se reutilizan los datos.
Si difiere, el cache se considera invalido y se ignora.
"""
import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("sfce.cache_ocr")

# Extension del archivo de cache
EXTENSION_CACHE = ".ocr.json"

# Tamano del bloque para leer archivos grandes (4 MB)
BLOQUE_LECTURA = 4 * 1024 * 1024


def calcular_hash_archivo(ruta_pdf: str) -> str:
    """Calcula el hash SHA256 del contenido de un archivo PDF.

    Lee el archivo en bloques para manejar PDFs grandes sin saturar memoria.

    Args:
        ruta_pdf: Ruta absoluta al archivo PDF.

    Returns:
        Hash SHA256 en formato hexadecimal (64 caracteres).

    Raises:
        FileNotFoundError: Si el archivo no existe.
    """
    ruta = Path(ruta_pdf)
    if not ruta.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {ruta_pdf}")

    hasher = hashlib.sha256()
    with ruta.open("rb") as f:
        while bloque := f.read(BLOQUE_LECTURA):
            hasher.update(bloque)

    return hasher.hexdigest()


def _ruta_cache(ruta_pdf: str) -> Path:
    """Calcula la ruta del archivo .ocr.json para un PDF dado.

    El archivo cache se coloca junto al PDF, con la misma base de nombre
    pero extension .ocr.json (ej: factura.pdf -> factura.ocr.json).

    Args:
        ruta_pdf: Ruta al archivo PDF.

    Returns:
        Ruta al archivo de cache correspondiente.
    """
    ruta = Path(ruta_pdf)
    return ruta.parent / (ruta.stem + EXTENSION_CACHE)


def obtener_cache_ocr(ruta_pdf: str) -> dict | None:
    """Busca y valida el cache OCR para un PDF.

    Verifica que:
    1. Existe el archivo .ocr.json junto al PDF.
    2. El hash SHA256 del PDF actual coincide con el guardado en cache.

    Si ambas condiciones se cumplen, retorna los datos OCR cacheados.
    En cualquier otro caso (no existe, hash difiere, JSON corrupto), retorna None.

    Args:
        ruta_pdf: Ruta al archivo PDF a consultar.

    Returns:
        Dict con los datos OCR si el cache es valido, None en caso contrario.
    """
    ruta = _ruta_cache(ruta_pdf)

    if not ruta.exists():
        logger.debug("Cache miss (no existe): %s", ruta_pdf)
        return None

    try:
        contenido = json.loads(ruta.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Cache corrupto para %s: %s", ruta_pdf, exc)
        return None

    hash_guardado = contenido.get("hash_sha256")
    if not hash_guardado:
        logger.warning("Cache sin campo hash_sha256: %s", ruta)
        return None

    try:
        hash_actual = calcular_hash_archivo(ruta_pdf)
    except FileNotFoundError:
        logger.warning("PDF no encontrado al validar cache: %s", ruta_pdf)
        return None

    if hash_actual != hash_guardado:
        logger.debug("Cache invalido (hash difiere): %s", ruta_pdf)
        return None

    logger.debug("Cache hit: %s", ruta_pdf)
    return contenido.get("datos")


def guardar_cache_ocr(ruta_pdf: str, datos_ocr: dict) -> str:
    """Guarda los datos OCR en cache junto al PDF.

    Calcula el hash actual del PDF y lo incluye en el cache para
    permitir validacion futura. Si ya existe un cache, lo sobrescribe.

    El JSON guardado tiene el formato:
    {
        "hash_sha256": "<sha256 del PDF>",
        "timestamp": "<ISO 8601>",
        "motor_ocr": "<motor usado>",
        "tier_ocr": <tier numerico>,
        "datos": { <datos OCR completos> }
    }

    Args:
        ruta_pdf: Ruta al archivo PDF procesado.
        datos_ocr: Diccionario con todos los datos extraidos por el OCR.

    Returns:
        Ruta del archivo .ocr.json creado.
    """
    hash_pdf = calcular_hash_archivo(ruta_pdf)

    envelope = {
        "hash_sha256": hash_pdf,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "motor_ocr": datos_ocr.get("motor_ocr", "desconocido"),
        "tier_ocr": datos_ocr.get("tier_ocr", 0),
        "datos": datos_ocr,
    }

    ruta = _ruta_cache(ruta_pdf)
    ruta.write_text(
        json.dumps(envelope, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    logger.debug("Cache guardado: %s", ruta)
    return str(ruta)


def invalidar_cache_ocr(ruta_pdf: str) -> bool:
    """Elimina el cache OCR de un PDF si existe.

    Util cuando se sabe que los datos cacheados ya no son validos
    (por ejemplo, tras corregir manualmente un error de OCR).

    Args:
        ruta_pdf: Ruta al archivo PDF cuyo cache se quiere eliminar.

    Returns:
        True si se elimino el cache, False si no existia.
    """
    ruta = _ruta_cache(ruta_pdf)

    if not ruta.exists():
        return False

    ruta.unlink()
    logger.debug("Cache invalidado: %s", ruta_pdf)
    return True


def estadisticas_cache(ruta_directorio: str) -> dict:
    """Analiza el estado del cache OCR en un directorio.

    Recorre todos los archivos .pdf del directorio (no recursivo) y
    clasifica cada uno como hit, miss o invalido:
    - **hit**: tiene cache .ocr.json con hash SHA256 que coincide con el PDF.
    - **miss**: no tiene archivo .ocr.json.
    - **invalido**: tiene .ocr.json pero el hash no coincide (PDF modificado
      desde que se genero el cache, o JSON corrupto).

    Args:
        ruta_directorio: Ruta al directorio a analizar.

    Returns:
        Dict con campos: total_pdfs, hits, misses, invalidos, ratio_hits.

    Raises:
        FileNotFoundError: Si el directorio no existe.
    """
    directorio = Path(ruta_directorio)
    if not directorio.exists():
        raise FileNotFoundError(f"Directorio no encontrado: {ruta_directorio}")

    total = 0
    hits = 0
    misses = 0
    invalidos = 0

    for pdf in directorio.glob("*.pdf"):
        total += 1
        ruta_json = _ruta_cache(str(pdf))

        if not ruta_json.exists():
            misses += 1
            continue

        # Intentar leer y validar el cache
        try:
            contenido = json.loads(ruta_json.read_text(encoding="utf-8"))
            hash_guardado = contenido.get("hash_sha256")
            if not hash_guardado:
                invalidos += 1
                continue
            hash_actual = calcular_hash_archivo(str(pdf))
            if hash_actual == hash_guardado:
                hits += 1
            else:
                invalidos += 1
        except (json.JSONDecodeError, OSError, FileNotFoundError):
            invalidos += 1

    ratio = hits / total if total > 0 else 0.0

    return {
        "total_pdfs": total,
        "hits": hits,
        "misses": misses,
        "invalidos": invalidos,
        "ratio_hits": ratio,
    }
