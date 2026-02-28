"""Convencion de nombres para carpetas y documentos — Task 38 Fase E.

Funciones utilitarias para generar nombres normalizados y mover documentos
dentro del flujo SFCE.
"""
import logging
import re
import shutil
import unicodedata
from pathlib import Path

logger = logging.getLogger("sfce.nombres")

# Mapa de formatos de fecha soportados (mas comunes primero)
_PATRONES_FECHA = [
    # YYYY-MM-DD o YYYY/MM/DD
    (re.compile(r"^(\d{4})[-/](\d{2})[-/](\d{2})$"), lambda m: f"{m.group(1)}{m.group(2)}{m.group(3)}"),
    # DD-MM-YYYY o DD/MM/YYYY
    (re.compile(r"^(\d{2})[-/](\d{2})[-/](\d{4})$"), lambda m: f"{m.group(3)}{m.group(2)}{m.group(1)}"),
    # DDMMYYYY (sin separador)
    (re.compile(r"^(\d{2})(\d{2})(\d{4})$"), lambda m: f"{m.group(3)}{m.group(2)}{m.group(1)}"),
    # YYYYMMDD ya normalizado
    (re.compile(r"^(\d{8})$"), lambda m: m.group(0)),
]


def _a_ascii(texto: str) -> str:
    """Convierte texto a ASCII eliminando diacriticos (acentos, tilde, etc.)."""
    normalizado = unicodedata.normalize("NFD", texto)
    solo_ascii = normalizado.encode("ascii", "ignore").decode("ascii")
    return solo_ascii


def _slug(texto: str, max_chars: int = None) -> str:
    """Convierte texto a slug: minusculas, solo alfanumericos y guiones, sin duplicados."""
    texto = _a_ascii(texto)
    texto = texto.lower()
    # Reemplazar puntos tras letras para suprimir ".L." en "S.L." etc.
    texto = re.sub(r"\.(?=[a-z])", "", texto)
    # Eliminar puntos sobrantes al final
    texto = texto.rstrip(".")
    # Reemplazar cualquier caracter no alfanumerico por guion
    texto = re.sub(r"[^a-z0-9]+", "-", texto)
    # Eliminar guiones duplicados
    texto = re.sub(r"-{2,}", "-", texto)
    # Eliminar guiones al inicio y al final
    texto = texto.strip("-")
    if max_chars:
        texto = texto[:max_chars].rstrip("-")
    return texto


def _normalizar_fecha(fecha: str) -> str:
    """Convierte fecha en varios formatos a YYYYMMDD.

    Retorna "SIN-FECHA" si no puede parsear.
    """
    if not fecha:
        return "SIN-FECHA"
    fecha = fecha.strip()
    for patron, formateador in _PATRONES_FECHA:
        coincidencia = patron.match(fecha)
        if coincidencia:
            return formateador(coincidencia)
    logger.warning("Formato de fecha no reconocido: %s", fecha)
    return "SIN-FECHA"


def _limpiar_numero(numero: str) -> str:
    """Elimina caracteres especiales de numeros de factura, deja alfanumericos."""
    if not numero:
        return "SIN-NUM"
    return re.sub(r"[^A-Z0-9]", "", numero.upper())


def generar_slug_cliente(cif: str, nombre: str) -> str:
    """Genera slug normalizado para carpetas de clientes.

    Args:
        cif: CIF/NIF del cliente (se convierte a mayusculas).
        nombre: Nombre o razon social del cliente.

    Returns:
        Slug con formato "{CIF}_{nombre-slug}".
        Ejemplo: "B12345678_pastorino-costa-del-sol"
    """
    cif_normalizado = cif.strip().upper()
    nombre_slug = _slug(nombre.strip())
    return f"{cif_normalizado}_{nombre_slug}"


def renombrar_documento(datos_ocr: dict, tipo_doc: str, fecha: str = None) -> str:
    """Genera nombre estandarizado para documentos procesados.

    Formato: {TIPO}_{EMISOR}_{FECHA}_{NUMERO}.pdf

    Args:
        datos_ocr: Diccionario con datos extraidos por OCR.
        tipo_doc: Codigo del tipo de documento (FC, FV, NC, NOM, SUM, BAN...).
        fecha: Fecha en cualquier formato soportado. Si None, se toma de datos_ocr.

    Returns:
        Nombre de archivo normalizado.
        Ejemplo: "FC_CARGAEXPRESS_20250115_F2025001.pdf"
    """
    tipo = tipo_doc.upper().strip()

    # Emisor: probar distintos campos
    emisor_raw = (
        datos_ocr.get("emisor_nombre")
        or datos_ocr.get("nombre_emisor")
        or "DESCONOCIDO"
    )
    emisor = _slug(emisor_raw, max_chars=20).upper()

    # Fecha: parametro tiene prioridad sobre datos_ocr
    fecha_raw = fecha or datos_ocr.get("fecha")
    fecha_norm = _normalizar_fecha(fecha_raw)

    # Numero: probar distintos campos
    numero_raw = datos_ocr.get("numero_factura") or datos_ocr.get("numero")
    numero = _limpiar_numero(numero_raw)

    return f"{tipo}_{emisor}_{fecha_norm}_{numero}.pdf"


def carpeta_sin_clasificar(ruta_base: str) -> str:
    """Retorna ruta a `_sin_clasificar/` dentro de ruta_base, creandola si no existe.

    Args:
        ruta_base: Ruta base de la carpeta del cliente o proyecto.

    Returns:
        Ruta absoluta a la carpeta `_sin_clasificar/`.
    """
    ruta = Path(ruta_base) / "_sin_clasificar"
    ruta.mkdir(parents=True, exist_ok=True)
    logger.debug("Carpeta sin clasificar asegurada: %s", ruta)
    return str(ruta)


def mover_documento(
    ruta_actual: str,
    ruta_destino: str,
    crear_directorios: bool = True,
) -> str:
    """Mueve un archivo a la ruta de destino.

    Args:
        ruta_actual: Ruta absoluta del archivo origen.
        ruta_destino: Ruta absoluta del archivo destino.
        crear_directorios: Si True, crea directorios intermedios necesarios.

    Returns:
        Ruta absoluta del archivo en su nueva ubicacion.

    Raises:
        FileNotFoundError: Si el archivo origen no existe.
        FileNotFoundError: Si el directorio destino no existe y crear_directorios=False.
    """
    origen = Path(ruta_actual)
    destino = Path(ruta_destino)

    if not origen.exists():
        raise FileNotFoundError(f"Archivo origen no encontrado: {ruta_actual}")

    if crear_directorios:
        destino.parent.mkdir(parents=True, exist_ok=True)
    elif not destino.parent.exists():
        raise FileNotFoundError(
            f"Directorio destino no existe: {destino.parent}"
        )

    shutil.move(str(origen), str(destino))
    logger.info("Documento movido: %s -> %s", ruta_actual, ruta_destino)
    return str(destino)
