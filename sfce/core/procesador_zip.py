"""Procesador de ZIPs con múltiples facturas PDF.

Extrae PDFs del ZIP, valida cada uno con validador_pdf, y los encola
en cola_procesamiento con trust_level ALTA (upload manual por gestor).
"""
import hashlib
import io
import logging
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from sfce.core.seguridad_archivos import sanitizar_nombre_archivo
from sfce.core.validador_pdf import validar_pdf, ErrorValidacionPDF

logger = logging.getLogger(__name__)

MAX_ARCHIVOS_ZIP = 500
MAX_BYTES_TOTAL = 500 * 1024 * 1024  # 500 MB total descomprimido


@dataclass
class ResultadoZIP:
    encolados: int = 0
    rechazados: int = 0
    errores: list[str] = field(default_factory=list)
    archivos_procesados: list[dict] = field(default_factory=list)


def extraer_pdfs_zip(
    contenido_zip: bytes,
    empresa_id: int,
    directorio_destino: Path,
    sesion,
) -> ResultadoZIP:
    """Extrae PDFs de un ZIP y los encola en cola_procesamiento.

    Args:
        contenido_zip: bytes del archivo ZIP
        empresa_id: ID de la empresa destino
        directorio_destino: carpeta donde guardar los PDFs extraídos
        sesion: sesión SQLAlchemy activa

    Returns:
        ResultadoZIP con contadores y lista de errores
    """
    import json
    from sfce.db.modelos import ColaProcesamiento

    resultado = ResultadoZIP()

    try:
        zf = zipfile.ZipFile(io.BytesIO(contenido_zip))
    except zipfile.BadZipFile:
        resultado.errores.append("Archivo ZIP corrupto o inválido")
        return resultado

    # Solo PDFs, excluir metadatos macOS
    pdfs = [
        info for info in zf.infolist()
        if info.filename.lower().endswith(".pdf")
        and not info.filename.startswith("__MACOSX")
        and not Path(info.filename).name.startswith(".")
    ]

    if len(pdfs) > MAX_ARCHIVOS_ZIP:
        resultado.errores.append(
            f"ZIP con {len(pdfs)} archivos excede el máximo de {MAX_ARCHIVOS_ZIP}"
        )
        return resultado

    total_bytes = 0
    for info in pdfs:
        contenido = zf.read(info.filename)
        total_bytes += len(contenido)

        if total_bytes > MAX_BYTES_TOTAL:
            resultado.errores.append("Tamaño total descomprimido excede 500 MB")
            break

        nombre = sanitizar_nombre_archivo(Path(info.filename).name)

        try:
            validar_pdf(contenido, nombre)
        except ErrorValidacionPDF as e:
            logger.warning("ZIP: PDF rechazado '%s' — %s", nombre, e)
            resultado.rechazados += 1
            resultado.errores.append(f"{nombre}: {e}")
            continue

        sha = hashlib.sha256(contenido).hexdigest()
        directorio_destino.mkdir(parents=True, exist_ok=True)
        ruta = directorio_destino / nombre
        ruta.write_bytes(contenido)

        item = ColaProcesamiento(
            empresa_id=empresa_id,
            nombre_archivo=nombre,
            ruta_archivo=str(ruta),
            estado="PENDIENTE",
            trust_level="ALTA",  # Upload manual por gestor = confianza alta
            sha256=sha,
            hints_json=json.dumps({"origen": "zip_masivo"}),
        )
        sesion.add(item)
        resultado.encolados += 1
        resultado.archivos_procesados.append({"nombre": nombre, "sha256": sha})

    sesion.commit()
    logger.info(
        "ZIP empresa %d: %d encolados, %d rechazados",
        empresa_id, resultado.encolados, resultado.rechazados,
    )
    return resultado
