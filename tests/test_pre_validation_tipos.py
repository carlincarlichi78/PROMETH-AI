"""Tests para checks de pre-validacion de tipos nuevos."""
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from sfce.phases.pre_validation import (
    _check_adeudo_ing_iva_exento,
    _check_bancario_importe,
    _check_nomina_cuadre,
    _check_nomina_irpf,
    _check_nomina_ss,
    _check_rlc_cuota,
    _check_suplido_cuenta_554,
    _check_suministro_cuadre,
    ejecutar_pre_validacion,
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


# === _check_adeudo_ing_iva_exento ===

def test_adeudo_ing_iva_cero():
    doc = {"datos_extraidos": {"metadata": {"tipo_documento": "adeudo_ing"}, "iva_porcentaje": 0}}
    assert _check_adeudo_ing_iva_exento(doc) is None


def test_adeudo_ing_iva_21():
    doc = {"datos_extraidos": {"metadata": {"tipo_documento": "adeudo_ing"}, "iva_porcentaje": 21}}
    aviso = _check_adeudo_ing_iva_exento(doc)
    assert aviso is not None
    assert "ING1" in aviso
    assert "21" in aviso


def test_adeudo_ing_tipo_distinto():
    doc = {"datos_extraidos": {"metadata": {"tipo_documento": "factura"}, "iva_porcentaje": 21}}
    assert _check_adeudo_ing_iva_exento(doc) is None


def test_adeudo_ing_sin_metadata():
    doc = {"datos_extraidos": {"iva_porcentaje": 21}}
    assert _check_adeudo_ing_iva_exento(doc) is None


# === _check_suplido_cuenta_554 ===

def _make_config(subcuenta: str):
    config = MagicMock()
    config.buscar_proveedor_por_cif.return_value = {
        "_nombre_corto": "VODAFONE",
        "subcuenta": subcuenta,
    }
    return config


def test_suplido_subcuenta_554_ok():
    doc = {"tipo": "SUM", "datos_extraidos": {"emisor_cif": "A12345678"}}
    config = _make_config("5540001")
    assert _check_suplido_cuenta_554(doc, config) is None


def test_suplido_subcuenta_621_aviso():
    doc = {"tipo": "SUM", "datos_extraidos": {"emisor_cif": "A12345678"}}
    config = _make_config("6210001")
    aviso = _check_suplido_cuenta_554(doc, config)
    assert aviso is not None
    assert "SUM1" in aviso
    assert "6210001" in aviso


def test_suplido_tipo_no_sum():
    doc = {"tipo": "FC", "datos_extraidos": {"emisor_cif": "A12345678"}}
    config = _make_config("6210001")
    assert _check_suplido_cuenta_554(doc, config) is None


def test_suplido_proveedor_no_encontrado():
    doc = {"tipo": "SUM", "datos_extraidos": {"emisor_cif": "A12345678"}}
    config = MagicMock()
    config.buscar_proveedor_por_cif.return_value = None
    assert _check_suplido_cuenta_554(doc, config) is None


# === ejecutar_pre_validacion — preautorizacion_anulada ===

def _make_intake_json(documentos: list) -> dict:
    return {"documentos": documentos, "total": len(documentos)}


def _make_config_pre_val():
    config = MagicMock()
    config.ejercicio = "2025"
    config.empresa = {"anio_ejercicio": "2025"}
    config.tolerancias = {"comparacion_importes": 0.02}
    config.tipos_cambio = {}
    config.idempresa = "2"
    config.buscar_proveedor_por_cif.return_value = None
    config.buscar_cliente_por_cif.return_value = None
    config.buscar_proveedor_por_nombre.return_value = None
    config.buscar_cliente_por_nombre.return_value = None
    config.buscar_cliente_fallback_sin_cif.return_value = None
    return config


def test_ejecutar_pre_validacion_preautorizacion_anulada_va_a_excluidos():
    doc_anulado = {
        "archivo": "ticket_preaut.pdf",
        "tipo": "FC",
        "hash_sha256": "abc123",
        "datos_extraidos": {
            "metadata": {"preautorizacion_anulada": True},
            "emisor_cif": "A12345678",
            "total": 10.0,
            "fecha": "2025-06-01",
        },
    }
    doc_normal = {
        "archivo": "factura_ok.pdf",
        "tipo": "FC",
        "hash_sha256": "def456",
        "datos_extraidos": {
            "metadata": {},
            "emisor_cif": "A12345678",
            "total": 121.0,
            "base_imponible": 100.0,
            "iva_importe": 21.0,
            "iva_porcentaje": 21,
            "fecha": "2025-06-01",
            "numero_factura": "F-001",
        },
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        ruta = Path(tmpdir)
        intake_data = _make_intake_json([doc_anulado, doc_normal])
        (ruta / "intake_results.json").write_text(
            json.dumps(intake_data), encoding="utf-8"
        )

        config = _make_config_pre_val()
        # Parchear FSAdapter y PreValidationOutput para no necesitar BD
        import unittest.mock as mock
        with mock.patch("sfce.phases.pre_validation.FSAdapter") as MockFS, \
             mock.patch("sfce.core.contracts.PreValidationOutput") as MockOut:
            MockFS.desde_config.return_value._get.return_value = []
            MockOut.validar_y_serializar.return_value = json.dumps(
                {"validados": [], "excluidos": [], "total_entrada": 0}
            )

            resultado = ejecutar_pre_validacion(config, ruta)

    excluidos = resultado.datos["excluidos"]
    validados = resultado.datos["validados"]

    archivos_excluidos = [e["archivo"] for e in excluidos]
    assert "ticket_preaut.pdf" in archivos_excluidos

    archivos_validados = [v["archivo"] for v in validados]
    assert "ticket_preaut.pdf" not in archivos_validados
