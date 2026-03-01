"""Worker async OCR Gate 0 — daemon de procesamiento automático de documentos.

Procesa la cola `ColaProcesamiento` en background:
  1. Extrae datos OCR (cascada Tier 0/1/2: Mistral → GPT → Gemini)
  2. Verifica coherencia fiscal
  3. Calcula score Gate 0 con 5 factores
  4. Decide destino (AUTO_PUBLICADO / COLA_REVISION / COLA_ADMIN / CUARENTENA)

Se integra en el lifespan de FastAPI. Corre cada `intervalo` segundos.
Recovery de docs bloqueados cada 10 ciclos (≈5 min con intervalo=30s).
"""
import asyncio
import json
import logging
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from typing import Optional

from .logger import crear_logger

logger = crear_logger("worker_ocr")

# Límite de documentos por ciclo (evita saturar APIs)
_LIMITE_POR_CICLO = 10
# Cada cuántos ciclos ejecutar recovery de bloqueados
_CICLOS_RECOVERY = 10


# ---------------------------------------------------------------------------
# Helpers de BD
# ---------------------------------------------------------------------------

def obtener_pendientes(sesion, limite: int = _LIMITE_POR_CICLO):
    """Retorna documentos en estado PENDIENTE (límite N)."""
    from sfce.db.modelos import ColaProcesamiento
    return (
        sesion.query(ColaProcesamiento)
        .filter(ColaProcesamiento.estado == "PENDIENTE")
        .limit(limite)
        .all()
    )


# ---------------------------------------------------------------------------
# OCR en cascada
# ---------------------------------------------------------------------------

def _ejecutar_ocr_tiers(ruta_pdf: Path) -> Optional[dict]:
    """Ejecuta OCR en cascada Tier 0 → Tier 1 → Tier 2.

    Tier 0: Mistral OCR3 (primario, más económico)
    Tier 1: GPT-4o (fallback Tier 0)
    Tier 2: Gemini Flash (fallback final)

    Retorna dict con datos extraídos o None si todos fallan.
    """
    # Tier 0: Mistral
    try:
        from sfce.core.ocr_mistral import extraer_factura_mistral
        datos = extraer_factura_mistral(ruta_pdf)
        if datos:
            logger.info(f"Tier 0 (Mistral) OK: {ruta_pdf.name}")
            return datos
    except Exception as e:
        logger.warning(f"Tier 0 Mistral falló para {ruta_pdf.name}: {e}")

    # Tier 1: GPT-4o
    try:
        from sfce.core.ocr_gpt import extraer_factura_gpt
        datos = extraer_factura_gpt(ruta_pdf)
        if datos:
            logger.info(f"Tier 1 (GPT-4o) OK: {ruta_pdf.name}")
            return datos
    except Exception as e:
        logger.warning(f"Tier 1 GPT falló para {ruta_pdf.name}: {e}")

    # Tier 2: Gemini
    try:
        from sfce.core.ocr_gemini import extraer_factura_gemini
        datos = extraer_factura_gemini(ruta_pdf)
        if datos:
            logger.info(f"Tier 2 (Gemini) OK: {ruta_pdf.name}")
            return datos
    except Exception as e:
        logger.warning(f"Tier 2 Gemini falló para {ruta_pdf.name}: {e}")

    logger.error(f"Todos los tiers OCR fallaron para {ruta_pdf.name}")
    return None


# ---------------------------------------------------------------------------
# Procesamiento de un documento
# ---------------------------------------------------------------------------

async def procesar_documento_ocr(doc_id: int, sesion_factory) -> None:
    """Procesa un documento en la cola: OCR → coherencia → score → decisión.

    En caso de excepción, resetea el estado a PENDIENTE para retry.
    """
    from sfce.db.modelos import ColaProcesamiento
    from sfce.core.coherencia_fiscal import verificar_coherencia_fiscal
    from sfce.core.gate0 import (
        calcular_score, decidir_destino,
        TrustLevel, Decision,
    )

    # Capturar atributos necesarios dentro de la sesión antes de cerrarla
    ruta_archivo = None
    trust_level_str = "BAJA"

    with sesion_factory() as sesion:
        doc = sesion.get(ColaProcesamiento, doc_id)
        if doc is None or doc.estado != "PENDIENTE":
            return

        # Capturar antes de cerrar sesión (evita DetachedInstanceError)
        ruta_archivo = doc.ruta_archivo
        trust_level_str = doc.trust_level or "BAJA"

        # Marcar como PROCESANDO
        doc.estado = "PROCESANDO"
        doc.worker_inicio = datetime.utcnow()
        sesion.commit()

    try:
        ruta_pdf = Path(ruta_archivo)

        # --- OCR tiers ---
        datos_ocr: Optional[dict] = None
        if ruta_pdf.exists():
            datos_ocr = _ejecutar_ocr_tiers(ruta_pdf)

        if not datos_ocr:
            _finalizar_doc(doc_id, sesion_factory, decision="CUARENTENA", score=0.0, datos_ocr=None)
            return

        # --- Coherencia fiscal ---
        coherencia = verificar_coherencia_fiscal(datos_ocr)

        # --- Score Gate 0 (5 factores) ---
        trust = _trust_desde_nivel(trust_level_str)
        score = calcular_score(
            confianza_ocr=_confianza_desde_ocr(datos_ocr),
            trust_level=trust,
            supplier_rule_aplicada=False,  # supplier rules se aplican en Gate 0 API, no en worker
            checks_pasados=0,
            checks_totales=0,
            coherencia=coherencia,
        )

        # --- Decisión ---
        decision = decidir_destino(score=score, trust=trust, coherencia=coherencia)

        _finalizar_doc(doc_id, sesion_factory, decision=decision.value, score=score, datos_ocr=datos_ocr,
                       coherencia_score=coherencia.score)

    except Exception as e:
        logger.error(f"Error procesando doc {doc_id}: {e}")
        # Reset a PENDIENTE para retry
        with sesion_factory() as sesion:
            doc = sesion.get(ColaProcesamiento, doc_id)
            if doc:
                doc.estado = "PENDIENTE"
                doc.worker_inicio = None
                sesion.commit()


