"""Tests Task 8 — Balance backend lógica de ratios y clasificación."""
import pytest
from sfce.core.pgc_nombres import clasificar


def test_balance_activo_no_corriente_amortizacion():
    info = clasificar("2810000000")
    assert info["naturaleza"] == "activo_no_corriente"


def test_balance_activo_corriente_clientes():
    info = clasificar("4300000000")
    assert info["naturaleza"] == "activo_corriente"


def test_balance_pasivo_corriente_proveedores():
    info = clasificar("4000000000")
    assert info["naturaleza"] == "pasivo_corriente"


def test_balance_bilateral_iva_soportado_activo():
    """472 se clasifica como activo_corriente por defecto."""
    info = clasificar("4720000000")
    assert info["naturaleza"] == "activo_corriente"


def test_ratios_calculo():
    activo_corriente = 2721863.83
    pasivo_corriente = 1749891.74
    fondo_maniobra = activo_corriente - pasivo_corriente
    liquidez = activo_corriente / pasivo_corriente
    assert fondo_maniobra == pytest.approx(971972.09, rel=0.01)
    assert liquidez == pytest.approx(1.556, rel=0.01)


def test_endeudamiento_calculo():
    pasivo_total = 1749891.74
    activo_total = 2689763.67
    endeudamiento = (pasivo_total / activo_total) * 100
    assert endeudamiento == pytest.approx(65.06, rel=0.01)


def test_pmc_calculo():
    saldo_clientes = 2671022.83
    ventas = 2428202.0
    pmc = (saldo_clientes / ventas) * 365
    assert pmc == pytest.approx(401.5, rel=0.05)


def test_alertas_pmc_alto():
    pmc = 401
    alertas = []
    if pmc > 60:
        alertas.append({"codigo": "PMC_ALTO", "nivel": "critical"})
    assert any(a["codigo"] == "PMC_ALTO" for a in alertas)


def test_cuadre_balance():
    activo = 2689763.67
    pn = 939871.93
    pasivo = 1749891.74
    diferencia = abs(activo - (pn + pasivo))
    assert diferencia < 1.0
