from scripts.motor_campo.catalogo.especiales import obtener_escenarios_especiales


def test_tiene_6_escenarios():
    esc = obtener_escenarios_especiales()
    assert len(esc) == 6


def test_nc_cliente_tipo_correcto():
    esc = obtener_escenarios_especiales()
    nc = next(e for e in esc if e.id == "nc_cliente")
    assert nc.datos_extraidos_base["tipo"] == "NC"


def test_nom_tiene_irpf():
    esc = obtener_escenarios_especiales()
    nom = next(e for e in esc if e.id == "nom_basica")
    assert "irpf_porcentaje" in nom.datos_extraidos_base


def test_sum_tipo_suministro():
    esc = obtener_escenarios_especiales()
    s = next(e for e in esc if e.id == "sum_suministro")
    assert s.datos_extraidos_base["tipo"] == "SUM"
