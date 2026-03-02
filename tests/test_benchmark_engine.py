"""Tests para benchmark_engine.py — Sector Brain (TDD)."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from sfce.analytics.modelos_analiticos import Base as BaseAnalitica, FactCaja
from sfce.db.modelos import Base as BaseApp, Empresa
import sfce.db.modelos_auth  # noqa: F401 — importar para registrar Gestoria en Base


@pytest.fixture
def sesion():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    BaseAnalitica.metadata.create_all(engine)
    BaseApp.metadata.create_all(engine)
    Session = sessionmaker(engine)
    with Session() as s:
        yield s


def test_menos_de_min_empresas_retorna_none(sesion):
    """Con menos de 5 empresas no hay benchmarks (anonimato)."""
    from sfce.analytics.benchmark_engine import calcular_percentiles_sector
    # 3 empresas activas con CNAE 5610
    for i in range(3):
        emp = Empresa(nombre=f"Emp{i}", cif=f"B1234567{i}", forma_juridica="sl", cnae="5610", activa=True)
        sesion.add(emp)
    sesion.commit()
    result = calcular_percentiles_sector(sesion, "5610", "ticket_medio")
    assert result is None


def test_cinco_empresas_devuelve_percentiles(sesion):
    """Con 5+ empresas devuelve P25/P50/P75."""
    from sfce.analytics.benchmark_engine import calcular_percentiles_sector
    from datetime import date
    for i in range(5):
        emp = Empresa(nombre=f"Emp{i}", cif=f"B9876543{i}", forma_juridica="sl", cnae="5610", activa=True)
        sesion.add(emp)
    sesion.flush()
    # Añadir fact_caja para cada empresa
    empresas = sesion.query(Empresa).all()
    tickets = [10.0, 15.0, 20.0, 25.0, 30.0]
    for emp, t in zip(empresas, tickets):
        sesion.add(FactCaja(
            empresa_id=emp.id,
            fecha=date.today(),
            servicio="almuerzo",
            covers=20,
            ventas_totales=t * 20,
            ticket_medio=t,
            metodo_pago_tarjeta=t * 20 * 0.8,
            metodo_pago_efectivo=t * 20 * 0.2,
        ))
    sesion.commit()
    result = calcular_percentiles_sector(sesion, "5610", "ticket_medio")
    assert result is not None
    assert "p25" in result
    assert "p50" in result
    assert "p75" in result
    assert result["n_empresas"] == 5


def test_kpi_no_soportado_retorna_none(sesion):
    """KPI desconocido retorna None inmediatamente."""
    from sfce.analytics.benchmark_engine import calcular_percentiles_sector
    result = calcular_percentiles_sector(sesion, "5610", "kpi_no_existe")
    assert result is None


def test_posicion_en_sector_cuartiles(sesion):
    """posicion_en_sector clasifica correctamente."""
    from sfce.analytics.benchmark_engine import posicion_en_sector
    percentiles = {"p25": 10.0, "p50": 20.0, "p75": 30.0}
    assert posicion_en_sector(5.0, percentiles)["color"] == "rojo"
    assert posicion_en_sector(15.0, percentiles)["color"] == "amarillo"
    assert posicion_en_sector(25.0, percentiles)["color"] == "verde"
    assert posicion_en_sector(35.0, percentiles)["color"] == "verde"


def test_cnae_vacio_retorna_none(sesion):
    """CNAE vacío o sin empresas suficientes → None (sin benchmarks)."""
    from sfce.analytics.benchmark_engine import calcular_percentiles_sector
    assert calcular_percentiles_sector(sesion, "", "ticket_medio") is None
    assert calcular_percentiles_sector(sesion, "9999", "ticket_medio") is None
