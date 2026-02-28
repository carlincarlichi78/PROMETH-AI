"""Tests para ServicioFiscal."""
import pytest
from unittest.mock import MagicMock, patch

from sfce.core.servicio_fiscal import ServicioFiscal


@pytest.fixture
def servicio():
    repo_mock = MagicMock()
    normativa_mock = MagicMock()
    normativa_mock.tipo_is.return_value = 25.0
    normativa_mock.umbral.return_value = 3005.06

    # Configurar retornos por defecto
    repo_mock.iva_por_periodo.return_value = {
        "total_repercutido": 2100.0,
        "total_soportado": 1050.0,
        "periodo": "1T", "ejercicio": "2025"
    }
    repo_mock.retenciones_por_periodo.return_value = {
        "trabajo": 500.0, "profesionales": 200.0,
        "alquileres": 0.0, "capital": 0.0, "total": 700.0,
        "periodo": "1T", "ejercicio": "2025"
    }
    repo_mock.alquileres_por_periodo.return_value = {
        "base_alquileres": 5000.0, "retenciones_alquileres": 950.0,
        "num_arrendadores": 1, "periodo": "1T"
    }
    repo_mock.operaciones_terceros.return_value = []
    repo_mock.operaciones_intracomunitarias.return_value = []
    repo_mock.pyg.return_value = {
        "ventas": -50000.0, "compras": 20000.0,
        "gastos_personal": 5000.0, "otros_gastos": 3000.0
    }

    return ServicioFiscal(repo_mock, normativa_mock)


class TestCalcularCasillas:
    def test_303_calcula_casillas(self, servicio):
        resultado = servicio.calcular_casillas(1, "303", "2025", "1T")
        assert resultado["modelo"] == "303"
        assert "casillas" in resultado
        assert resultado["casillas"]["27"] == 2100.0

    def test_303_casilla_37_iva_soportado(self, servicio):
        resultado = servicio.calcular_casillas(1, "303", "2025", "1T")
        assert resultado["casillas"]["37"] == 1050.0

    def test_111_calcula_casillas(self, servicio):
        resultado = servicio.calcular_casillas(1, "111", "2025", "1T")
        assert resultado["modelo"] == "111"
        assert resultado["casillas"]["28"] == 700.0

    def test_111_casilla_trabajo(self, servicio):
        resultado = servicio.calcular_casillas(1, "111", "2025", "1T")
        assert resultado["casillas"]["02"] == 500.0

    def test_115_calcula_casillas(self, servicio):
        resultado = servicio.calcular_casillas(1, "115", "2025", "1T")
        assert resultado["modelo"] == "115"
        assert resultado["casillas"]["03"] == 950.0

    def test_115_casilla_04_igual_03(self, servicio):
        resultado = servicio.calcular_casillas(1, "115", "2025", "1T")
        assert resultado["casillas"]["04"] == resultado["casillas"]["03"]

    def test_347_calcula_casillas(self, servicio):
        resultado = servicio.calcular_casillas(1, "347", "2025", "0A")
        assert resultado["modelo"] == "347"
        assert "casillas" in resultado

    def test_347_sin_operaciones(self, servicio):
        resultado = servicio.calcular_casillas(1, "347", "2025", "0A")
        assert resultado["casillas"]["num_declarados"] == 0

    def test_347_con_operaciones_grandes(self, servicio):
        servicio.repo.operaciones_terceros.return_value = [
            {"cif": "B12345678", "nombre": "Gran proveedor",
             "importe_total": 10000.0},
        ]
        resultado = servicio.calcular_casillas(1, "347", "2025", "0A")
        assert resultado["casillas"]["num_declarados"] == 1

    def test_349_calcula_casillas(self, servicio):
        resultado = servicio.calcular_casillas(1, "349", "2025", "1T")
        assert resultado["modelo"] == "349"
        assert "casillas" in resultado

    def test_349_con_operaciones(self, servicio):
        servicio.repo.operaciones_intracomunitarias.return_value = [
            {"cif": "FR12345678901", "nombre": "Client FR",
             "pais": "FR", "importe": 5000.0, "tipo_operacion": "E"},
        ]
        resultado = servicio.calcular_casillas(1, "349", "2025", "1T")
        assert resultado["casillas"]["num_declarados"] == 1
        assert resultado["casillas"]["total_entregas"] == 5000.0

    def test_130_calcula_casillas(self, servicio):
        resultado = servicio.calcular_casillas(1, "130", "2025", "1T")
        assert resultado["modelo"] == "130"
        assert resultado["casillas"]["01"] == 50000.0

    def test_devuelve_modelo_ejercicio_periodo(self, servicio):
        resultado = servicio.calcular_casillas(1, "303", "2025", "2T")
        assert resultado["ejercicio"] == "2025"
        assert resultado["periodo"] == "2T"


