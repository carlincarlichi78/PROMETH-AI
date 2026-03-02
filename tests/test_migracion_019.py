import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool


@pytest.fixture
def engine_019():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Crear tabla minimal antes de migrar
    with eng.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS cuentas_correo (
                id INTEGER PRIMARY KEY,
                empresa_id INTEGER NOT NULL,
                nombre TEXT NOT NULL,
                protocolo TEXT NOT NULL,
                usuario TEXT NOT NULL,
                activa INTEGER DEFAULT 1
            )
        """))
    return eng


def test_migrar_019_añade_gestoria_id(engine_019):
    from sfce.db.migraciones.migracion_019_cuentas_correo_gestoria import ejecutar
    ejecutar(engine_019)
    with engine_019.connect() as conn:
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info(cuentas_correo)")).fetchall()}
    assert "gestoria_id" in cols
    assert "tipo_cuenta" in cols


def test_migrar_019_es_idempotente(engine_019):
    from sfce.db.migraciones.migracion_019_cuentas_correo_gestoria import ejecutar
    ejecutar(engine_019)
    ejecutar(engine_019)  # segunda ejecucion no falla


def test_migrar_019_tipo_cuenta_default_empresa(engine_019):
    from sfce.db.migraciones.migracion_019_cuentas_correo_gestoria import ejecutar
    ejecutar(engine_019)
    with engine_019.begin() as conn:
        conn.execute(text(
            "INSERT INTO cuentas_correo (empresa_id, nombre, protocolo, usuario) "
            "VALUES (1, 'Test', 'imap', 'u@test.com')"
        ))
        row = conn.execute(text("SELECT tipo_cuenta FROM cuentas_correo WHERE id=1")).fetchone()
    assert row[0] == "empresa"


def test_migrar_019_empresa_id_nullable(engine_019):
    from sfce.db.migraciones.migracion_019_cuentas_correo_gestoria import ejecutar
    ejecutar(engine_019)
    # empresa_id ahora es nullable — debe aceptar NULL
    with engine_019.begin() as conn:
        conn.execute(text(
            "INSERT INTO cuentas_correo (gestoria_id, tipo_cuenta, nombre, protocolo, usuario) "
            "VALUES (7, 'gestoria', 'Gestoría1', 'imap', 'g1@prometh-ai.es')"
        ))
        row = conn.execute(text(
            "SELECT gestoria_id, tipo_cuenta FROM cuentas_correo ORDER BY id DESC LIMIT 1"
        )).fetchone()
    assert row[0] == 7
    assert row[1] == "gestoria"
