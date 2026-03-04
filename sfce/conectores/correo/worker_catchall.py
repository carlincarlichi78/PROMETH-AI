"""Worker que procesa emails del buzón catch-all prometh-ai.es.

Flujo:
  email_data → parsear destinatario → resolver empresa →
  extraer hints asunto → validar adjuntos PDF → guardar en disk → encolar Gate 0
"""
import asyncio
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
from sfce.db.modelos import ColaProcesamiento, EmailProcesado

if TYPE_CHECKING:
    from sfce.conectores.correo.extractor_adjuntos import ArchivoExtraido

logger = logging.getLogger(__name__)
DIRECTORIO_DOCS = Path("docs")
RAIZ_CLIENTES = Path("clientes")


def _carpeta_slug(nombre: str) -> str:
    """Convierte nombre de empresa al slug de carpeta (misma lógica que onboarding.py)."""
    import re
    slug = nombre.lower().strip()
    for src, dst in [("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"), ("ñ", "n")]:
        slug = slug.replace(src, dst)
    slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
    return slug


def _inbox_empresa(empresa_id: int, sesion: Session) -> Path:
    """Resuelve el directorio inbox de una empresa.

    Prioridad:
    1. empresa.slug del DB (ya con guiones, ej: gerardo-gonzalez-callejon)
    2. slug derivado del nombre (fallback para empresas sin slug en DB)
    3. docs/{empresa_id}/inbox/ si ninguna carpeta existe en disco
    """
    from sfce.db.modelos import Empresa
    empresa = sesion.query(Empresa).filter(Empresa.id == empresa_id).first()
    if empresa:
        for candidato_slug in filter(None, [empresa.slug, _carpeta_slug(empresa.nombre or "")]):
            candidato = RAIZ_CLIENTES / candidato_slug
            if candidato.exists():
                return candidato / "inbox"
    return DIRECTORIO_DOCS / str(empresa_id) / "inbox"


def _emitir_ws_nuevo_pdf(empresa_id: int, nombre: str, fuente: str = "correo") -> None:
    """Emite evento WS watcher_nuevo_pdf desde contexto síncrono. No bloquea si falla."""
    try:
        from sfce.api.websocket import gestor_ws, EVENTO_WATCHER_NUEVO_PDF
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(gestor_ws.emitir_a_empresa(empresa_id, EVENTO_WATCHER_NUEVO_PDF, {
                "empresa_id": empresa_id,
                "nombre_archivo": nombre,
                "fuente": fuente,
            }))
    except Exception:
        pass


def _encolar_archivo(
    archivo: "ArchivoExtraido",
    empresa_id: int,
    email_id: int | None,
    email_data: dict,
    directorio: Path,
    sesion: Session,
    hints_extra: dict | None = None,
) -> bool:
    """Encola un ArchivoExtraido en ColaProcesamiento.

    Valida PDFs, calcula SHA256, guarda en disco y crea la entrada en cola.

    Args:
        hints_extra: campos de enriquecimiento adicionales (G7/G13).
                     Si se proporciona, se almacena en hints_json["enriquecimiento"].

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

    dir_empresa = _inbox_empresa(empresa_id, sesion)
    dir_empresa.mkdir(parents=True, exist_ok=True)
    ruta = dir_empresa / nombre
    ruta.write_bytes(contenido)

    hints = extraer_hints_asunto(email_data.get("asunto", ""))

    hints_dict: dict = {
        "tipo_doc": hints.tipo_doc,
        "nota": hints.nota,
        "from": email_data.get("remitente", email_data.get("from", "")),
        "origen": "email_ingesta",
        "email_id": email_id,
    }
    # G7/G13: integrar enriquecimiento si se ha extraído
    if hints_extra:
        hints_dict["enriquecimiento"] = hints_extra

    item = ColaProcesamiento(
        empresa_id=empresa_id,
        nombre_archivo=nombre,
        ruta_archivo=str(ruta),
        estado="PENDIENTE",
        trust_level="BAJA",
        sha256=sha,
        empresa_origen_correo_id=empresa_id,
        hints_json=json.dumps(hints_dict),
    )
    sesion.add(item)
    sesion.flush()
    logger.info("Encolado '%s' para empresa %d", nombre, empresa_id)
    _emitir_ws_nuevo_pdf(empresa_id, nombre, fuente="correo")
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
        logger.warning(
            "Catch-all: slug '%s' no resuelve a ninguna empresa, guardando en cuarentena",
            dest_parsed.slug,
        )
        ep = EmailProcesado(
            cuenta_id=None,
            uid_servidor=str(email_data.get("uid", "")),
            remitente=email_data.get("from", ""),
            asunto=email_data.get("subject", ""),
            estado="CUARENTENA",
            nivel_clasificacion="MANUAL",
        )
        sesion.add(ep)
        sesion.commit()
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

        dir_empresa = _inbox_empresa(empresa_id, sesion)
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
