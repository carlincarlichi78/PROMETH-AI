from scripts.motor_campo.catalogo.fc import obtener_escenarios_fc
from scripts.motor_campo.catalogo.fv import obtener_escenarios_fv


def test_fc_tiene_5_escenarios():
    escenarios = obtener_escenarios_fc()
    assert len(escenarios) == 5
    ids = [e.id for e in escenarios]
    assert "fc_basica" in ids
    assert "fc_intracomunitaria" in ids
    assert "fc_usd" in ids


def test_fc_basica_tiene_campos_correctos():
    escenarios = obtener_escenarios_fc()
    e = next(e for e in escenarios if e.id == "fc_basica")
    d = e.datos_extraidos_base
    assert d["tipo"] == "FC"
    assert d["iva_porcentaje"] == 21
    assert d["base_imponible"] > 0
    assert "fecha" in d
    assert "emisor_cif" in d


def test_fc_intracomunitaria_iva_cero():
    escenarios = obtener_escenarios_fc()
    e = next(e for e in escenarios if e.id == "fc_intracomunitaria")
    assert e.datos_extraidos_base["iva_porcentaje"] == 0


def test_fv_tiene_4_escenarios():
    escenarios = obtener_escenarios_fv()
    assert len(escenarios) == 4


def test_fv_intracomunitario_regimen():
    escenarios = obtener_escenarios_fv()
    e = next(e for e in escenarios if e.id == "fv_intracomunitario")
    assert e.datos_extraidos_base["regimen"] == "intracomunitario"
