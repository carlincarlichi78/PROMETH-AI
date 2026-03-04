"""Endpoint unificado de ingesta — Gate 0."""
import logging
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile

from sfce.api.app import get_sesion_factory
from sfce.api.auth import obtener_usuario_actual
from sfce.core.gate0 import (
    TrustLevel, calcular_trust_level, ejecutar_preflight,
    calcular_score, decidir_destino, Decision, ErrorPreflight,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/gate0", tags=["gate0"])

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


def _inbox_empresa(empresa_id: int, sesion) -> Path:
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


@router.post("/ingestar", status_code=202)
async def ingestar_documento(
    request: Request,
    archivo: UploadFile = File(...),
    empresa_id: int = Form(...),
    emisor_cif: str = Form(default=""),
    sesion_factory=Depends(get_sesion_factory),
):
    """Punto de entrada unificado para todos los documentos."""
    usuario = obtener_usuario_actual(request)

    DIRECTORIO_DOCS.mkdir(parents=True, exist_ok=True)
    tmp_ruta = DIRECTORIO_DOCS / f"tmp_{archivo.filename}"
    contenido = await archivo.read()
    tmp_ruta.write_bytes(contenido)

    try:
        with sesion_factory() as sesion:
            # Preflight: validacion + deduplicacion
            try:
                preflight = ejecutar_preflight(
                    str(tmp_ruta), empresa_id, sesion, archivo.filename or ""
                )
            except ErrorPreflight as e:
                tmp_ruta.unlink(missing_ok=True)
                raise HTTPException(status_code=422, detail=str(e))

            if preflight.duplicado:
                tmp_ruta.unlink(missing_ok=True)
                raise HTTPException(status_code=409, detail="Documento duplicado (SHA256 ya procesado)")

            # Mover a directorio final (clientes/{slug}/inbox/ si hay slug)
            dir_final = _inbox_empresa(empresa_id, sesion)
            dir_final.mkdir(parents=True, exist_ok=True)
            ruta_final = dir_final / preflight.nombre_sanitizado
            tmp_ruta.replace(ruta_final)  # replace() sobrescribe si ya existe (Windows safe)

            # Trust level segun rol del usuario
            trust = calcular_trust_level(fuente="portal", rol=getattr(usuario, "rol", ""))

            # Aplicar Supplier Rule si existe y es auto_aplicable
            campos_prefill: dict = {}
            supplier_rule_aplicada = False
            if emisor_cif:
                try:
                    from sfce.core.supplier_rules import buscar_regla_aplicable, aplicar_regla
                    regla = buscar_regla_aplicable(sesion=sesion, emisor_cif=emisor_cif, empresa_id=empresa_id)
                    if regla and regla.auto_aplicable:
                        aplicar_regla(regla, campos_prefill)
                        supplier_rule_aplicada = True
                except Exception:
                    logger.warning("Error al aplicar Supplier Rule para CIF=%s", emisor_cif)

            # Score inicial conservador (sin OCR todavia)
            score = calcular_score(
                confianza_ocr=0.0,
                trust_level=trust,
                supplier_rule_aplicada=supplier_rule_aplicada,
                checks_pasados=1,
                checks_totales=5,
            )
            decision = decidir_destino(score, trust)

            # Insertar en cola
            import json
            from sfce.db.modelos import ColaProcesamiento
            item = ColaProcesamiento(
                empresa_id=empresa_id,
                nombre_archivo=preflight.nombre_sanitizado,
                ruta_archivo=str(ruta_final),
                estado="PENDIENTE",
                trust_level=trust.value,
                score_final=score,
                decision=decision.value,
                sha256=preflight.sha256,
                hints_json=json.dumps(campos_prefill) if campos_prefill else "{}",
            )
            sesion.add(item)
            sesion.commit()
            sesion.refresh(item)

            logger.info("Documento encolado: %s, score=%.0f, decision=%s, regla=%s",
                        preflight.nombre_sanitizado, score, decision.value, supplier_rule_aplicada)
            # Emitir evento WS para actualizar dashboard en tiempo real
            try:
                from sfce.api.websocket import gestor_ws, EVENTO_WATCHER_NUEVO_PDF
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(gestor_ws.emitir_a_empresa(empresa_id, EVENTO_WATCHER_NUEVO_PDF, {
                        "empresa_id": empresa_id,
                        "nombre_archivo": preflight.nombre_sanitizado,
                        "fuente": "manual",
                    }))
            except Exception:
                pass
            return {
                "cola_id": item.id,
                "nombre": preflight.nombre_sanitizado,
                "sha256": preflight.sha256,
                "trust_level": trust.value,
                "score_inicial": score,
                "estado": decision.value,
                "supplier_rule_aplicada": supplier_rule_aplicada,
                "campos_prefill": campos_prefill,
            }
    except HTTPException:
        raise
    except Exception as exc:
        tmp_ruta.unlink(missing_ok=True)
        logger.error("Error en Gate 0: %s", exc)
        raise HTTPException(status_code=500, detail="Error interno en Gate 0")


@router.post("/ingestar-zip", status_code=202)
async def ingestar_zip(
    archivo: UploadFile = File(...),
    empresa_id: int = Form(...),
    sesion_factory=Depends(get_sesion_factory),
    usuario=Depends(obtener_usuario_actual),
):
    """Ingesta masiva: ZIP con múltiples facturas PDF.

    Extrae todos los PDFs del ZIP, valida cada uno y los encola en Gate 0
    con trust_level ALTA (upload manual por gestor).
    """
    from sfce.core.procesador_zip import extraer_pdfs_zip
    from sqlalchemy.orm import Session

    MAX_ZIP = 500 * 1024 * 1024
    contenido = await archivo.read()
    if len(contenido) > MAX_ZIP:
        raise HTTPException(status_code=413, detail="ZIP demasiado grande (máx 500 MB)")

    with Session(sesion_factory()) as sesion:
        dir_destino = _inbox_empresa(empresa_id, sesion)
        resultado = extraer_pdfs_zip(contenido, empresa_id, dir_destino, sesion)

    return {
        "encolados": resultado.encolados,
        "rechazados": resultado.rechazados,
        "errores": resultado.errores[:10],
    }


@router.get("/worker/estado")
async def estado_worker(
    request: Request,
    sesion_factory=Depends(get_sesion_factory),
    _usuario=Depends(obtener_usuario_actual),
):
    """Estado del worker OCR en background."""
    from sfce.db.modelos import ColaProcesamiento
    from sqlalchemy.orm import Session

    task = getattr(request.app.state, "worker_ocr_task", None)
    activo = task is not None and not task.done()

    with sesion_factory() as sesion:
        pendientes = (
            sesion.query(ColaProcesamiento)
            .filter(ColaProcesamiento.estado == "PENDIENTE")
            .count()
        )
        procesados_hoy = (
            sesion.query(ColaProcesamiento)
            .filter(
                ColaProcesamiento.estado == "PROCESADO",
                ColaProcesamiento.updated_at >= date.today(),
            )
            .count()
        )

    return {
        "activo": activo,
        "pendientes": pendientes,
        "procesados_hoy": procesados_hoy,
    }