class TestGenerarModelo:
    def test_generar_303(self, servicio):
        resultado = servicio.generar_modelo(
            empresa_id=1, modelo="303", ejercicio="2025", periodo="1T",
            empresa_datos={"nif": "B12345678", "nombre": "TEST SL"}
        )
        assert "casillas" in resultado
        assert "validacion" in resultado

    def test_override_casillas(self, servicio):
        resultado = servicio.generar_modelo(
            empresa_id=1, modelo="303", ejercicio="2025", periodo="1T",
            casillas_override={"27": 9999.0},
            empresa_datos={"nif": "B12345678"}
        )
        assert resultado["casillas"]["27"] == 9999.0

    def test_override_no_destruye_otras_casillas(self, servicio):
        resultado = servicio.generar_modelo(
            empresa_id=1, modelo="303", ejercicio="2025", periodo="1T",
            casillas_override={"69": 500.0},
            empresa_datos={"nif": "B12345678"}
        )
        # casilla 27 sigue con el valor del repositorio
        assert resultado["casillas"]["27"] == 2100.0
        # casilla 69 tiene el override
        assert resultado["casillas"]["69"] == 500.0

    def test_error_generador_devuelve_error_amigable(self, servicio):
        # Si el generador falla, el servicio captura y devuelve estructura con error
        servicio.generador.generar = MagicMock(
            side_effect=Exception("Modelo no soportado")
        )
        resultado = servicio.generar_modelo(
            empresa_id=1, modelo="303", ejercicio="2025", periodo="1T",
            empresa_datos={"nif": "B12345678"}
        )
        assert "error" in resultado
        assert resultado["validacion"]["valido"] is False


class TestCalendarioFiscal:
    def test_calendario_sl(self, servicio):
        calendario = servicio.calendario_fiscal(1, "2025", "sl")
        modelos = {c["modelo"] for c in calendario}
        assert "303" in modelos
        assert "200" in modelos
        assert len(calendario) > 0

    def test_calendario_autonomo(self, servicio):
        calendario = servicio.calendario_fiscal(1, "2025", "autonomo")
        modelos = {c["modelo"] for c in calendario}
        assert "130" in modelos
        assert "303" in modelos

    def test_calendario_autonomo_modulos(self, servicio):
        calendario = servicio.calendario_fiscal(1, "2025", "autonomo_modulos")
        modelos = {c["modelo"] for c in calendario}
        assert "131" in modelos
        assert "420" in modelos

    def test_tiene_fecha_limite(self, servicio):
        calendario = servicio.calendario_fiscal(1, "2025", "sl")
        for item in calendario:
            assert "fecha_limite" in item
            assert item["fecha_limite"].startswith("202")

    def test_ordenado_por_fecha(self, servicio):
        calendario = servicio.calendario_fiscal(1, "2025", "sl")
        fechas = [c["fecha_limite"] for c in calendario]
        assert fechas == sorted(fechas)

    def test_4t_es_ano_siguiente(self, servicio):
        calendario = servicio.calendario_fiscal(1, "2025", "sl")
        items_4t = [c for c in calendario if c["periodo"] == "4T"]
        for item in items_4t:
            assert item["fecha_limite"].startswith("2026")

    def test_anual_es_ano_siguiente(self, servicio):
        calendario = servicio.calendario_fiscal(1, "2025", "sl")
        items_anuales = [c for c in calendario if c["periodo"] == "0A"]
        for item in items_anuales:
            assert item["fecha_limite"].startswith("2026")

    def test_estructura_item_calendario(self, servicio):
        calendario = servicio.calendario_fiscal(1, "2025", "sl")
        item = calendario[0]
        campos_requeridos = ["modelo", "nombre", "periodo", "ejercicio",
                             "fecha_limite", "estado"]
        for campo in campos_requeridos:
            assert campo in item

    def test_estado_pendiente(self, servicio):
        calendario = servicio.calendario_fiscal(1, "2025", "sl")
        for item in calendario:
            assert item["estado"] == "pendiente"

    def test_tipo_empresa_desconocido_usa_sl(self, servicio):
        # Tipo desconocido → fallback a sl
        calendario = servicio.calendario_fiscal(1, "2025", "tipo_inexistente")
        modelos = {c["modelo"] for c in calendario}
        # Debe tener los modelos de SL
        assert "303" in modelos
