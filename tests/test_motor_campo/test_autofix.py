import pytest
from unittest.mock import patch, MagicMock
from scripts.motor_campo.autofix import AutoFix


@pytest.fixture
def autofix():
    return AutoFix(fs_api_url="http://localhost/api/3", fs_token="TEST")


def test_reconoce_error_cuadre(autofix):
    error = {"tipo": "cuadre", "descripcion": "DEBE 0.00 != HABER 1210.00",
             "datos": {"debe": 0.0, "haber": 1210.0}}
    assert autofix.puede_arreglar(error) is True


def test_no_puede_arreglar_error_desconocido(autofix):
    error = {"tipo": "desconocido_xyzabc", "descripcion": "algo raro", "datos": {}}
    assert autofix.puede_arreglar(error) is False


def test_fix_http_401_no_intentado(autofix):
    error = {"tipo": "http_status", "descripcion": "HTTP 401 != esperado 200", "datos": {}}
    ok, desc = autofix.intentar_fix(error, contexto={})
    assert ok is False
    assert "401" in desc
