"""Tests para checks de pre-validacion de tipos nuevos."""
import pytest
from scripts.phases.pre_validation import (
    _check_nomina_cuadre,
    _check_nomina_irpf,
    _check_nomina_ss,
    _check_suministro_cuadre,
    _check_bancario_importe,
    _check_rlc_cuota,
)


def test_nomina_cuadre_ok():
    datos = {"bruto": 1800, "retenciones_irpf": 180,
             "aportaciones_ss_trabajador": 114.30, "neto": 1505.70}
    assert _check_nomina_cuadre(datos) is None


def test_nomina_cuadre_error():
    datos = {"bruto": 1800, "retenciones_irpf": 180,
             "aportaciones_ss_trabajador": 114.30, "neto": 1400}
    err = _check_nomina_cuadre(datos)
    assert err is not None
    assert "N1" in err


def test_nomina_cuadre_ceros():
    datos = {"bruto": 0, "retenciones_irpf": 0,
             "aportaciones_ss_trabajador": 0, "neto": 0}
    assert _check_nomina_cuadre(datos) is None


def test_nomina_irpf_ok():
    datos = {"bruto": 1800, "retenciones_irpf": 180, "irpf_porcentaje": 10}
    assert _check_nomina_irpf(datos) is None


def test_nomina_irpf_alto():
    datos = {"bruto": 1800, "retenciones_irpf": 900, "irpf_porcentaje": 50}
    err = _check_nomina_irpf(datos)
    assert err is not None
    assert "N2" in err


def test_nomina_irpf_negativo():
    datos = {"bruto": 1800, "retenciones_irpf": -50, "irpf_porcentaje": -3}
    err = _check_nomina_irpf(datos)
    assert err is not None
    assert "N2" in err


def test_nomina_ss_ok():
    datos = {"bruto": 1800, "aportaciones_ss_trabajador": 114.30}
    assert _check_nomina_ss(datos) is None


def test_nomina_ss_alta():
    datos = {"bruto": 1800, "aportaciones_ss_trabajador": 500}
    err = _check_nomina_ss(datos)
    assert err is not None
    assert "N3" in err


def test_suministro_cuadre_ok():
    datos = {"base_imponible": 100, "iva_importe": 21, "total": 121}
    assert _check_suministro_cuadre(datos) is None


def test_suministro_cuadre_error():
    datos = {"base_imponible": 100, "iva_importe": 21, "total": 150}
    err = _check_suministro_cuadre(datos)
    assert err is not None
    assert "S1" in err


def test_suministro_cuadre_total_cero():
    datos = {"base_imponible": 0, "iva_importe": 0, "total": 0}
    assert _check_suministro_cuadre(datos) is None


def test_bancario_importe_ok():
    datos = {"importe": 25.50}
    assert _check_bancario_importe(datos) is None


def test_bancario_importe_cero():
    datos = {"importe": 0}
    err = _check_bancario_importe(datos)
    assert err is not None
    assert "B1" in err


def test_bancario_importe_negativo():
    datos = {"importe": -10}
    err = _check_bancario_importe(datos)
    assert err is not None
    assert "B1" in err


def test_rlc_cuota_ok():
    datos = {"base_cotizacion": 7500, "cuota_empresarial": 2295}
    assert _check_rlc_cuota(datos) is None


def test_rlc_cuota_anomala_baja():
    datos = {"base_cotizacion": 7500, "cuota_empresarial": 100}
    err = _check_rlc_cuota(datos)
    assert err is not None
    assert "R1" in err


def test_rlc_cuota_cero():
    datos = {"base_cotizacion": 0, "cuota_empresarial": 0}
    assert _check_rlc_cuota(datos) is None
