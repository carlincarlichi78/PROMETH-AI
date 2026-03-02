"""Worker que procesa emails del buzón catch-all prometh-ai.es.

Flujo:
  email_data → parsear destinatario → resolver empresa →
  extraer hints asunto → validar adjuntos PDF → guardar en disk → encolar Gate 0
"""
import hashlib
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from sfce.conectores.correo.canal_email_dedicado import (
    parsear_destinatario_dedicado,
    resolver_empresa_por_slug,
)
from sfce.conectores.correo.parser_hints import extraer_hints_asunto
from sfce.core.seguridad_archivos import sanitizar_nombre_archivo
from sfce.core.validador_pdf import validar_pdf, ErrorValidacionPDF
from sfce.db.modelos import ColaProcesamiento

if TYPE_CHECKING:
    from sfce.conectores.correo.extractor_adjuntos import ArchivoExtraido

logger = logging.getLogger(__name__)
DIRECTORIO_DOCS = Path("docs")


def _encolar_archivo(
    archivo: "ArchivoExtraido",
    empresa_id: int,
    email_id: int | None,
    email_data: dict,
    directorio: Path,
    sesion: Session,
) -> bool:
    """Encola un ArchivoExtraido en ColaProcesamiento.

    Valida PDFs, calcula SHA256, guarda en disco y crea la entrada en cola.

    Returns:
        True si el archivo fue encolado, False si fue rechazado.
    """
    nombre = sanitizar_nombre_archivo(archivo.nombre)
    contenido = archivo.contenido

    if archivo.extension == "pdf":
        try:
            validar_pdf(contenido, nombre)
        except ErrorValidacionPDF as e:
            logger.warning("Adjunto rechazado '%s': %s", nombre, e)
            return False

    sha = hashlib.sha256(contenido).hexdigest()

    dir_empresa = Path(directorio) / str(empresa_id) / "inbox"
    dir_empresa.mkdir(parents=True, exist_ok=True)
    ruta = dir_empresa / nombre
    ruta.write_bytes(contenido)

    hints = extraer_hints_asunto(email_data.get("asunto", ""))

    item = ColaProcesamiento(
        empresa_id=empresa_id,
        nombre_archivo=nombre,
        ruta_archivo=str(ruta),
        estado="PENDIENTE",
        trust_level="BAJA",
        sha256=sha,
        empresa_origen_correo_id=empresa_id,
        hints_json=json.dumps({
            "tipo_doc": hints.tipo_doc,
            "nota": hints.nota,
            "from": email_data.get("remitente", email_data.get("from", "")),
            "origen": "email_ingesta",
            "email_id": email_id,
        }),
    )
    sesion.add(item)
    sesion.flush()
    logger.info("Encolado '%s' para empresa %d", nombre, empresa_id)
    return True


def procesar_email_catchall(email_data: dict, sesion: Session) -> dict:
    """Procesa un email del catch-all y encola los adjuntos PDF válidos.

    Args:
        email_data: dict con claves 'to', 'from', 'subject', 'adjuntos'
                    Cada adjunto: {'nombre': str, 'contenido': bytes}
        sesion: sesión SQLAlchemy activa

    Returns:
        dict con 'encolados', 'empresa_id' (si resolvió) y 'motivo' (si no resolvió)
    """
    destinatario = email_data.get("to", "")
    dest_parsed = parsear_destinatario_dedicado(destinatario)

    if not dest_parsed:
        return {"encolados": 0, "motivo": "dominio_no_dedicado"}

    empresa_id = resolver_empresa_por_slug(dest_parsed.slug, sesion)
    if not empresa_id:
        logger.warning("Catch-all: slug '%s' no resuelve a ninguna empresa", dest_parsed.slug)
        return {"encolados": 0, "motivo": "slug_desconocido"}

    hints = extraer_hints_asunto(email_data.get("subject", ""))
    # Tipo explícito en subdirección (+compras) tiene precedencia sobre hints del asunto
    if dest_parsed.tipo_doc and not hints.tipo_doc:
        hints.tipo_doc = dest_parsed.tipo_doc

    encolados = 0
    rechazados = 0
    for adjunto in email_data.get("adjuntos", []):
        nombre = sanitizar_nombre_archivo(adjunto.get("nombre", ""))
        contenido = adjunto.get("contenido", b"")

        if not nombre.lower().endswith(".pdf"):
            continue

        try:
            validar_pdf(contenido, nombre)
        except ErrorValidacionPDF as e:
            logger.warning("Catch-all: adjunto rechazado '%s' — %s", nombre, e)
            rechazados += 1
            continue

        sha = hashlib.sha256(contenido).hexdigest()

        dir_empresa = DIRECTORIO_DOCS / str(empresa_id) / "inbox"
        dir_empresa.mkdir(parents=True, exist_ok=True)
        ruta = dir_empresa / nombre
        ruta.write_bytes(contenido)

        item = ColaProcesamiento(
            empresa_id=empresa_id,
            nombre_archivo=nombre,
            ruta_archivo=str(ruta),
            estado="PENDIENTE",
            trust_level="BAJA",  # Email externo = confianza baja
            sha256=sha,
            hints_json=json.dumps({
                "tipo_doc": hints.tipo_doc,
                "nota": hints.nota,
                "slug": dest_parsed.slug,
                "from": email_data.get("from", ""),
                "origen": "catchall_email",
            }),
        )
        sesion.add(item)
        encolados += 1

    sesion.commit()
    logger.info(
        "Catch-all: %d encolados, %d rechazados para empresa %d",
        encolados, rechazados, empresa_id,
    )
    return {"encolados": encolados, "rechazados": rechazados, "empresa_id": empresa_id}
