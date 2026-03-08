"""Tests FASE 2: nuevas señales de identificación en _match_proveedor_multi_signal."""
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from sfce.phases.intake import _match_proveedor_multi_signal


def _make_config(proveedores: dict) -> MagicMock:
    """Crea un ConfigCliente mock con los proveedores indicados."""
    config = MagicMock()
    config.proveedores = proveedores
    config.cif = "A00000000"
    # buscar_proveedor_por_cif y buscar_proveedor_por_nombre sin match por defecto
    config.buscar_proveedor_por_cif.return_value = None
    config.buscar_proveedor_por_nombre.return_value = None
    return config


def test_match_por_iban():
    """IBAN exacto en senales_identificacion debe sumar +60."""
    iban = "ES2101820000120201631223"
    config = _make_config({
        "banco_uralde": {
            "cif": "A12345678",
            "nombre_fs": "BANCO URALDE",
            "iban": iban,
        }
    })
    datos_gpt = {
        "emisor_cif": None,
        "emisor_nombre": None,
        "senales_identificacion": {"iban": iban, "telefono": None,
                                   "direccion_fragmento": None,
                                   "numero_comercio": None,
                                   "tipo_doc_inferido": None},
    }
    result = _match_proveedor_multi_signal(datos_gpt, config, texto_raw="", nombre_archivo="")
    assert result is not None
    assert result["proveedor_key"] == "banco_uralde"
    assert result["match_score"] >= 60


def test_match_por_numero_comercio():
    """Número de comercio exacto debe sumar +50."""
    num = "123456789"
    config = _make_config({
        "tpv_tienda": {
            "cif": "B87654321",
            "nombre_fs": "TIENDA TPV",
            "numero_comercio": num,
        }
    })
    datos_gpt = {
        "emisor_cif": None,
        "emisor_nombre": None,
        "senales_identificacion": {"iban": None, "telefono": None,
                                   "direccion_fragmento": None,
                                   "numero_comercio": num,
                                   "tipo_doc_inferido": None},
    }
    result = _match_proveedor_multi_signal(datos_gpt, config, texto_raw="", nombre_archivo="")
    assert result is not None
    assert result["proveedor_key"] == "tpv_tienda"
    assert result["match_score"] >= 50


def test_match_por_telefono():
    """Teléfono exacto debe sumar +35."""
    tel = "+34911234567"
    config = _make_config({
        "proveedor_tel": {
            "cif": "C11111111",
            "nombre_fs": "PROVEEDOR TEL",
            "telefono": tel,
        }
    })
    datos_gpt = {
        "emisor_cif": None,
        "emisor_nombre": None,
        "senales_identificacion": {"iban": None, "telefono": tel,
                                   "direccion_fragmento": None,
                                   "numero_comercio": None,
                                   "tipo_doc_inferido": None},
    }
    result = _match_proveedor_multi_signal(datos_gpt, config, texto_raw="", nombre_archivo="")
    assert result is not None
    assert result["proveedor_key"] == "proveedor_tel"
    assert result["match_score"] >= 35


def test_no_match_score_bajo():
    """Señales que no coinciden con ningún proveedor → resultado None."""
    config = _make_config({
        "otro_proveedor": {
            "cif": "D22222222",
            "nombre_fs": "OTRO",
            "iban": "ES9999999999999999999999",
            "telefono": "+34900000000",
            "numero_comercio": "000000000",
        }
    })
    datos_gpt = {
        "emisor_cif": None,
        "emisor_nombre": None,
        "senales_identificacion": {"iban": "ES1111111111111111111111",
                                   "telefono": "+34666000001",
                                   "direccion_fragmento": None,
                                   "numero_comercio": "111111111",
                                   "tipo_doc_inferido": None},
    }
    result = _match_proveedor_multi_signal(datos_gpt, config, texto_raw="", nombre_archivo="")
    assert result is None
