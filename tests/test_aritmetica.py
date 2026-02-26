"""Tests para checks aritmeticos."""
import pytest
from scripts.core.aritmetica import (
    check_cuadre_linea,
    check_suma_lineas,
    check_base_por_iva,
    check_iva_legal,
    ejecutar_checks_aritmeticos,
)


def test_cuadre_linea_ok():
    assert check_cuadre_linea(100, 21, 121) is None

def test_cuadre_linea_error():
    err = check_cuadre_linea(100, 21, 125)
    assert err is not None

def test_suma_lineas_ok():
    lineas = [{"pvptotal": 121}, {"pvptotal": 242}]
    assert check_suma_lineas(lineas, 363) is None

def test_suma_lineas_error():
    lineas = [{"pvptotal": 121}, {"pvptotal": 242}]
    err = check_suma_lineas(lineas, 400)
    assert err is not None

def test_iva_21_legal():
    assert check_iva_legal(21) is None

def test_iva_19_ilegal():
    assert check_iva_legal(19) is not None

def test_ejecutar_checks_doc_correcto():
    doc = {
        "tipo": "FC",
        "datos_extraidos": {
            "base_imponible": 100, "iva_porcentaje": 21,
            "iva_importe": 21, "total": 121,
            "irpf_porcentaje": 0, "irpf_importe": 0,
            "lineas": [{"base_imponible": 100, "iva": 21, "pvptotal": 121}]
        }
    }
    avisos = ejecutar_checks_aritmeticos(doc)
    assert len(avisos) == 0
