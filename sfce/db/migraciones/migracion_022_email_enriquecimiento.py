"""Migración 022: campos enriquecimiento en emails_procesados."""
import logging
from sqlalchemy import Engine, text

logger = logging.getLogger(__name__)


def ejecutar(engine: Engine) -> None:
    with engine.begin() as conn:
        for col in ("enriquecimiento_pendiente_json", "enriquecimiento_aplicado_json"):
            try:
                conn.execute(text(f"ALTER TABLE emails_procesados ADD COLUMN {col} TEXT"))
                logger.info("Columna %s añadida.", col)
            except Exception:
                logger.info("Columna %s ya existe, omitiendo.", col)
    logger.info("Migración 022 completada.")


if __name__ == "__main__":
    from sfce.db.base import crear_motor
    ejecutar(crear_motor())
