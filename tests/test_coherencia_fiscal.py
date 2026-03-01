"""Tests para el motor de coherencia fiscal post-OCR."""
import pytest
from sfce.core.coherencia_fiscal import verificar_coherencia_fiscal, ResultadoCoherencia


def _doc_ok() -> dict:
    return {
        "emisor_cif": "B12345678",
        "base_imponible": 100.0,
        "iva_importe": 21.0,
        "total": 121.0,
        "fecha_factura": "2025-06-15",
        "concepto": "Servicios de consultoría",
    }


# --- Bloqueos duros ---

def test_cif_invalido_genera_error_grave():
    doc = _doc_ok()
    doc["emisor_cif"] = "ZZZINVALIDO"
    resultado = verificar_coherencia_fiscal(doc)
    assert len(resultado.errores_graves) > 0
    assert resultado.score == 0


def test_suma_no_cuadra_genera_error_grave():
    doc = _doc_ok()
    doc["total"] = 999.0  # debería ser 121
    resultado = verificar_coherencia_fiscal(doc)
    assert len(resultado.errores_graves) > 0
    assert resultado.score == 0


def test_doc_correcto_no_tiene_errores_graves():
    resultado = verificar_coherencia_fiscal(_doc_ok())
    assert resultado.errores_graves == []
    assert resultado.score == 100


# --- Tolerancia suma 1% ---

def test_suma_con_tolerancia_1_pct_no_es_error_grave():
    doc = _doc_ok()
    doc["total"] = 121.0 * 1.005  # 0.5% de desviación
    resultado = verificar_coherencia_fiscal(doc)
    assert resultado.errores_graves == []


def test_suma_fuera_tolerancia_1_pct_es_error_grave():
    doc = _doc_ok()
    doc["total"] = 121.0 * 1.02  # 2% de desviación
    resultado = verificar_coherencia_fiscal(doc)
    assert len(resultado.errores_graves) > 0


# --- Alertas (penalizan score) ---

def test_total_no_positivo_genera_alerta():
    doc = _doc_ok()
    doc["base_imponible"] = -100.0
    doc["iva_importe"] = -21.0
    doc["total"] = -121.0
    resultado = verificar_coherencia_fiscal(doc)
    assert any("positivo" in a.lower() or "negativo" in a.lower() or "importe" in a.lower()
               for a in resultado.alertas)
    assert resultado.score < 100


def test_concepto_vacio_genera_alerta():
    doc = _doc_ok()
    doc["concepto"] = ""
    resultado = verificar_coherencia_fiscal(doc)
    assert any("concepto" in a.lower() for a in resultado.alertas)
    assert resultado.score < 100


def test_fecha_fuera_rango_genera_alerta():
    doc = _doc_ok()
    doc["fecha_factura"] = "2018-01-01"  # más de 5 años
    resultado = verificar_coherencia_fiscal(doc)
    assert any("fecha" in a.lower() for a in resultado.alertas)
    assert resultado.score < 100


# --- Validación CIF ---

def test_cif_espanol_nif_persona_juridica_valido():
    doc = _doc_ok()
    doc["emisor_cif"] = "A87654321"
    resultado = verificar_coherencia_fiscal(doc)
    assert resultado.errores_graves == []


def test_nif_persona_fisica_espanol_valido():
    doc = _doc_ok()
    doc["emisor_cif"] = "12345678Z"
    resultado = verificar_coherencia_fiscal(doc)
    assert resultado.errores_graves == []


def test_cif_intracomunitario_valido():
    doc = _doc_ok()
    doc["emisor_cif"] = "DE123456789"
    resultado = verificar_coherencia_fiscal(doc)
    assert resultado.errores_graves == []


def test_sin_cif_no_genera_error_grave():
    """CIF vacío genera alerta, no error grave (puede ser factura simplificada)."""
    doc = _doc_ok()
    doc["emisor_cif"] = ""
    resultado = verificar_coherencia_fiscal(doc)
    assert resultado.errores_graves == []
    assert resultado.score < 100


# --- Score acumulativo ---

def test_multiples_alertas_penalizan_mas():
    doc_una_alerta = _doc_ok()
    doc_una_alerta["concepto"] = ""

    doc_dos_alertas = _doc_ok()
    doc_dos_alertas["concepto"] = ""
    doc_dos_alertas["fecha_factura"] = "2018-01-01"

    r1 = verificar_coherencia_fiscal(doc_una_alerta)
    r2 = verificar_coherencia_fiscal(doc_dos_alertas)
    assert r2.score < r1.score
