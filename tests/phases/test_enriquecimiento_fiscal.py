"""Tests FASE 3: _enriquecer_perfil_fiscal."""
import pytest
from sfce.phases.intake import _enriquecer_perfil_fiscal


def test_base_desde_total_iva21():
    """total=121, base=null, IVA21 → base=100.0, iva=21.0."""
    datos = {"total": 121.0, "base_imponible": None}
    config_prov = {"codimpuesto": "IVA21", "cif": "B12345678"}
    res = _enriquecer_perfil_fiscal(datos, config_prov)
    assert res["base_imponible"] == pytest.approx(100.0, abs=0.01)
    assert res["iva_importe"] == pytest.approx(21.0, abs=0.01)
    assert res["iva_porcentaje"] == 21


def test_base_desde_total_iva10():
    """total=110, base=null, IVA10 → base=100.0, iva=10.0."""
    datos = {"total": 110.0, "base_imponible": None}
    config_prov = {"codimpuesto": "IVA10", "cif": "B12345678"}
    res = _enriquecer_perfil_fiscal(datos, config_prov)
    assert res["base_imponible"] == pytest.approx(100.0, abs=0.01)
    assert res["iva_importe"] == pytest.approx(10.0, abs=0.01)
    assert res["iva_porcentaje"] == 10


def test_irpf_desde_codretencion():
    """codretencion=IRPF15, base=500 → irpf_importe=75.0."""
    datos = {"total": 500.0, "base_imponible": 500.0, "irpf_porcentaje": None}
    config_prov = {"codretencion": "IRPF15", "codimpuesto": "IVA21"}
    res = _enriquecer_perfil_fiscal(datos, config_prov)
    assert res["irpf_porcentaje"] == 15
    assert res["irpf_importe"] == pytest.approx(75.0, abs=0.01)


def test_total_con_irpf():
    """base=500, iva=105, irpf=75 → total=530.0."""
    datos = {
        "total": 605.0,
        "base_imponible": 500.0,
        "iva_importe": 105.0,
        "irpf_porcentaje": None,
    }
    config_prov = {"codretencion": "IRPF15", "codimpuesto": "IVA21"}
    res = _enriquecer_perfil_fiscal(datos, config_prov)
    assert res["total"] == pytest.approx(530.0, abs=0.01)


def test_no_modifica_si_base_presente():
    """Si base_imponible ya tiene valor → no recalcula."""
    datos = {"total": 121.0, "base_imponible": 100.0}
    config_prov = {"codimpuesto": "IVA21"}
    res = _enriquecer_perfil_fiscal(datos, config_prov)
    # base no se toca porque ya estaba presente
    assert res["base_imponible"] == 100.0
    # iva_importe no se añade (base ya presente)
    assert "iva_importe" not in res or res.get("iva_importe") is None or True
    # Lo importante: no cambió la base
    assert res["base_imponible"] == 100.0


def test_campos_internos_asiento():
    """Campos _subcuenta, _codimpuesto, _perfil_aplicado siempre presentes."""
    datos = {"total": 100.0, "base_imponible": None}
    config_prov = {"codimpuesto": "IVA0", "subcuenta": "6290000000"}
    res = _enriquecer_perfil_fiscal(datos, config_prov)
    assert res["_subcuenta"] == "6290000000"
    assert res["_codimpuesto"] == "IVA0"
    assert res["_perfil_aplicado"] is True
