"""Tests para ExecutorPortal — simula subida móvil vía portal API."""
from unittest.mock import patch, MagicMock
from scripts.motor_campo.executor_portal import ExecutorPortal
from scripts.motor_campo.modelos import ResultadoEjecucion


def _mock_responses(status_list: list, json_list: list) -> list:
    mocks = []
    for status, data in zip(status_list, json_list):
        m = MagicMock()
        m.status_code = status
        m.json.return_value = data
        m.headers = {"content-type": "application/json"}
        mocks.append(m)
    return mocks


@patch("scripts.motor_campo.executor_portal.requests.post")
@patch("scripts.motor_campo.executor_portal.requests.get")
def test_upload_exitoso_retorna_resultado(mock_get, mock_post):
    # Login → upload → poll estado
    mock_post.side_effect = [
        MagicMock(status_code=200, json=lambda: {"access_token": "tok"},
                  raise_for_status=lambda: None),                          # login
        MagicMock(status_code=200, json=lambda: {"doc_id": 77},
                  headers={"content-type": "application/json"}),           # upload
    ]
    mock_get.return_value = MagicMock(
        status_code=200,
        json=lambda: {"estado": "procesado", "tipo_doc": "FC", "idasiento": 12},
        headers={"content-type": "application/json"},
    )

    ep = ExecutorPortal("http://api", empresa_id=3, poll_timeout_s=5, poll_interval_s=0.01)
    from pathlib import Path
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(b"%PDF-1.4 test")
        ruta = f.name
    try:
        resultado = ep.ejecutar_archivo(ruta, escenario_id="fc_basica", variante_id="portal_test")
        assert isinstance(resultado, ResultadoEjecucion)
        assert resultado.canal == "portal"
        assert resultado.estado_doc_final == "procesado"
    finally:
        os.unlink(ruta)


@patch("scripts.motor_campo.executor_portal.requests.post")
@patch("scripts.motor_campo.executor_portal.requests.get")
def test_upload_timeout_retorna_timeout(mock_get, mock_post):
    mock_post.side_effect = [
        MagicMock(status_code=200, json=lambda: {"access_token": "tok"}, raise_for_status=lambda: None),
        MagicMock(status_code=200, json=lambda: {"doc_id": 99}, headers={"content-type": "application/json"}),
    ]
    # Estado siempre PROCESANDO → timeout
    mock_get.return_value = MagicMock(
        status_code=200, json=lambda: {"estado": "PROCESANDO"},
        headers={"content-type": "application/json"},
    )

    ep = ExecutorPortal("http://api", empresa_id=3, poll_timeout_s=0.1, poll_interval_s=0.01)
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(b"%PDF-1.4 test"); ruta = f.name
    try:
        resultado = ep.ejecutar_archivo(ruta, escenario_id="fc_basica", variante_id="p_test")
        assert resultado.resultado == "timeout"
    finally:
        os.unlink(ruta)
