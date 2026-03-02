import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.pool import StaticPool


@pytest.fixture
def engine_con_migracion():
    from sfce.db.base import Base
    import sfce.db.modelos
    import sfce.db.modelos_auth
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    from sfce.db.migraciones.migracion_018_email_mejorado import ejecutar
    ejecutar(engine)
    return engine


def test_tabla_remitentes_autorizados_existe(engine_con_migracion):
    insp = inspect(engine_con_migracion)
    assert "remitentes_autorizados" in insp.get_table_names()


def test_tabla_contrasenas_zip_existe(engine_con_migracion):
    insp = inspect(engine_con_migracion)
    assert "contrasenas_zip" in insp.get_table_names()


def test_emails_procesados_tiene_campo_es_respuesta_ack(engine_con_migracion):
    insp = inspect(engine_con_migracion)
    cols = {c["name"] for c in insp.get_columns("emails_procesados")}
    assert "es_respuesta_ack" in cols


def test_emails_procesados_tiene_score_confianza(engine_con_migracion):
    insp = inspect(engine_con_migracion)
    cols = {c["name"] for c in insp.get_columns("emails_procesados")}
    assert "score_confianza" in cols


def test_emails_procesados_tiene_motivo_cuarentena(engine_con_migracion):
    insp = inspect(engine_con_migracion)
    cols = {c["name"] for c in insp.get_columns("emails_procesados")}
    assert "motivo_cuarentena" in cols


def test_cola_procesamiento_tiene_empresa_origen_correo(engine_con_migracion):
    insp = inspect(engine_con_migracion)
    cols = {c["name"] for c in insp.get_columns("cola_procesamiento")}
    assert "empresa_origen_correo_id" in cols


def test_migracion_es_idempotente(engine_con_migracion):
    from sfce.db.migraciones.migracion_018_email_mejorado import ejecutar
    ejecutar(engine_con_migracion)   # segunda ejecución no debe fallar
    insp = inspect(engine_con_migracion)
    assert "remitentes_autorizados" in insp.get_table_names()
