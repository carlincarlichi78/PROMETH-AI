from scripts.motor_campo.modelos import ResultadoEjecucion


def test_resultado_ejecucion_defaults():
    r = ResultadoEjecucion(
        escenario_id="fc_basica", variante_id="imp_000",
        canal="http", resultado="ok", duracion_ms=123,
    )
    assert r.estado_doc_final is None
    assert r.idasiento is None
    assert r.detalles == {}


def test_resultado_ejecucion_completo():
    r = ResultadoEjecucion(
        escenario_id="fc_basica", variante_id="imp_000",
        canal="http", resultado="ok",
        estado_doc_final="procesado", tipo_doc_detectado="FC",
        idasiento=42, asiento_cuadrado=True, duracion_ms=850,
        detalles={"idfactura": 7, "partidas": []},
    )
    assert r.idasiento == 42
    assert r.detalles["idfactura"] == 7
