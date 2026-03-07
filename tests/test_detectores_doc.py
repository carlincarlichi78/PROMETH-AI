"""Tests del detector de tipo documental para adeudos bancarios ING."""
import pytest
from sfce.core.detectores_doc import (
    detectar_tipo_adeudo_ing,
    extraer_emisor_adeudo_ing,
    procesar_adeudo_ing,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TEXTO_ADEUDO_ING_ICAM = """Adeudo recibido
ING Bank NV
Entidad emisora
ILUSTRE COLEGIO DE ABOGADOS DE MALAGA
Fecha operación
28/01/2025
Importe euros
107,18
Referencia
DEU20250113502571941
Información adicional
CUOTA 1 TRIM 2025 BASE EXENTA:107,18EUR IVA:0,00EUR"""

TEXTO_ADEUDO_ING_MUTUALIDAD = """Adeudo recibido
ING
Entidad emisora
MUTUALIDAD ABOGACIA C. GENERAL-RECIBOS
Fecha operación
05/02/2025
Importe euros
183,22
Referencia
DEU20250205123456789
Información adicional
RECIBO MUTUALIDAD FEBRERO 2025"""

TEXTO_FACTURA_NORMAL = """Factura simplificada
Dropbox International
Total: 11,99 EUR
IVA: 2,52 EUR"""

TEXTO_FACTURA_AVATEL = """AVATEL TELECOM SA
CIF A93135218
Factura 2025-01-001
Base imponible: 49,58 EUR
IVA 21%: 10,41 EUR
Total: 59,99 EUR"""


# ---------------------------------------------------------------------------
# detectar_tipo_adeudo_ing
# ---------------------------------------------------------------------------

def test_detectar_adeudo_ing_positivo_icam():
    assert detectar_tipo_adeudo_ing(TEXTO_ADEUDO_ING_ICAM) is True


def test_detectar_adeudo_ing_positivo_mutualidad():
    assert detectar_tipo_adeudo_ing(TEXTO_ADEUDO_ING_MUTUALIDAD) is True


def test_detectar_adeudo_ing_negativo_factura_dropbox():
    assert detectar_tipo_adeudo_ing(TEXTO_FACTURA_NORMAL) is False


def test_detectar_adeudo_ing_negativo_factura_avatel():
    assert detectar_tipo_adeudo_ing(TEXTO_FACTURA_AVATEL) is False


def test_detectar_adeudo_ing_negativo_texto_vacio():
    assert detectar_tipo_adeudo_ing("") is False


def test_detectar_adeudo_ing_case_insensitive():
    texto = "ADEUDO RECIBIDO\nING BANK\nENTIDAD EMISORA\nProveedor X"
    assert detectar_tipo_adeudo_ing(texto) is True


# ---------------------------------------------------------------------------
# extraer_emisor_adeudo_ing
# ---------------------------------------------------------------------------

def test_extraer_emisor_adeudo_ing_nombre():
    resultado = extraer_emisor_adeudo_ing(TEXTO_ADEUDO_ING_ICAM)
    assert resultado["emisor_nombre"] == "ILUSTRE COLEGIO DE ABOGADOS DE MALAGA"


def test_extraer_emisor_adeudo_ing_importe():
    resultado = extraer_emisor_adeudo_ing(TEXTO_ADEUDO_ING_ICAM)
    assert resultado["total"] == 107.18


def test_extraer_emisor_adeudo_ing_fecha():
    resultado = extraer_emisor_adeudo_ing(TEXTO_ADEUDO_ING_ICAM)
    assert resultado["fecha"] == "2025-01-28"


def test_extraer_emisor_adeudo_ing_referencia():
    resultado = extraer_emisor_adeudo_ing(TEXTO_ADEUDO_ING_ICAM)
    assert resultado["numero_factura"] == "DEU20250113502571941"


def test_extraer_emisor_adeudo_ing_info_adicional():
    resultado = extraer_emisor_adeudo_ing(TEXTO_ADEUDO_ING_ICAM)
    assert "CUOTA 1 TRIM 2025" in resultado["info_adicional"]


def test_extraer_emisor_adeudo_ing_fuente():
    resultado = extraer_emisor_adeudo_ing(TEXTO_ADEUDO_ING_ICAM)
    assert resultado["_fuente"] == "detector_adeudo_ing"
    assert resultado["_tipo_doc_detectado"] == "adeudo_bancario_ing"


def test_extraer_emisor_adeudo_ing_mutualidad():
    resultado = extraer_emisor_adeudo_ing(TEXTO_ADEUDO_ING_MUTUALIDAD)
    assert resultado["emisor_nombre"] == "MUTUALIDAD ABOGACIA C. GENERAL-RECIBOS"
    assert resultado["total"] == 183.22


def test_extraer_emisor_adeudo_ing_campos_none_si_ausentes():
    texto = "Adeudo recibido\nING\nEntidad emisora\nProveedor X"
    resultado = extraer_emisor_adeudo_ing(texto)
    assert resultado["emisor_nombre"] == "Proveedor X"
    assert resultado["total"] is None
    assert resultado["fecha"] is None
    assert resultado["numero_factura"] is None


# ---------------------------------------------------------------------------
# procesar_adeudo_ing (integración)
# ---------------------------------------------------------------------------

def test_procesar_adeudo_ing_retorna_dict_si_es_adeudo():
    resultado = procesar_adeudo_ing(TEXTO_ADEUDO_ING_ICAM)
    assert resultado is not None
    assert resultado["emisor_nombre"] == "ILUSTRE COLEGIO DE ABOGADOS DE MALAGA"


def test_procesar_adeudo_ing_retorna_none_si_no_es_adeudo():
    assert procesar_adeudo_ing(TEXTO_FACTURA_NORMAL) is None


def test_procesar_adeudo_ing_retorna_none_si_texto_vacio():
    assert procesar_adeudo_ing("") is None
