import sfce.db.modelos  # noqa: F401 — registra todos los mappers en Base.metadata
import sfce.db.modelos_auth  # noqa: F401
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool
from sfce.db.base import Base


def _motor():
    e = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(e)
    return e


def test_migra_columnas_email():
    engine = _motor()
    from sfce.db.migraciones.migracion_022_email_enriquecimiento import ejecutar
    ejecutar(engine)
    with engine.connect() as conn:
        cols = [r[1] for r in conn.execute(text("PRAGMA table_info(emails_procesados)")).fetchall()]
    assert "enriquecimiento_pendiente_json" in cols
    assert "enriquecimiento_aplicado_json" in cols
