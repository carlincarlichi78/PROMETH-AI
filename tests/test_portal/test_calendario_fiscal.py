from datetime import date
from sfce.modelos_fiscales.calendario_fiscal import obtener_deadlines_ejercicio


class EmpresaFake:
    """Objeto minimo que simula una Empresa para los tests."""
    def __init__(self, forma_juridica, territorio, regimen_iva):
        self.forma_juridica = forma_juridica
        self.territorio = territorio
        self.regimen_iva = regimen_iva


def test_autonomo_tiene_303_trimestral():
    empresa = EmpresaFake("autonomo", "peninsula", "general")
    deadlines = obtener_deadlines_ejercicio(empresa, ejercicio=2025)
    modelos = [d["modelo"] for d in deadlines]
    assert "303" in modelos


def test_sl_tiene_200_anual():
    empresa = EmpresaFake("sl", "peninsula", "general")
    deadlines = obtener_deadlines_ejercicio(empresa, ejercicio=2025)
    modelos = [d["modelo"] for d in deadlines]
    assert "200" in modelos  # IS sociedades


def test_autonomo_tiene_130_trimestral():
    empresa = EmpresaFake("autonomo", "peninsula", "general")
    deadlines = obtener_deadlines_ejercicio(empresa, ejercicio=2025)
    modelos = [d["modelo"] for d in deadlines]
    assert "130" in modelos


def test_deadlines_tienen_campos_requeridos():
    empresa = EmpresaFake("sl", "peninsula", "general")
    deadlines = obtener_deadlines_ejercicio(empresa, ejercicio=2025)
    for d in deadlines:
        assert "modelo" in d
        assert "fecha_limite" in d
        assert isinstance(d["fecha_limite"], date)
        assert "descripcion" in d


def test_canarias_no_tiene_303():
    """Canarias usa IGIC, no IVA/303."""
    empresa = EmpresaFake("autonomo", "canarias", "general")
    deadlines = obtener_deadlines_ejercicio(empresa, ejercicio=2025)
    modelos = [d["modelo"] for d in deadlines]
    assert "303" not in modelos
