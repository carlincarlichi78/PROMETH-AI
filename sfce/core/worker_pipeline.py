"""
Worker daemon de procesamiento de documentos por pipeline.
Complementa worker_ocr_gate0 (que hace OCR + scoring).
Este worker lanza el pipeline completo (7 fases) cuando toca según schedule.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

from sfce.core.pipeline_runner import (
    ejecutar_pipeline_empresa,
    adquirir_lock_empresa,
    liberar_lock_empresa,
)
from sfce.db.modelos import ColaProcesamiento, ConfigProcesamientoEmpresa

logger = logging.getLogger(__name__)

_INTERVALO_CICLO = 60  # segundos entre ciclos del worker


def obtener_empresas_con_docs_pendientes(sesion_factory) -> list[int]:
    """Retorna lista de empresa_ids con docs PENDIENTE o APROBADO en cola."""
    with sesion_factory() as s:
        rows = (
            s.query(ColaProcesamiento.empresa_id)
            .filter(ColaProcesamiento.estado.in_(["PENDIENTE", "APROBADO"]))
            .distinct()
            .all()
        )
    return [r[0] for r in rows]


def schedule_ok(empresa_id: int, sesion_factory) -> bool:
    """
    Retorna True si ha pasado suficiente tiempo desde el último pipeline.
    Si schedule_minutos es None, siempre retorna True (manual/inmediato).
    Si último_pipeline es None, siempre retorna True (nunca ejecutado).
    """
    with sesion_factory() as s:
        cfg = s.query(ConfigProcesamientoEmpresa).filter_by(empresa_id=empresa_id).first()

    if not cfg:
        return True  # Sin config → procesar siempre
    if cfg.schedule_minutos is None:
        return True  # Manual
    if cfg.ultimo_pipeline is None:
        return True  # Nunca ejecutado

    elapsed = datetime.utcnow() - cfg.ultimo_pipeline
    return elapsed >= timedelta(minutes=cfg.schedule_minutos)


def _docs_para_empresa(empresa_id: int, sesion_factory) -> list[int]:
    """Retorna IDs de Documento listos para el pipeline de una empresa."""
    with sesion_factory() as s:
        cfg = s.query(ConfigProcesamientoEmpresa).filter_by(empresa_id=empresa_id).first()
        modo = cfg.modo if cfg else "revision"
        estados_validos = ["PENDIENTE"] if modo == "auto" else ["APROBADO"]
        rows = (
            s.query(ColaProcesamiento.documento_id)
            .filter(
                ColaProcesamiento.empresa_id == empresa_id,
                ColaProcesamiento.estado.in_(estados_validos),
            )
            .all()
        )
    return [r[0] for r in rows if r[0]]


def _actualizar_ultimo_pipeline(empresa_id: int, sesion_factory) -> None:
    with sesion_factory() as s:
        cfg = s.query(ConfigProcesamientoEmpresa).filter_by(empresa_id=empresa_id).first()
        if cfg:
            cfg.ultimo_pipeline = datetime.utcnow()
            s.commit()


def _notificar_cuarentena_docs(empresa_id: int, sesion_factory) -> None:
    """Dispara notificaciones para docs en cuarentena según tipo de motivo."""
    try:
        from sfce.core.notificaciones import notificar_cuarentena
        from sfce.db.modelos import Documento
        with sesion_factory() as s:
            docs_cuarentena = (
                s.query(Documento)
                .filter(
                    Documento.empresa_id == empresa_id,
                    Documento.estado == "cuarentena",
                    Documento.motivo_cuarentena.isnot(None),
                )
                .all()
            )
            for doc in docs_cuarentena:
                notificar_cuarentena(
                    sesion=s,
                    empresa_id=empresa_id,
                    motivo=doc.motivo_cuarentena,
                    nombre_archivo=doc.ruta_pdf,
                    documento_id=doc.id,
                )
    except Exception as e:
        logger.warning(f"Error notificando cuarentena empresa {empresa_id}: {e}")


def ejecutar_ciclo_worker(sesion_factory) -> None:
    """Un ciclo completo del worker. Llamar periódicamente."""
    empresas = obtener_empresas_con_docs_pendientes(sesion_factory)

    for empresa_id in empresas:
        if not schedule_ok(empresa_id, sesion_factory):
            logger.debug(f"Empresa {empresa_id}: schedule no cumplido, omitiendo")
            continue

        if not adquirir_lock_empresa(empresa_id):
            logger.warning(f"Empresa {empresa_id}: pipeline ya en ejecución, omitiendo")
            continue

        try:
            doc_ids = _docs_para_empresa(empresa_id, sesion_factory)
            if not doc_ids:
                continue

            logger.info(f"Empresa {empresa_id}: lanzando pipeline para {len(doc_ids)} docs")
            resultado = ejecutar_pipeline_empresa(
                empresa_id=empresa_id,
                sesion_factory=sesion_factory,
                documentos_ids=doc_ids,
            )
            _actualizar_ultimo_pipeline(empresa_id, sesion_factory)
            logger.info(
                f"Empresa {empresa_id}: pipeline completado — "
                f"{resultado.docs_procesados} OK, {resultado.docs_cuarentena} cuarentena, "
                f"{resultado.docs_error} errores"
            )

            if resultado.docs_cuarentena > 0:
                _notificar_cuarentena_docs(empresa_id, sesion_factory)
        except Exception as e:
            logger.error(f"Empresa {empresa_id}: error en ciclo worker: {e}", exc_info=True)
        finally:
            liberar_lock_empresa(empresa_id)


async def loop_worker_pipeline(sesion_factory, intervalo: int = _INTERVALO_CICLO) -> None:
    """Loop asyncio. Integrar en lifespan de FastAPI."""
    logger.info(f"Worker pipeline iniciado (ciclo cada {intervalo}s)")
    while True:
        try:
            ejecutar_ciclo_worker(sesion_factory)
        except Exception as e:
            logger.error(f"Error en ciclo worker pipeline: {e}", exc_info=True)
        await asyncio.sleep(intervalo)
