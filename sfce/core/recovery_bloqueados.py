"""Recovery de documentos bloqueados en la cola de procesamiento.

Detecta documentos que llevan demasiado tiempo en estado PROCESANDO
(indicativo de que el worker crasheó o fue interrumpido) y los resetea
a PENDIENTE para que el worker los reintente.

Tras MAX_REINTENTOS fallidos, el documento pasa a CUARENTENA definitivamente.
"""
from datetime import datetime, timedelta
from typing import Optional

from .logger import crear_logger

logger = crear_logger("recovery_bloqueados")

# Tiempo máximo en estado PROCESANDO antes de considerarlo bloqueado
TIMEOUT_PROCESANDO = timedelta(hours=1)

# Máximo de reintentos antes de enviar a CUARENTENA definitiva
MAX_REINTENTOS = 3


def recovery_documentos_bloqueados(sesion) -> dict:
    """Detecta y recupera documentos bloqueados en estado PROCESANDO.

    Proceso:
      1. Busca docs en PROCESANDO con worker_inicio > TIMEOUT_PROCESANDO
      2. Si reintentos < MAX_REINTENTOS → reset a PENDIENTE + incrementar reintentos
      3. Si reintentos >= MAX_REINTENTOS → PROCESADO con decision CUARENTENA

    Args:
        sesion: Sesión SQLAlchemy activa.

    Returns:
        dict con claves: bloqueados (total), resetados (a PENDIENTE), cuarentena (definitivo).
    """
    from sfce.db.modelos import ColaProcesamiento

    limite_tiempo = datetime.utcnow() - TIMEOUT_PROCESANDO

    bloqueados = (
        sesion.query(ColaProcesamiento)
        .filter(
            ColaProcesamiento.estado == "PROCESANDO",
            ColaProcesamiento.worker_inicio < limite_tiempo,
        )
        .all()
    )

    resetados = 0
    cuarentena = 0

    for doc in bloqueados:
        if doc.reintentos is not None and doc.reintentos >= MAX_REINTENTOS:
            # Demasiados intentos → cuarentena definitiva
            doc.estado = "PROCESADO"
            doc.decision = "CUARENTENA"
            cuarentena += 1
            logger.warning(
                f"Doc {doc.id} ({doc.nombre_archivo}): max reintentos alcanzado, enviado a CUARENTENA"
            )
        else:
            # Reset para retry
            doc.estado = "PENDIENTE"
            doc.worker_inicio = None
            doc.reintentos = (doc.reintentos or 0) + 1
            resetados += 1
            logger.info(
                f"Doc {doc.id} ({doc.nombre_archivo}): reset a PENDIENTE (reintento {doc.reintentos})"
            )

    sesion.commit()

    return {
        "bloqueados": len(bloqueados),
        "resetados": resetados,
        "cuarentena": cuarentena,
    }