def _finalizar_doc(
    doc_id: int,
    sesion_factory,
    decision: str,
    score: float,
    datos_ocr: Optional[dict],
    coherencia_score: Optional[float] = None,
) -> None:
    """Guarda resultado final en BD."""
    from sfce.db.modelos import ColaProcesamiento
    with sesion_factory() as sesion:
        doc = sesion.get(ColaProcesamiento, doc_id)
        if doc:
            doc.estado = "PROCESADO"
            doc.decision = decision
            doc.score_final = score
            doc.coherencia_score = coherencia_score
            if datos_ocr:
                doc.datos_ocr_json = json.dumps(datos_ocr, ensure_ascii=False)
            sesion.commit()


def _trust_desde_nivel(trust_level: str):
    """Convierte string a TrustLevel enum."""
    from sfce.core.gate0 import TrustLevel
    try:
        return TrustLevel(trust_level.upper())
    except ValueError:
        return TrustLevel.BAJA


def _confianza_desde_ocr(datos_ocr: dict) -> float:
    """Extrae confianza OCR del resultado (si el motor la incluye)."""
    # Mistral incluye _confianza, otros no
    confianza = datos_ocr.get("_confianza", datos_ocr.get("confianza_ocr", None))
    if confianza is None:
        # Inferir por campos presentes
        campos_clave = ["emisor_cif", "total", "base_imponible", "fecha_factura"]
        presentes = sum(1 for c in campos_clave if datos_ocr.get(c))
        confianza = presentes / len(campos_clave)
    return float(min(max(confianza, 0.0), 1.0))


# ---------------------------------------------------------------------------
# Loop principal del worker
# ---------------------------------------------------------------------------

async def loop_worker_ocr(
    sesion_factory,
    intervalo: int = 30,
) -> None:
    """Corrutina async principal. Procesa la cola en ciclos de `intervalo` segundos.

    - Procesa hasta _LIMITE_POR_CICLO documentos por ciclo.
    - Cada _CICLOS_RECOVERY ciclos ejecuta recovery de bloqueados.
    - Se detiene limpiamente al recibir CancelledError.
    """
    ciclo = 0
    logger.info("Worker OCR Gate 0 iniciado")

    while True:
        try:
            ciclo += 1

            # Recovery de docs bloqueados cada N ciclos
            if ciclo % _CICLOS_RECOVERY == 0:
                try:
                    from sfce.core.recovery_bloqueados import recovery_documentos_bloqueados
                    with sesion_factory() as sesion:
                        resultado = recovery_documentos_bloqueados(sesion)
                    if resultado.get("resetados", 0) > 0:
                        logger.info(f"Recovery: {resultado}")
                except ImportError:
                    pass  # recovery_bloqueados aún no disponible
                except Exception as e:
                    logger.warning(f"Error en recovery: {e}")

            # Obtener y procesar pendientes
            with sesion_factory() as sesion:
                pendientes = obtener_pendientes(sesion, limite=_LIMITE_POR_CICLO)
                ids_pendientes = [doc.id for doc in pendientes]

            if ids_pendientes:
                logger.debug(f"Ciclo {ciclo}: procesando {len(ids_pendientes)} documentos")
                for doc_id in ids_pendientes:
                    await procesar_documento_ocr(doc_id, sesion_factory)

        except asyncio.CancelledError:
            logger.info("Worker OCR Gate 0 detenido")
            raise
        except Exception as e:
            logger.error(f"Error en ciclo {ciclo} del worker: {e}")

        await asyncio.sleep(intervalo)
