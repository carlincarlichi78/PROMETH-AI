from unittest.mock import patch, MagicMock
from scripts.motor_campo.modelos import VarianteEjecucion, ResultadoEsperado, ResultadoEjecucion
from scripts.motor_campo.executor import Executor


def _variante_fc():
    return VarianteEjecucion(
        escenario_id="fc_basica", variante_id="test",
        datos_extraidos={"tipo": "FC", "base_imponible": 1000.0, "iva_porcentaje": 21, "total": 1210.0},
        resultado_esperado=ResultadoEsperado(http_status=200),
    )


@patch("scripts.motor_campo.executor.requests.post")
def test_ejecutar_retorna_resultado_ejecucion(mock_post):
    login_resp = MagicMock(); login_resp.json.return_value = {"access_token": "tok"}; login_resp.raise_for_status = lambda: None
    pipeline_resp = MagicMock()
    pipeline_resp.status_code = 200
    pipeline_resp.headers = {"content-type": "application/json"}
    pipeline_resp.json.return_value = {
        "doc": {"idfactura": 55, "idasiento": 33},
        "estado": "procesado", "tipo_doc": "FC",
    }
    mock_post.side_effect = [login_resp, pipeline_resp]

    ex = Executor("http://api", "http://fs", "token123", empresa_id=3, codejercicio="0003")
    resultado = ex.ejecutar(_variante_fc())

    assert isinstance(resultado, ResultadoEjecucion)
    assert resultado.canal == "http"
    assert resultado.detalles.get("idfactura") == 55
    assert resultado.detalles.get("idasiento") == 33


@patch("scripts.motor_campo.executor.requests.post")
def test_ejecutar_error_retorna_error_sistema(mock_post):
    login_resp = MagicMock(); login_resp.json.return_value = {"access_token": "tok"}; login_resp.raise_for_status = lambda: None
    mock_post.side_effect = [login_resp, Exception("timeout")]

    ex = Executor("http://api", "http://fs", "token123", empresa_id=3, codejercicio="0003")
    resultado = ex.ejecutar(_variante_fc())

    assert resultado.resultado == "error_sistema"
    assert "timeout" in resultado.detalles.get("error", "")
