"""Migración 026 — tabla tokens_servicio para autenticación del pipeline.

Crea la tabla tokens_servicio que permite al pipeline local (y otros servicios)
autenticarse con la API SFCE sin usar credenciales de usuario humano.
El token raw se entrega una sola vez al crear; en BD se almacena su SHA256.
"""
import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)


def upgrade(sesion) -> None:
    dialect = sesion.bind.dialect.name if sesion.bind else "sqlite"

    if dialect == "postgresql":
        sesion.execute(text("""
            CREATE TABLE IF NOT EXISTS tokens_servicio (
                id          SERIAL PRIMARY KEY,
                nombre      VARCHAR(200) NOT NULL,
                token_hash  VARCHAR(64) NOT NULL UNIQUE,
                gestoria_id INTEGER,
                empresa_ids TEXT NOT NULL DEFAULT '[]',
                activo      BOOLEAN NOT NULL DEFAULT TRUE,
                creado_en   TIMESTAMP NOT NULL,
                ultimo_uso  TIMESTAMP
            )
        """))
        sesion.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS ix_tokens_servicio_hash
            ON tokens_servicio (token_hash)
        """))
    else:
        sesion.execute(text("""
            CREATE TABLE IF NOT EXISTS tokens_servicio (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre      TEXT NOT NULL,
                token_hash  TEXT NOT NULL UNIQUE,
                gestoria_id INTEGER,
                empresa_ids TEXT NOT NULL DEFAULT '[]',
                activo      BOOLEAN NOT NULL DEFAULT 1,
                creado_en   TEXT NOT NULL,
                ultimo_uso  TEXT
            )
        """))

    sesion.commit()
    logger.info("026: tabla tokens_servicio creada")


def downgrade(sesion) -> None:
    sesion.execute(text("DROP TABLE IF EXISTS tokens_servicio"))
    sesion.commit()
    logger.info("026: tabla tokens_servicio eliminada")


if __name__ == "__main__":
    import os
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    dsn = os.environ.get("DATABASE_URL", "sqlite:///sfce.db")
    engine = create_engine(dsn)
    Session = sessionmaker(bind=engine)
    with Session() as s:
        s.bind = engine  # type: ignore[attr-defined]
        upgrade(s)
        print("Migración 026 aplicada.")
