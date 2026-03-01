import pytest
from pathlib import Path
from sfce.phases.parsers.parser_tpv import ParserTPV, DatosCaja

FIXTURE = Path(__file__).parent / "fixtures" / "tpv_almuerzo.txt"


@pytest.fixture
def texto_ocr():
    return FIXTURE.read_text(encoding="utf-8")


def test_parsear_covers(texto_ocr):
    resultado = ParserTPV().parsear(texto_ocr)
    assert isinstance(resultado, DatosCaja)
    assert resultado.covers == 62


def test_parsear_ventas_totales(texto_ocr):
    resultado = ParserTPV().parsear(texto_ocr)
    assert abs(resultado.ventas_totales - 1840.0) < 0.1


def test_parsear_servicio_almuerzo(texto_ocr):
    resultado = ParserTPV().parsear(texto_ocr)
    assert resultado.servicio == "almuerzo"


def test_parsear_desglose_familias(texto_ocr):
    resultado = ParserTPV().parsear(texto_ocr)
    assert abs(resultado.desglose_familias.get("comida", 0) - 1120.0) < 0.1
    assert abs(resultado.desglose_familias.get("bebida", 0) - 580.0) < 0.1
    assert abs(resultado.desglose_familias.get("postre", 0) - 140.0) < 0.1


def test_parsear_productos(texto_ocr):
    resultado = ParserTPV().parsear(texto_ocr)
    assert len(resultado.productos) == 5
    paella = next((p for p in resultado.productos if "paella" in p["nombre"].lower()), None)
    assert paella is not None
    assert paella["qty"] == 18
    assert abs(paella["total"] - 261.0) < 0.1


def test_parsear_metodos_pago(texto_ocr):
    resultado = ParserTPV().parsear(texto_ocr)
    assert abs(resultado.metodo_pago_tarjeta - 1540.0) < 0.1
    assert abs(resultado.metodo_pago_efectivo - 300.0) < 0.1


def test_texto_vacio_retorna_none():
    resultado = ParserTPV().parsear("")
    assert resultado is None
