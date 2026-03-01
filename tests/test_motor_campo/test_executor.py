import pytest
from unittest.mock import patch, MagicMock
from scripts.motor_campo.executor import Executor
from scripts.motor_campo.modelos import VarianteEjecucion, ResultadoEsperado

@pytest.fixture
def executor():
    return Executor(
        sfce_api_url="http://localhost:8000",
        fs_api_url="http://localhost/api/3",
        fs_token="TEST",
        empresa_id=3,
        codejercicio="0003"
    )

def test_executor_inicializa(executor):
    assert executor.empresa_id == 3

def test_ejecutar_variante_pipeline_llama_ejecutar_pipeline(executor):
    variante = VarianteEjecucion(
        escenario_id="fc_basica", variante_id="v001",
        datos_extraidos={"tipo": "FC", "base_imponible": 1000.0, "iva_porcentaje": 21,
                         "total": 1210.0, "fecha": "2025-06-15", "emisor_cif": "A11111111",
                         "numero_factura": "TEST-001", "coddivisa": "EUR"},
        resultado_esperado=ResultadoEsperado()
    )
    with patch.object(executor, '_ejecutar_pipeline', return_value={"ok": True, "idfactura": 99}) as mock_p:
        resultado = executor.ejecutar(variante)
    mock_p.assert_called_once()
    assert resultado["escenario_id"] == "fc_basica"

def test_ejecutar_variante_api_llama_endpoint(executor):
    variante = VarianteEjecucion(
        escenario_id="api_login", variante_id="v001",
        datos_extraidos={"tipo": "_API", "endpoint": "/api/auth/login",
                         "method": "POST", "body": {"username": "admin@sfce.local", "password": "admin"}},
        resultado_esperado=ResultadoEsperado(http_status=200)
    )
    executor._jwt_token = "token_preinyectado"
    with patch("requests.request") as mock_req:
        mock_req.return_value = MagicMock(status_code=200,
                                           json=lambda: {"access_token": "x"},
                                           headers={"content-type": "application/json"})
        resultado = executor.ejecutar(variante)
    assert resultado["http_status"] == 200

def test_ejecutar_excepcion_capturada(executor):
    variante = VarianteEjecucion(
        escenario_id="fc_basica", variante_id="v001",
        datos_extraidos={"tipo": "FC"},
        resultado_esperado=ResultadoEsperado()
    )
    with patch.object(executor, '_ejecutar_pipeline', side_effect=ConnectionError("sin servidor")):
        resultado = executor.ejecutar(variante)
    assert resultado["ok"] is False
    assert "error" in resultado
