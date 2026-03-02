"""Worker async de polling de correo para el lifespan de FastAPI."""
import asyncio
import logging
from sfce.conectores.correo.ingesta_correo import ejecutar_polling_todas_las_cuentas

logger = logging.getLogger(__name__)

_INTERVALO_DEFAULT = 60  # segundos


async def loop_polling_correo(sesion_factory, intervalo_segundos: int = _INTERVALO_DEFAULT):
    """Loop async que ejecuta el polling de todas las cuentas de correo activas."""
    logger.info("Worker correo arrancado (intervalo=%ds)", intervalo_segundos)
    while True:
        try:
            engine = sesion_factory.kw.get("bind") or sesion_factory.bind
            ejecutar_polling_todas_las_cuentas(engine)
        except Exception as exc:
            logger.error("Error en polling correo: %s", exc)
        await asyncio.sleep(intervalo_segundos)
