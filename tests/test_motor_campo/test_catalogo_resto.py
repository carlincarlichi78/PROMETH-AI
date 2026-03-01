from scripts.motor_campo.catalogo.bancario import obtener_escenarios_bancario
from scripts.motor_campo.catalogo.gate0 import obtener_escenarios_gate0
from scripts.motor_campo.catalogo.api_seguridad import obtener_escenarios_api
from scripts.motor_campo.catalogo.dashboard import obtener_escenarios_dashboard


def test_bancario_5_escenarios():
    assert len(obtener_escenarios_bancario()) == 5


def test_gate0_5_escenarios():
    assert len(obtener_escenarios_gate0()) == 5


def test_api_5_escenarios():
    assert len(obtener_escenarios_api()) == 5


def test_dashboard_8_escenarios():
    assert len(obtener_escenarios_dashboard()) == 8


def test_catalogo_completo():
    total = (len(obtener_escenarios_bancario()) + len(obtener_escenarios_gate0()) +
             len(obtener_escenarios_api()) + len(obtener_escenarios_dashboard()))
    assert total == 23
