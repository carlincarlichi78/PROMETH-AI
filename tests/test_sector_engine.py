import pytest
from pathlib import Path
from sfce.analytics.sector_engine import SectorEngine, KPIResultado, AlertaGenerada

YAML_DIR = Path(__file__).parent.parent / "reglas" / "sectores"

def test_cargar_yaml_hosteleria():
    engine = SectorEngine(yaml_dir=YAML_DIR)
    engine.cargar("5610")
    assert engine.sector_activo == "hosteleria_restauracion"
    assert len(engine.kpis) == 7

def test_cnae_no_soportado_retorna_generico():
    engine = SectorEngine(yaml_dir=YAML_DIR)
    engine.cargar("9999")
    assert engine.sector_activo == "generico"

def test_calcular_ticket_medio():
    engine = SectorEngine(yaml_dir=YAML_DIR)
    engine.cargar("5610")
    datos = {"ventas_totales": 1840.0, "covers": 62}
    resultado = engine.calcular_kpi("ticket_medio", datos)
    assert isinstance(resultado, KPIResultado)
    assert abs(resultado.valor - 29.67) < 0.1
    assert resultado.semaforo == "verde"  # 29.67 > p50 22.0

def test_calcular_food_cost_pct_alerta():
    engine = SectorEngine(yaml_dir=YAML_DIR)
    engine.cargar("5610")
    datos = {"coste_materia_prima": 15000.0, "ventas_cocina": 35000.0}
    resultado = engine.calcular_kpi("food_cost_pct", datos)
    assert abs(resultado.valor - 42.86) < 0.1
    assert resultado.semaforo == "rojo"  # > alerta_alta 38%

def test_semaforo_verde_amarillo_rojo():
    engine = SectorEngine(yaml_dir=YAML_DIR)
    engine.cargar("5610")
    # ticket_medio: p25=16, p50=22, p75=32
    assert engine._semaforo_kpi("ticket_medio", 25.0) == "verde"   # entre p50 y p75
    assert engine._semaforo_kpi("ticket_medio", 18.0) == "amarillo"  # entre p25 y p50
    assert engine._semaforo_kpi("ticket_medio", 10.0) == "rojo"   # < p25

def test_evaluar_alerta_food_cost_spike():
    engine = SectorEngine(yaml_dir=YAML_DIR)
    engine.cargar("5610")
    alertas = engine.evaluar_alertas(empresa_id=1, metricas={
        "food_cost_pct": 40.0,
        "tendencia_7d_food_cost": 4.0,
    })
    ids = [a.alerta_id for a in alertas]
    assert "food_cost_spike" in ids

def test_sin_alerta_cuando_metricas_ok():
    engine = SectorEngine(yaml_dir=YAML_DIR)
    engine.cargar("5610")
    alertas = engine.evaluar_alertas(empresa_id=1, metricas={
        "food_cost_pct": 26.0,
        "tendencia_7d_food_cost": 1.0,
        "revpash": 22.0,
        "variacion_mom_proveedor_max": 5.0,
        "dias_sin_tpv": 0,
    })
    assert alertas == []
