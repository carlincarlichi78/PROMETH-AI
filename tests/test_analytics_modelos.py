"""Tests TDD para star schema analítico — modelos SQLAlchemy."""
import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sfce.analytics.modelos_analiticos import Base, FactVenta, FactCompra, FactPersonal, FactCaja, EventoAnalitico


@pytest.fixture
def engine():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return eng


def test_tablas_creadas(engine):
    ins = inspect(engine)
    tablas = ins.get_table_names()
    assert "fact_venta" in tablas
    assert "fact_compra" in tablas
    assert "fact_personal" in tablas
    assert "fact_caja" in tablas
    assert "eventos_analiticos" in tablas


def test_fact_caja_columnas(engine):
    ins = inspect(engine)
    cols = {c["name"] for c in ins.get_columns("fact_caja")}
    assert {"empresa_id", "fecha", "servicio", "covers", "ventas_totales",
            "ticket_medio", "metodo_pago_tarjeta", "metodo_pago_efectivo"}.issubset(cols)


def test_fact_venta_columnas(engine):
    ins = inspect(engine)
    cols = {c["name"] for c in ins.get_columns("fact_venta")}
    assert {"empresa_id", "fecha", "servicio", "producto_nombre",
            "familia", "qty", "pvp_unitario", "total"}.issubset(cols)


def test_alerta_analitica_columnas(engine):
    ins = inspect(engine)
    tablas = ins.get_table_names()
    assert "alertas_analiticas" in tablas
    cols = {c["name"] for c in ins.get_columns("alertas_analiticas")}
    assert {"empresa_id", "alerta_id", "severidad", "mensaje",
            "activa", "creada_en"}.issubset(cols)
