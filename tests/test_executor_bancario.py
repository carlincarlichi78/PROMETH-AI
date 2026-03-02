from unittest.mock import patch, MagicMock
from scripts.motor_campo.executor_bancario import ExecutorBancario
from scripts.motor_campo.modelos import ResultadoEjecucion


@patch("scripts.motor_campo.executor_bancario.requests.post")
def test_c43_normal_retorna_ok(mock_post):
    mock_post.side_effect = [
        MagicMock(status_code=200, json=lambda: {"access_token": "tok"}, raise_for_status=lambda: None),
        MagicMock(status_code=200, json=lambda: {"movimientos_creados": 2, "saldo_inicial": 0, "saldo_final": 200},
                  headers={"content-type": "application/json"}),
    ]
    eb = ExecutorBancario("http://api", empresa_id=3)
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False, encoding="latin-1") as f:
        f.write("11201234567890000020260101001210600000000001                    00000000000000000000        BANCO          EUR\n")
        ruta = f.name
    try:
        resultado = eb.ejecutar_archivo(ruta, "ban_c43_estandar", "test", movimientos_esperados=2)
        assert isinstance(resultado, ResultadoEjecucion)
        assert resultado.canal == "bancario"
        assert resultado.estado_doc_final == "procesado"
        assert resultado.resultado == "ok"
    finally:
        os.unlink(ruta)


@patch("scripts.motor_campo.executor_bancario.requests.post")
def test_c43_movimientos_incorrectos_retorna_bug(mock_post):
    mock_post.side_effect = [
        MagicMock(status_code=200, json=lambda: {"access_token": "tok"}, raise_for_status=lambda: None),
        MagicMock(status_code=200, json=lambda: {"movimientos_creados": 5},
                  headers={"content-type": "application/json"}),
    ]
    eb = ExecutorBancario("http://api", empresa_id=3)
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as f:
        f.write("test"); ruta = f.name
    try:
        resultado = eb.ejecutar_archivo(ruta, "ban_test", "test", movimientos_esperados=2)
        assert resultado.resultado == "bug_pendiente"
        assert "movimientos" in resultado.detalles.get("error", "")
    finally:
        os.unlink(ruta)
