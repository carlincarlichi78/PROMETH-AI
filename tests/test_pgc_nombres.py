"""Tests Task 1: módulo pgc_nombres — diccionario PGC 2007."""
import pytest
from sfce.core.pgc_nombres import obtener_nombre, clasificar, GRUPOS


def test_obtener_nombre_exacto():
    assert obtener_nombre("7000000000") == "Ventas de mercaderías"


def test_obtener_nombre_por_prefijo_subgrupo():
    assert obtener_nombre("6400000000") == "Sueldos y salarios"


def test_obtener_nombre_fallback_grupo():
    # cuenta de grupo 6 sin match específico → nombre del grupo
    assert "Compras" in obtener_nombre("6990000000") or obtener_nombre("6990000000") != "6990000000"


def test_obtener_nombre_desconocido():
    # cuenta inexistente → devuelve el código formateado
    assert obtener_nombre("9999999999") == "9999999999"


def test_clasificar_ingreso():
    info = clasificar("7000000000")
    assert info["naturaleza"] == "ingreso"
    assert info["nombre"] == "Ventas de mercaderías"


def test_clasificar_gasto_personal():
    info = clasificar("6400000000")
    assert info["naturaleza"] == "gasto"
    assert info["linea_pyg"] == "L6"


def test_clasificar_activo_corriente():
    info = clasificar("4300000000")  # clientes
    assert info["naturaleza"] == "activo_corriente"


def test_clasificar_pasivo_corriente():
    info = clasificar("4000000000")  # proveedores
    assert info["naturaleza"] == "pasivo_corriente"


def test_clasificar_patrimonio():
    info = clasificar("1000000000")  # capital
    assert info["naturaleza"] == "patrimonio"


def test_clasificar_activo_no_corriente():
    info = clasificar("2110000000")  # construcciones
    assert info["naturaleza"] == "activo_no_corriente"


def test_grupos_completo():
    assert len(GRUPOS) == 9
    assert GRUPOS["1"]["nombre"] == "Financiación básica"
    assert GRUPOS["7"]["nombre"] == "Ventas e ingresos"


def test_linea_pyg_aprovisionamientos():
    info = clasificar("6000000000")  # compras mercaderías
    assert info["linea_pyg"] == "L4"


def test_linea_pyg_amortizacion():
    info = clasificar("6810000000")  # amortización inmovilizado material
    assert info["linea_pyg"] == "L8"
