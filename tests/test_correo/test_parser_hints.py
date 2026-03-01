"""Tests para parser_hints — extracción de [tipo:FV] [nota:...] del asunto."""
import pytest
from sfce.conectores.correo.parser_hints import extraer_hints_asunto, HintsEmail


def test_tipo_fv_en_asunto():
    hints = extraer_hints_asunto("[tipo:FV] Factura enero")
    assert hints.tipo_doc == "FV"


def test_nota_en_asunto():
    hints = extraer_hints_asunto("[tipo:FC] [nota:pagada el 15]")
    assert hints.nota == "pagada el 15"


def test_asunto_sin_hints():
    hints = extraer_hints_asunto("Factura de Mercadona enero 2025")
    assert hints.tipo_doc is None
    assert hints.nota is None


def test_hints_case_insensitive():
    hints = extraer_hints_asunto("[TIPO:fv] Factura")
    assert hints.tipo_doc == "FV"


def test_subcuenta_hint():
    hints = extraer_hints_asunto("[subcuenta:6280] alquiler oficina")
    assert hints.subcuenta == "6280"


def test_multiple_hints():
    hints = extraer_hints_asunto("[tipo:FV][subcuenta:6000][nota:urgent]")
    assert hints.tipo_doc == "FV"
    assert hints.subcuenta == "6000"
    assert hints.nota == "urgent"


def test_tipo_invalido_ignorado():
    hints = extraer_hints_asunto("[tipo:SPAM] mensaje")
    assert hints.tipo_doc is None


def test_pagada_flag():
    hints = extraer_hints_asunto("[tipo:FV][pagada:si]")
    assert hints.pagada is True


def test_pagada_false_por_defecto():
    hints = extraer_hints_asunto("[tipo:FV]")
    assert hints.pagada is False


def test_ejercicio_hint():
    hints = extraer_hints_asunto("[tipo:FV][ejercicio:2025]")
    assert hints.ejercicio == "2025"


def test_asunto_vacio():
    hints = extraer_hints_asunto("")
    assert hints.tipo_doc is None
    assert hints.nota is None
    assert hints.subcuenta is None
