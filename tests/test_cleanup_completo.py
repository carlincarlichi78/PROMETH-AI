from unittest.mock import patch, MagicMock, call
from scripts.motor_campo.cleanup_completo import CleanupCompleto


def test_limpiar_facturascripts_llama_delete():
    with patch("scripts.motor_campo.cleanup_completo.requests.delete") as mock_del:
        mock_del.return_value = MagicMock(status_code=204)
        c = CleanupCompleto("http://fs", "token", 3, "http://api", "jwt")
        c.limpiar_facturascripts([("FC", 10), ("FV", 20)])
        assert mock_del.call_count == 2
        urls = [call_args[0][0] for call_args in mock_del.call_args_list]
        assert any("facturaclientes/10" in u for u in urls)
        assert any("facturaproveedores/20" in u for u in urls)


def test_limpiar_bd_ejecuta_sql_en_orden(tmp_path):
    mock_session = MagicMock()
    c = CleanupCompleto("http://fs", "token", 3, "http://api", "jwt")
    c.limpiar_bd(mock_session)
    # Debe ejecutar al menos 8 DELETE statements
    assert mock_session.execute.call_count >= 8
    # El primero debe ser cola_procesamiento
    primera_sql = str(mock_session.execute.call_args_list[0].args[0])
    assert "cola_procesamiento" in primera_sql


def test_limpiar_disco_borra_carpetas(tmp_path):
    uploads = tmp_path / "uploads" / "3"
    uploads.mkdir(parents=True)
    (uploads / "test.pdf").write_bytes(b"test")

    c = CleanupCompleto("http://fs", "token", 3, "http://api", "jwt")
    c.limpiar_disco(str(tmp_path))
    assert not (tmp_path / "uploads" / "3").exists()
