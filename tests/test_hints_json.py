from sfce.core.hints_json import HintsJson, EnriquecimientoAplicado, construir_hints, merge_enriquecimiento


def test_construir_hints_minimo():
    h = construir_hints(tipo_doc="FV", origen="email_ingesta")
    assert h["tipo_doc"] == "FV"
    assert h["origen"] == "email_ingesta"
    assert "enriquecimiento" not in h


def test_construir_hints_con_enriquecimiento():
    enr: EnriquecimientoAplicado = {"iva_deducible_pct": 100, "fuente": "email_gestor"}
    h = construir_hints(tipo_doc="FV", origen="email_ingesta", enriquecimiento=enr)
    assert h["enriquecimiento"]["iva_deducible_pct"] == 100


def test_merge_enriquecimiento_override():
    """El enriquecimiento del gestor tiene prioridad máxima."""
    hints_ocr: HintsJson = {"tipo_doc": "FV", "origen": "email_ingesta"}
    enr_gestor: EnriquecimientoAplicado = {"iva_deducible_pct": 0, "tipo_doc_override": "FC"}
    resultado = merge_enriquecimiento(hints_ocr, enr_gestor)
    assert resultado["enriquecimiento"]["iva_deducible_pct"] == 0
    assert resultado["enriquecimiento"]["tipo_doc_override"] == "FC"


def test_merge_enriquecimiento_preserva_hints_existentes():
    hints_existentes: HintsJson = {"tipo_doc": "FV", "nota": "factura enero", "origen": "catchall_email"}
    enr: EnriquecimientoAplicado = {"notas": "urgente contabilizar"}
    resultado = merge_enriquecimiento(hints_existentes, enr)
    assert resultado["nota"] == "factura enero"
    assert resultado["enriquecimiento"]["notas"] == "urgente contabilizar"
