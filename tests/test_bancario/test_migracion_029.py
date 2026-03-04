"""Tests migración 029 — conciliación bancaria inteligente."""
import importlib.util
import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import sfce.db.modelos_auth  # registra Gestoria en Base.metadata (FK gestorias.id)
from sfce.db.modelos import Base


def _cargar_migracion():
    spec = importlib.util.spec_from_file_location(
        "m029",
        "sfce/db/migraciones/029_conciliacion_inteligente.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def engine():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return eng


def test_tablas_nuevas_existen(engine):
    mod = _cargar_migracion()
    mod.aplicar(engine)
    inspector = inspect(engine)
    tablas = inspector.get_table_names()
    assert "sugerencias_match" in tablas
    assert "patrones_conciliacion" in tablas
    assert "conciliaciones_parciales" in tablas


def test_columnas_cuentas_bancarias(engine):
    mod = _cargar_migracion()
    mod.aplicar(engine)
    inspector = inspect(engine)
    cols = {c["name"] for c in inspector.get_columns("cuentas_bancarias")}
    assert "saldo_bancario_ultimo" in cols
    assert "fecha_saldo_ultimo" in cols


def test_columnas_movimientos_bancarios(engine):
    mod = _cargar_migracion()
    mod.aplicar(engine)
    inspector = inspect(engine)
    cols = {c["name"] for c in inspector.get_columns("movimientos_bancarios")}
    assert "documento_id" in cols
    assert "score_confianza" in cols
    assert "metadata_match" in cols
    assert "capa_match" in cols


def test_idempotente(engine):
    mod = _cargar_migracion()
    mod.aplicar(engine)
    mod.aplicar(engine)  # segunda vez no debe lanzar excepción
