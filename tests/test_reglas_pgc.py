"""Tests para reglas PGC."""
import pytest
from sfce.core.reglas_pgc import (
    detectar_regimen_por_cif,
    validar_coherencia_cif_iva,
    validar_subcuenta_lado,
    detectar_suplido_en_linea,
    validar_tipo_irpf,
    validar_tipo_iva,
)


def test_cif_espanol_general():
    info = detectar_regimen_por_cif("B12345678")
    assert info["pais"] == "ESP"
    assert info["regimen"] == "general"
    assert 21 in info["iva_factura_validos"]


def test_cif_portugues_extracom():
    info = detectar_regimen_por_cif("PT123456789")
    assert info["pais"] == "PRT"
    assert info["regimen"] == "extracomunitario"
    assert info["iva_factura_validos"] == [0]


def test_cif_aleman_intracom():
    info = detectar_regimen_por_cif("DE123456789")
    assert info["pais"] == "DEU"
    assert info["regimen"] == "intracomunitario"


def test_coherencia_iva_portugues_con_21():
    err = validar_coherencia_cif_iva("PT123456789", 21)
    assert err is not None
    assert "no esperado" in err


def test_coherencia_iva_espanol_ok():
    err = validar_coherencia_cif_iva("B12345678", 21)
    assert err is None


def test_subcuenta_600_debe_ok():
    err = validar_subcuenta_lado("6000000000", 100.0, 0.0)
    assert err is None


def test_subcuenta_600_haber_error():
    err = validar_subcuenta_lado("6000000000", 0.0, 100.0)
    assert err is not None
    assert "DEBE" in err


def test_subcuenta_400_haber_ok():
    err = validar_subcuenta_lado("4000000000", 0.0, 100.0)
    assert err is None


def test_suplido_iva_aduana():
    match = detectar_suplido_en_linea("IVA ADUANA IMPORTACION")
    assert match is not None
    assert match["subcuenta"] == "4709000000"


def test_suplido_no_matchea():
    match = detectar_suplido_en_linea("TRANSPORTE TERRESTRE")
    assert match is None


def test_irpf_15_valido():
    assert validar_tipo_irpf(15) is None


def test_irpf_18_invalido():
    err = validar_tipo_irpf(18)
    assert err is not None


def test_iva_21_valido():
    assert validar_tipo_iva(21) is None


def test_iva_19_invalido():
    err = validar_tipo_iva(19)
    assert err is not None
