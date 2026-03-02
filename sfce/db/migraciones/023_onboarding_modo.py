"""Migración 023 — añade columna modo a onboarding_lotes."""
import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)


def upgrade(sesion) -> None:
    sesion.execute(text("""
        ALTER TABLE onboarding_lotes
        ADD COLUMN modo TEXT NOT NULL DEFAULT 'zip'
    """))
    sesion.commit()
    logger.info("023: columna modo añadida a onboarding_lotes")


def downgrade(sesion) -> None:
    # SQLite no soporta DROP COLUMN — para PG:
    sesion.execute(text("""
        ALTER TABLE onboarding_lotes DROP COLUMN IF EXISTS modo
    """))
    sesion.commit()


if __name__ == "__main__":
    import os
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    dsn = os.environ["DATABASE_URL"]
    engine = create_engine(dsn)
    Session = sessionmaker(bind=engine)
    with Session() as s:
        upgrade(s)
        print("Migración 023 aplicada.")
