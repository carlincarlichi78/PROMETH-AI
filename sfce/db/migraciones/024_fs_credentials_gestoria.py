"""Migración 024 — añade fs_url y fs_token_enc a tabla gestorias.

Permite que cada gestoría tenga su propia instancia de FacturaScripts.
- fs_url: URL base de la API REST de FacturaScripts (ej: https://fs.migestoria.es/api/3)
- fs_token_enc: token API cifrado con Fernet (SFCE_FERNET_KEY)
Ambos nullables: si son NULL se usa la instancia global del sistema.
"""
import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)


def upgrade(sesion) -> None:
    dialect = sesion.bind.dialect.name if hasattr(sesion, "bind") else "sqlite"
    # Detectar dialect desde la conexión
    try:
        dialect = sesion.get_bind().dialect.name
    except Exception:
        pass

    sesion.execute(text("ALTER TABLE gestorias ADD COLUMN fs_url TEXT"))
    sesion.execute(text("ALTER TABLE gestorias ADD COLUMN fs_token_enc TEXT"))
    sesion.commit()
    logger.info("024: columnas fs_url + fs_token_enc añadidas a gestorias")


def downgrade(sesion) -> None:
    # SQLite no soporta DROP COLUMN — solo PG
    sesion.execute(text("ALTER TABLE gestorias DROP COLUMN IF EXISTS fs_url"))
    sesion.execute(text("ALTER TABLE gestorias DROP COLUMN IF EXISTS fs_token_enc"))
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
        print("Migración 024 aplicada.")
