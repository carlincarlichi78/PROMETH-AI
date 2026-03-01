"""Endpoint unificado de ingesta — Gate 0."""
import logging
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


@router.post("/ingestar", status_code=202)
async def ingestar_documento(
    request: Request,
    archivo: UploadFile = File(...),
    empresa_id: int = Form(...),
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

            # Mover a directorio final
            dir_final = DIRECTORIO_DOCS / str(empresa_id) / "inbox"
            dir_final.mkdir(parents=True, exist_ok=True)
            ruta_final = dir_final / preflight.nombre_sanitizado
            tmp_ruta.replace(ruta_final)  # replace() sobrescribe si ya existe (Windows safe)

            # Trust level segun rol del usuario
            trust = calcular_trust_level(fuente="portal", rol=getattr(usuario, "rol", ""))

            # Score inicial conservador (sin OCR todavia)
            score = calcular_score(
                confianza_ocr=0.0,
                trust_level=trust,
                supplier_rule_aplicada=False,
                checks_pasados=1,
                checks_totales=5,
            )
            decision = decidir_destino(score, trust)

            # Insertar en cola
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
            )
            sesion.add(item)
            sesion.commit()
            sesion.refresh(item)

            logger.info("Documento encolado: %s, score=%.0f, decision=%s",
                        preflight.nombre_sanitizado, score, decision.value)
            return {
                "cola_id": item.id,
                "nombre": preflight.nombre_sanitizado,
                "sha256": preflight.sha256,
                "trust_level": trust.value,
                "score_inicial": score,
                "estado": decision.value,
            }
    except HTTPException:
        raise
    except Exception as exc:
        tmp_ruta.unlink(missing_ok=True)
        logger.error("Error en Gate 0: %s", exc)
        raise HTTPException(status_code=500, detail="Error interno en Gate 0")
