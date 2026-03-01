from scripts.motor_campo.modelos import Escenario, VarianteEjecucion, ResultadoEsperado


def test_escenario_tiene_id():
    e = Escenario(
        id="fc_basica",
        grupo="facturas_cliente",
        descripcion="FC española IVA 21%",
        datos_extraidos_base={"tipo": "FC", "base_imponible": 1000.0, "iva_porcentaje": 21},
        resultado_esperado=ResultadoEsperado(http_status=200, debe_igual_haber=True),
    )
    assert e.id == "fc_basica"
    assert e.resultado_esperado.debe_igual_haber is True


def test_variante_merge():
    e = Escenario(
        id="fc_basica", grupo="fc", descripcion="test",
        datos_extraidos_base={"tipo": "FC", "base_imponible": 1000.0, "iva_porcentaje": 21},
        resultado_esperado=ResultadoEsperado(http_status=200, debe_igual_haber=True),
    )
    v = e.crear_variante({"base_imponible": 500.0}, "v_500")
    assert v.datos_extraidos["base_imponible"] == 500.0
    assert v.datos_extraidos["tipo"] == "FC"
