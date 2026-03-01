import pytest
from scripts.motor_campo.validator import Validator
from scripts.motor_campo.modelos import ResultadoEsperado


@pytest.fixture
def validator():
    return Validator(sfce_api_url="http://localhost:8000", empresa_id=3)


def test_http_status_correcto(validator):
    resultado_ejecucion = {"http_status": 200, "response": {}}
    esperado = ResultadoEsperado(http_status=200)
    errores = validator.validar(resultado_ejecucion, esperado)
    assert not any(e["tipo"] == "http_status" for e in errores)


def test_http_status_incorrecto(validator):
    resultado_ejecucion = {"http_status": 422, "response": {"detail": "error"}}
    esperado = ResultadoEsperado(http_status=200)
    errores = validator.validar(resultado_ejecucion, esperado)
    assert any(e["tipo"] == "http_status" for e in errores)


def test_debe_haber_cuadrado(validator):
    resultado = {"http_status": 200, "response": {},
                 "asiento": {"partidas": [
                     {"debe": 1000.0, "haber": 0.0},
                     {"debe": 210.0, "haber": 0.0},
                     {"debe": 0.0, "haber": 1210.0},
                 ]}}
    esperado = ResultadoEsperado(debe_igual_haber=True)
    errores = validator.validar(resultado, esperado)
    assert not any(e["tipo"] == "cuadre" for e in errores)


def test_debe_haber_descuadrado(validator):
    resultado = {"http_status": 200, "response": {},
                 "asiento": {"partidas": [
                     {"debe": 1000.0, "haber": 0.0},
                     {"debe": 0.0, "haber": 500.0},
                 ]}}
    esperado = ResultadoEsperado(debe_igual_haber=True)
    errores = validator.validar(resultado, esperado)
    assert any(e["tipo"] == "cuadre" for e in errores)
