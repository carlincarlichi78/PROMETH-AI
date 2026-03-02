"""Migración 021: backfill slug en empresas existentes."""
import re
import logging
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def _slug_desde_nombre(nombre: str) -> str:
    """Genera slug URL-friendly desde nombre de empresa."""
    # Convertir & en 'y' antes de limpiar
    nombre_normalizado = nombre.lower().replace("&", "y")
    return re.sub(r"[^a-z0-9]", "", nombre_normalizado)[:20]


def _slug_unico(base: str, existentes: set[str]) -> str:
    if base not in existentes:
        return base
    for i in range(1, 100):
        candidato = f"{base[:17]}{i:03d}"
        if candidato not in existentes:
            return candidato
    raise RuntimeError(f"No se pudo generar slug único para '{base}'")


def ejecutar(engine: Engine) -> None:
    with Session(engine) as sesion:
        rows = sesion.execute(
            text("SELECT id, nombre, slug FROM empresas")
        ).fetchall()

        slugs_usados: set[str] = {r[2] for r in rows if r[2]}

        for emp_id, nombre, slug_actual in rows:
            if slug_actual:
                continue
            base = _slug_desde_nombre(nombre or f"empresa{emp_id}")
            nuevo_slug = _slug_unico(base, slugs_usados)
            slugs_usados.add(nuevo_slug)
            sesion.execute(
                text("UPDATE empresas SET slug = :slug WHERE id = :id"),
                {"slug": nuevo_slug, "id": emp_id},
            )
            logger.info("Empresa %d: slug = '%s'", emp_id, nuevo_slug)

        sesion.commit()
    logger.info("Migración 021 completada.")


if __name__ == "__main__":
    from sfce.db.base import crear_motor
    ejecutar(crear_motor())
