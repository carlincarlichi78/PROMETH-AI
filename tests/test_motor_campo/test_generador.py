import pytest
from scripts.motor_campo.generador import GeneradorVariaciones
from scripts.motor_campo.modelos import Escenario, ResultadoEsperado


@pytest.fixture
def escenario_base():
    return Escenario(
        id="fc_basica", grupo="fc", descripcion="test",
        datos_extraidos_base={
            "tipo": "FC", "base_imponible": 1000.0,
            "iva_porcentaje": 21, "total": 1210.0,
            "fecha": "2025-06-15", "coddivisa": "EUR"
        },
        resultado_esperado=ResultadoEsperado()
    )


def test_variantes_importes(escenario_base):
    gen = GeneradorVariaciones()
    variantes = gen.variantes_importes(escenario_base)
    bases = [v.datos_extraidos["base_imponible"] for v in variantes]
    assert 100.0 in bases
    assert 9999.99 in bases
    assert len(variantes) >= 4


def test_variantes_iva(escenario_base):
    gen = GeneradorVariaciones()
    variantes = gen.variantes_iva(escenario_base)
    ivas = [v.datos_extraidos["iva_porcentaje"] for v in variantes]
    assert 0 in ivas
    assert 4 in ivas
    assert 10 in ivas


def test_variantes_fechas(escenario_base):
    gen = GeneradorVariaciones()
    variantes = gen.variantes_fechas(escenario_base, ejercicio=2025)
    fechas = [v.datos_extraidos["fecha"] for v in variantes]
    assert "2025-01-01" in fechas
    assert "2025-12-31" in fechas


def test_generar_todas_respeta_maximo(escenario_base):
    gen = GeneradorVariaciones(max_variantes=10)
    variantes = gen.generar_todas(escenario_base)
    assert len(variantes) <= 10
