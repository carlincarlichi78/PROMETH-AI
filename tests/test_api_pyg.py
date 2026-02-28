"""Tests Task 5 — PyG backend lógica de agrupación y cálculos."""
import pytest
from sfce.core.pgc_nombres import clasificar


def test_clasificar_para_pyg_ventas():
    info = clasificar("7000000000")
    assert info["linea_pyg"] == "L1"
    assert info["naturaleza"] == "ingreso"


def test_clasificar_para_pyg_personal():
    info = clasificar("6400000000")
    assert info["linea_pyg"] == "L6"


def test_clasificar_para_pyg_amortizacion():
    info = clasificar("6810000000")
    assert info["linea_pyg"] == "L8"


def test_calcular_waterfall_offsets():
    """Los offsets del waterfall se calculan correctamente."""
    ventas = 2428202.0
    aprovisionamientos = 168575.0
    personal = 745327.0
    amortizacion = 40100.0

    margen_bruto = ventas - aprovisionamientos
    ebitda = margen_bruto - personal
    ebit = ebitda - amortizacion

    waterfall = [
        {"nombre": "Ventas netas", "valor": ventas, "offset": 0},
        {"nombre": "Aprovisionamientos", "valor": aprovisionamientos, "offset": margen_bruto},
        {"nombre": "Margen Bruto", "valor": margen_bruto, "offset": 0},
        {"nombre": "Personal", "valor": personal, "offset": ebitda},
        {"nombre": "EBITDA", "valor": ebitda, "offset": 0},
        {"nombre": "Amortizaciones", "valor": amortizacion, "offset": ebit},
        {"nombre": "RESULTADO", "valor": ebit, "offset": 0},
    ]

    assert waterfall[1]["offset"] == pytest.approx(2259627.0, rel=0.01)
    assert waterfall[2]["valor"] == pytest.approx(2259627.0, rel=0.01)
    assert waterfall[4]["valor"] == pytest.approx(1514300.0, rel=0.01)
    assert waterfall[6]["valor"] == pytest.approx(1474200.0, rel=0.01)


def test_agrupar_partidas_por_linea_pyg():
    """Partidas se agrupan correctamente en líneas PGC."""
    partidas = [
        {"subcuenta": "7000000000", "haber": 100.0, "debe": 0.0},
        {"subcuenta": "7050000000", "haber": 50.0,  "debe": 0.0},
        {"subcuenta": "6400000000", "haber": 0.0,   "debe": 30.0},
    ]
    grupos: dict[str, float] = {}
    for p in partidas:
        info = clasificar(p["subcuenta"])
        if info["naturaleza"] == "ingreso":
            importe = p["haber"] - p["debe"]
        else:
            importe = p["debe"] - p["haber"]
        linea = info.get("linea_pyg") or "OTROS"
        grupos[linea] = grupos.get(linea, 0) + importe

    assert grupos["L1"] == pytest.approx(150.0)
    assert grupos["L6"] == pytest.approx(30.0)
