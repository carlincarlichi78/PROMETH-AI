from unittest.mock import patch
from scripts.motor_campo.executor_playwright import ExecutorPlaywright
from scripts.motor_campo.modelos import ResultadoEjecucion


@patch("scripts.motor_campo.executor_playwright.asyncio.run")
def test_ejecutar_playwright_retorna_resultado(mock_run):
    mock_run.return_value = ResultadoEjecucion(
        escenario_id="test_crear_gestoria", variante_id="playwright",
        canal="playwright", resultado="ok", duracion_ms=8000,
    )
    ep = ExecutorPlaywright(base_url="http://app", headless=True)
    resultado = ep.ejecutar("test_crear_gestoria")
    assert isinstance(resultado, ResultadoEjecucion)
    assert resultado.canal == "playwright"
    assert resultado.resultado == "ok"


def test_escenario_inexistente_retorna_error():
    ep = ExecutorPlaywright(base_url="http://app", headless=True)
    resultado = ep.ejecutar("escenario_que_no_existe_xyz")
    assert resultado.resultado == "error_sistema"
    assert "no registrado" in resultado.detalles.get("error", "")
