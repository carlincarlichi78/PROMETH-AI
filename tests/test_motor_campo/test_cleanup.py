import pytest
from unittest.mock import patch, MagicMock
from scripts.motor_campo.cleanup import Cleanup

@pytest.fixture
def cleanup():
    return Cleanup(fs_base_url="http://localhost/api/3", fs_token="TEST", empresa_id=3)

def test_cleanup_vacio_no_falla(cleanup):
    cleanup.limpiar_escenario([])

def test_registrar_factura(cleanup):
    cleanup.registrar_factura("FC", 9999)
    assert ("FC", 9999) in cleanup._pendientes

def test_registrar_asiento(cleanup):
    cleanup.registrar_asiento(8888)
    assert 8888 in cleanup._asientos_pendientes

def test_limpiar_llama_delete(cleanup):
    cleanup.registrar_factura("FC", 100)
    cleanup.registrar_asiento(200)
    with patch("requests.delete") as mock_del:
        mock_del.return_value = MagicMock(status_code=200)
        cleanup.limpiar_escenario([])
    assert mock_del.call_count >= 1
