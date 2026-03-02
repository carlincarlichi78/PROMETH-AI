from unittest.mock import patch, MagicMock
from scripts.motor_campo.executor_email import ExecutorEmail
from scripts.motor_campo.modelos import ResultadoEjecucion


@patch("scripts.motor_campo.executor_email.smtplib.SMTP")
@patch("scripts.motor_campo.executor_email.requests.get")
@patch("scripts.motor_campo.executor_email.requests.post")
def test_envia_email_y_espera_doc(mock_post, mock_get, mock_smtp):
    mock_post.return_value = MagicMock(
        status_code=200, json=lambda: {"access_token": "tok"}, raise_for_status=lambda: None
    )
    mock_get.side_effect = [
        MagicMock(status_code=200, json=lambda: {"items": [{"doc_id": 55, "nombre_archivo": "fc_SFCE_TEST_fc_basica_abc12345.pdf"}]}),
        MagicMock(status_code=200, json=lambda: {"estado": "procesado", "tipo_doc": "FC", "idasiento": 7}),
    ]
    smtp_instance = MagicMock()
    mock_smtp.return_value.__enter__ = lambda s: smtp_instance
    mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

    ee = ExecutorEmail(
        sfce_api_url="http://api", empresa_id=3,
        smtp_host="smtp.test", smtp_port=587,
        smtp_user="test@test.com", smtp_password="pass",
        email_destino="inbox@test.com",
        poll_timeout_s=5, poll_interval_s=0.01,
    )
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(b"%PDF-1.4 test"); ruta = f.name
    try:
        resultado = ee.ejecutar_archivo(ruta, escenario_id="fc_basica", variante_id="email_test")
        assert isinstance(resultado, ResultadoEjecucion)
        assert resultado.canal == "email"
        assert smtp_instance.sendmail.called or smtp_instance.send_message.called
    finally:
        os.unlink(ruta)


def test_sin_smtp_config_retorna_error_sistema():
    ee = ExecutorEmail(
        sfce_api_url="http://api", empresa_id=3,
        smtp_host="", smtp_port=587,
        smtp_user="", smtp_password="",
        email_destino="inbox@test.com",
    )
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(b"test"); ruta = f.name
    try:
        resultado = ee.ejecutar_archivo(ruta, "fc_basica", "email_test")
        assert resultado.resultado == "error_sistema"
        assert "smtp" in resultado.detalles.get("error", "").lower()
    finally:
        os.unlink(ruta)
