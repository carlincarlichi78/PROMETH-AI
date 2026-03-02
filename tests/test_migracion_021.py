"""Tests para migración 021: backfill slug en empresas existentes."""
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool


def _motor_test():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS empresas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cif TEXT NOT NULL,
                nombre TEXT NOT NULL,
                slug TEXT
            )
        """))
    return engine


def test_backfill_slug_genera_valores():
    engine = _motor_test()
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO empresas (cif, nombre, slug) VALUES ('A12345678', 'Fulano SL', NULL)"))
        conn.execute(text("INSERT INTO empresas (cif, nombre, slug) VALUES ('B87654321', 'Mengano & Asociados', NULL)"))
        conn.execute(text("INSERT INTO empresas (cif, nombre, slug) VALUES ('C11111111', 'Fulano CB', 'ya-tiene-slug')"))

    from sfce.db.migraciones.migracion_021_empresa_slug_backfill import ejecutar
    ejecutar(engine)

    with engine.connect() as conn:
        fulano = conn.execute(text("SELECT slug FROM empresas WHERE cif='A12345678'")).scalar()
        mengano = conn.execute(text("SELECT slug FROM empresas WHERE cif='B87654321'")).scalar()
        preservado = conn.execute(text("SELECT slug FROM empresas WHERE cif='C11111111'")).scalar()

    assert fulano == "fulanosl"
    assert mengano == "menganoyasociados"  # sin & ni espacios
    assert preservado == "ya-tiene-slug"  # no se sobreescribe


def test_backfill_slug_evita_colisiones():
    engine = _motor_test()
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO empresas (cif, nombre, slug) VALUES ('A00000001', 'Fulano SL', NULL)"))
        conn.execute(text("INSERT INTO empresas (cif, nombre, slug) VALUES ('A00000002', 'Fulano SA', NULL)"))

    from sfce.db.migraciones.migracion_021_empresa_slug_backfill import ejecutar
    ejecutar(engine)

    with engine.connect() as conn:
        slugs = [r[0] for r in conn.execute(text("SELECT slug FROM empresas ORDER BY id")).fetchall()]

    assert len(set(slugs)) == 2  # ambos únicos
    assert "fulanosl" in slugs
    assert "fulanosa" in slugs
