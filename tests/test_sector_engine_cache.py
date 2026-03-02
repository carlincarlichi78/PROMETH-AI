"""Tests para la caché de SectorEngine (obtener_sector_engine)."""
import pytest
from pathlib import Path
import tempfile
import yaml


@pytest.fixture
def yaml_dir_tmp(tmp_path):
    """Directorio temporal con un YAML de sector de prueba."""
    datos = {
        "sector": "hosteleria_test",
        "cnae": ["5610"],
        "kpis": {
            "ticket_medio": {
                "nombre": "Ticket medio",
                "formula": "ticket_medio",
                "unidad": "€",
                "benchmarks": {"p25": 10.0, "p50": 20.0, "p75": 30.0},
            }
        },
        "alertas": [],
    }
    (tmp_path / "hosteleria_test.yaml").write_text(yaml.dump(datos), encoding="utf-8")
    return tmp_path


def test_misma_instancia_para_mismo_cnae(yaml_dir_tmp):
    """Dos llamadas con el mismo CNAE devuelven la misma instancia en caché."""
    from sfce.analytics.sector_engine import obtener_sector_engine, _CACHE
    _CACHE.clear()

    e1 = obtener_sector_engine("5610", yaml_dir_tmp)
    e2 = obtener_sector_engine("5610", yaml_dir_tmp)
    assert e1 is e2


def test_distinta_instancia_para_distinto_cnae(yaml_dir_tmp):
    """CNAE diferentes → instancias diferentes (sector_activo puede diferir)."""
    from sfce.analytics.sector_engine import obtener_sector_engine, _CACHE
    _CACHE.clear()

    e1 = obtener_sector_engine("5610", yaml_dir_tmp)
    e2 = obtener_sector_engine("9999", yaml_dir_tmp)  # CNAE sin YAML → generico
    assert e1 is not e2


def test_cnae_sin_yaml_devuelve_generico(yaml_dir_tmp):
    """CNAE sin YAML de sector → SectorEngine con sector_activo='generico'."""
    from sfce.analytics.sector_engine import obtener_sector_engine, _CACHE
    _CACHE.clear()

    engine = obtener_sector_engine("0001", yaml_dir_tmp)
    assert engine.sector_activo == "generico"
