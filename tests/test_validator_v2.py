from unittest.mock import patch, MagicMock
from scripts.motor_campo.modelos import ResultadoEjecucion
from scripts.motor_campo.validator_v2 import ValidatorV2

MANIFESTO_FC = {
    "tipo_doc_esperado": "FC",
    "estado_esperado": "procesado",
    "asiento_cuadrado": True,
    "iva_correcto": True,
    "codimpuesto_esperado": "IVA21",
    "tiene_asiento": True,
    "max_duracion_s": 60,
}
MANIFESTO_E01 = {
    "estado_esperado": "cuarentena",
    "razon_cuarentena_esperada": "check_1_cif_invalido",
    "tiene_asiento": False,
    "max_duracion_s": 600,
}


def _ok_fc():
    return ResultadoEjecucion(
        escenario_id="fc_basica", variante_id="test", canal="http",
        resultado="ok", duracion_ms=1500,
        estado_doc_final="procesado", tipo_doc_detectado="FC",
        idasiento=42, asiento_cuadrado=True,
        detalles={"doc_id": 1},
    )


def test_sin_errores_cuando_todo_correcto():
    with patch("scripts.motor_campo.validator_v2.ValidatorV2._verificar_iva") as mock_iva, \
         patch("scripts.motor_campo.validator_v2.ValidatorV2._verificar_cuadre") as mock_cuadre:
        mock_iva.return_value = None
        mock_cuadre.return_value = None
        v = ValidatorV2("http://api", "jwt")
        errores = v.validar(_ok_fc(), MANIFESTO_FC, doc_id=1)
        assert errores == []


def test_error_estado_incorrecto():
    r = _ok_fc()
    r.estado_doc_final = "cuarentena"
    v = ValidatorV2("http://api", "jwt")
    errores = v.validar(r, MANIFESTO_FC, doc_id=1)
    assert any(e["tipo"] == "estado_incorrecto" for e in errores)


def test_error_tipo_doc_incorrecto():
    r = _ok_fc()
    r.tipo_doc_detectado = "FV"
    v = ValidatorV2("http://api", "jwt")
    errores = v.validar(r, MANIFESTO_FC, doc_id=1)
    assert any(e["tipo"] == "tipo_doc_incorrecto" for e in errores)


def test_error_timeout():
    r = _ok_fc()
    r.duracion_ms = 120_000  # 120s
    v = ValidatorV2("http://api", "jwt")
    errores = v.validar(r, MANIFESTO_FC, doc_id=1)
    assert any(e["tipo"] == "timeout_excedido" for e in errores)


@patch("scripts.motor_campo.validator_v2.requests.get")
def test_valida_razon_cuarentena(mock_get):
    mock_get.return_value = MagicMock(
        status_code=200,
        json=lambda: {"razon_cuarentena": "check_1_cif_invalido"},
    )
    r = ResultadoEjecucion(
        escenario_id="E01", variante_id="test", canal="http",
        resultado="ok", duracion_ms=500,
        estado_doc_final="cuarentena", detalles={"doc_id": 99},
    )
    v = ValidatorV2("http://api", "jwt")
    errores = v.validar(r, MANIFESTO_E01, doc_id=99)
    assert errores == []
