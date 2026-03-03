"""
Worker daemon de procesamiento de documentos por pipeline.
Complementa worker_ocr_gate0 (que hace OCR + scoring).
Este worker lanza el pipeline completo (7 fases) cuando toca según schedule.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy import select, update

from sfce.api.websocket import (
    EVENTO_CUARENTENA_NUEVO,
    EVENTO_DOCUMENTO_PROCESADO,
    EVENTO_PIPELINE_PROGRESO,
    gestor_ws,
)
from sfce.core.pipeline_runner import (
    ejecutar_pipeline_empresa,
    adquirir_lock_empresa,
    liberar_lock_empresa,
)
from sfce.db.modelos import ColaProcesamiento, ConfigProcesamientoEmpresa

logger = logging.getLogger(__name__)


def _emitir_evento_pipeline(empresa_id: int, evento: str, datos: dict) -> None:
    """Emite evento WS desde contexto sincrono. No bloquea el pipeline si falla."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(gestor_ws.emitir_a_empresa(empresa_id, evento, datos))
    except Exception:
        pass

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


def _clamar_docs_para_empresa(empresa_id: int, sesion_factory) -> list[int]:
    """Reclama atomicamente entradas de cola PENDIENTE/APROBADO → PROCESANDO.

    El SELECT y el UPDATE ocurren dentro de la misma transaccion con
    with_for_update(), lo que serializa el acceso a nivel de BD y evita
    que dos workers distintos procesen el mismo documento.

    SQLite (WAL + busy_timeout=5000) serializa writers; PostgreSQL usa
    row-level locks. En ambos casos el par SELECT-UPDATE es atomico dentro
    de la transaccion.

    Retorna la lista de documento_id reclamados (puede ser menor que las
    entradas si alguna entrada no tiene documento_id asociado aun).
    """
    with sesion_factory() as s:
        cfg = s.query(ConfigProcesamientoEmpresa).filter_by(empresa_id=empresa_id).first()
        modo = cfg.modo if cfg else "revision"
        estados_validos = ["PENDIENTE"] if modo == "auto" else ["APROBADO"]

        # SELECT con bloqueo de filas para evitar lectura simultanea por otro worker
        ids_cola = s.scalars(
            select(ColaProcesamiento.id)
            .where(
                ColaProcesamiento.empresa_id == empresa_id,
                ColaProcesamiento.estado.in_(estados_validos),
            )
            .with_for_update()
        ).all()

        if not ids_cola:
            return []

        # UPDATE atomico dentro de la misma transaccion (antes del commit)
        s.execute(
            update(ColaProcesamiento)
            .where(ColaProcesamiento.id.in_(ids_cola))
            .values(estado="PROCESANDO", worker_inicio=datetime.utcnow())
        )
        s.flush()

        # Recuperar documento_ids de las entradas reclamadas
        filas = s.scalars(
            select(ColaProcesamiento.documento_id)
            .where(ColaProcesamiento.id.in_(ids_cola))
        ).all()

        s.commit()

    return [doc_id for doc_id in filas if doc_id is not None]


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
                _emitir_evento_pipeline(empresa_id, EVENTO_CUARENTENA_NUEVO, {
                    "nombre_archivo": doc.ruta_pdf or "",
                    "motivo": doc.motivo_cuarentena or "Revision requerida",
                    "empresa_id": empresa_id,
                })
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
            doc_ids = _clamar_docs_para_empresa(empresa_id, sesion_factory)
            if not doc_ids:
                continue

            logger.info(f"Empresa {empresa_id}: lanzando pipeline para {len(doc_ids)} docs")
            _emitir_evento_pipeline(empresa_id, EVENTO_PIPELINE_PROGRESO, {
                "estado": "procesando",
                "docs_count": len(doc_ids),
                "empresa_id": empresa_id,
            })
            resultado = ejecutar_pipeline_empresa(
                empresa_id=empresa_id,
                sesion_factory=sesion_factory,
                documentos_ids=doc_ids,
            )
            _actualizar_ultimo_pipeline(empresa_id, sesion_factory)
            estado_final = "registrado" if resultado.exito else "error"
            _emitir_evento_pipeline(empresa_id, EVENTO_DOCUMENTO_PROCESADO, {
                "estado": estado_final,
                "docs_procesados": resultado.docs_procesados,
                "empresa_id": empresa_id,
            })
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


def _resetear_docs_procesando(sesion_factory) -> None:
    """Devuelve a PENDIENTE los docs que quedaron en PROCESANDO al apagar el worker."""
    try:
        with sesion_factory() as s:
            s.execute(
                update(ColaProcesamiento)
                .where(ColaProcesamiento.estado == "PROCESANDO")
                .values(estado="PENDIENTE", worker_inicio=None)
            )
            s.commit()
            logger.info("Worker pipeline: docs PROCESANDO resetados a PENDIENTE")
    except Exception as e:
        logger.error(f"Error reseteando docs PROCESANDO: {e}", exc_info=True)


async def loop_worker_pipeline(sesion_factory, intervalo: int = _INTERVALO_CICLO) -> None:
    """Loop asyncio. Integrar en lifespan de FastAPI.

    Al recibir CancelledError (shutdown), resetea los docs que quedaron
    en estado PROCESANDO para que el próximo arranque los reintente.
    """
    logger.info(f"Worker pipeline iniciado (ciclo cada {intervalo}s)")
    try:
        while True:
            try:
                ejecutar_ciclo_worker(sesion_factory)
            except Exception as e:
                logger.error(f"Error en ciclo worker pipeline: {e}", exc_info=True)
            await asyncio.sleep(intervalo)
    except asyncio.CancelledError:
        logger.info("Worker pipeline: recibida señal de parada, limpiando...")
        _resetear_docs_procesando(sesion_factory)
        raise
