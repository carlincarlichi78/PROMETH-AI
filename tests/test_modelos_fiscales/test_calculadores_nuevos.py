"""Tests para calculadores nuevos en sfce.core.calculador_modelos.

Cubre metodos T10-T12: 115, 180, 123, 193, 131, 202, 349, 420, 210, 216.
"""
import pytest
from sfce.core.calculador_modelos import CalculadorModelos
from sfce.normativa.vigente import Normativa


@pytest.fixture
def calculador():
    """Calculador con normativa real."""
    return CalculadorModelos(Normativa())


# ==================== MODELO 115 ====================

class TestCalculador115:
    """Retenciones arrendamientos trimestrales."""

    def test_basico(self, calculador):
        resultado = calculador.calcular_115(
            retenciones_alquileres=950.0,
            trimestre="T1",
            ejercicio=2025,
        )
        assert resultado["modelo"] == "115"
        assert resultado["trimestre"] == "T1"
        assert resultado["ejercicio"] == 2025
        assert resultado["casilla_03"] == 950.0
        assert resultado["casilla_04"] == 950.0
        assert resultado["casilla_01"] >= 1  # al menos 1 arrendador
        assert resultado["tipo"] == "automatico"

    def test_sin_retenciones(self, calculador):
        resultado = calculador.calcular_115(
            retenciones_alquileres=0.0,
            trimestre="T2",
            ejercicio=2025,
        )
        assert resultado["casilla_03"] == 0.0
        assert resultado["casilla_04"] == 0.0
        assert resultado["casilla_02"] == 0.0

    def test_base_calculada_desde_retencion(self, calculador):
        # Base = retencion / 0.19 (tipo retención 19%)
        retencion = 190.0
        resultado = calculador.calcular_115(
            retenciones_alquileres=retencion,
            trimestre="T3",
            ejercicio=2025,
        )
        assert resultado["casilla_02"] == round(retencion / 0.19, 2)


# ==================== MODELO 180 ====================

class TestCalculador180:
    """Resumen anual retenciones alquileres."""

    def test_basico(self, calculador):
        datos = [
            {"nif_arrendador": "12345678A", "nombre": "Arrendador UNO",
             "importe": 5000.0, "retencion": 950.0,
             "referencia_catastral": "0001", "direccion": "Calle Mayor 1"},
        ]
        resultado = calculador.calcular_180(datos, ejercicio=2025)
        assert resultado["modelo"] == "180"
        assert resultado["ejercicio"] == 2025
        assert resultado["num_arrendadores"] == 1
        assert resultado["total_base"] == 5000.0
        assert resultado["total_retencion"] == 950.0
        assert resultado["tipo"] == "automatico"

    def test_multiples_arrendadores(self, calculador):
        datos = [
            {"nif_arrendador": "11111111A", "nombre": "Arrendador A",
             "importe": 3000.0, "retencion": 570.0},
            {"nif_arrendador": "22222222B", "nombre": "Arrendador B",
             "importe": 4000.0, "retencion": 760.0},
            {"nif_arrendador": "33333333C", "nombre": "Arrendador C",
             "importe": 2000.0, "retencion": 380.0},
        ]
        resultado = calculador.calcular_180(datos, ejercicio=2025)
        assert resultado["num_arrendadores"] == 3
        assert resultado["total_base"] == 9000.0
        assert resultado["total_retencion"] == 1710.0
        assert len(resultado["declarados"]) == 3

    def test_sin_arrendadores(self, calculador):
        resultado = calculador.calcular_180([], ejercicio=2025)
        assert resultado["num_arrendadores"] == 0
        assert resultado["total_base"] == 0.0
        assert resultado["total_retencion"] == 0.0


# ==================== MODELO 123 ====================

class TestCalculador123:
    """Retenciones capital mobiliario trimestrales."""

    def test_basico(self, calculador):
        resultado = calculador.calcular_123(
            rendimientos_capital=2000.0,
            retenciones=380.0,
            trimestre="T1",
            ejercicio=2025,
        )
        assert resultado["modelo"] == "123"
        assert resultado["trimestre"] == "T1"
        assert resultado["ejercicio"] == 2025
        assert resultado["casilla_02"] == 2000.0
        assert resultado["casilla_03"] == 380.0
        assert resultado["casilla_04"] == 380.0
        assert resultado["casilla_01"] == 1  # hay perceptores

    def test_sin_rendimientos(self, calculador):
        resultado = calculador.calcular_123(
            rendimientos_capital=0.0,
            retenciones=0.0,
            trimestre="T2",
            ejercicio=2025,
        )
        assert resultado["casilla_01"] == 0  # sin perceptores
        assert resultado["casilla_02"] == 0.0
        assert resultado["casilla_03"] == 0.0

    def test_redondeo_centimos(self, calculador):
        resultado = calculador.calcular_123(
            rendimientos_capital=1500.555,
            retenciones=285.105,
            trimestre="T3",
            ejercicio=2025,
        )
        # Verificar que los valores estan redondeados a 2 decimales
        assert resultado["casilla_02"] == round(1500.555, 2)
        assert resultado["casilla_03"] == round(285.105, 2)


# ==================== MODELO 193 ====================

class TestCalculador193:
    """Resumen anual capital mobiliario."""

    def test_basico(self, calculador):
        datos = [
            {"nif_perceptor": "12345678A", "nombre": "Socio UNO",
             "clave_tipo": "A", "base": 5000.0,
             "porcentaje": 19.0, "retencion": 950.0},
        ]
        resultado = calculador.calcular_193(datos, ejercicio=2025)
        assert resultado["modelo"] == "193"
        assert resultado["ejercicio"] == 2025
        assert resultado["num_perceptores"] == 1
        assert resultado["total_base"] == 5000.0
        assert resultado["total_retencion"] == 950.0
        assert resultado["tipo"] == "automatico"

    def test_multiples_perceptores(self, calculador):
        datos = [
            {"nif_perceptor": "11111111A", "nombre": "Socio A",
             "clave_tipo": "A", "base": 2000.0, "porcentaje": 19.0, "retencion": 380.0},
            {"nif_perceptor": "22222222B", "nombre": "Socio B",
             "clave_tipo": "A", "base": 3000.0, "porcentaje": 19.0, "retencion": 570.0},
        ]
        resultado = calculador.calcular_193(datos, ejercicio=2025)
        assert resultado["num_perceptores"] == 2
        assert resultado["total_base"] == 5000.0
        assert resultado["total_retencion"] == 950.0
        assert len(resultado["declarados"]) == 2

    def test_sin_datos(self, calculador):
        resultado = calculador.calcular_193([], ejercicio=2025)
        assert resultado["num_perceptores"] == 0
        assert resultado["total_base"] == 0.0
        assert resultado["total_retencion"] == 0.0


# ==================== MODELO 131 ====================

class TestCalculador131:
    """Pago fraccionado IRPF regimen modulos."""

    def test_basico(self, calculador):
        resultado = calculador.calcular_131(
            rendimiento_modulos=50000.0,
            pagos_anteriores=500.0,
            trimestre="T2",
            ejercicio=2025,
        )
        assert resultado["modelo"] == "131"
        assert resultado["trimestre"] == "T2"
        assert resultado["ejercicio"] == 2025
        # cuota = 50000 * 0.02 = 1000, resultado = 1000 - 500 = 500
        assert resultado["cuota"] == 1000.0
        assert resultado["resultado"] == 500.0
        assert resultado["porcentaje"] == 2.0
        assert resultado["tipo"] == "automatico"

    def test_sin_pagos_anteriores(self, calculador):
        resultado = calculador.calcular_131(
            rendimiento_modulos=80000.0,
            pagos_anteriores=0.0,
            trimestre="T1",
            ejercicio=2025,
        )
        # cuota = 80000 * 0.02 = 1600, sin pagos previos → resultado = 1600
        assert resultado["cuota"] == 1600.0
        assert resultado["resultado"] == 1600.0
        assert resultado["pagos_anteriores"] == 0.0

    def test_resultado_no_negativo(self, calculador):
        # Si pagos anteriores > cuota, resultado = 0 (no se puede pagar negativo)
        resultado = calculador.calcular_131(
            rendimiento_modulos=10000.0,
            pagos_anteriores=9999.0,
            trimestre="T4",
            ejercicio=2025,
        )
        # cuota = 10000 * 0.02 = 200, pagos_ant=9999 → max(200-9999, 0) = 0
        assert resultado["resultado"] == 0.0


# ==================== MODELO 202 ====================

class TestCalculador202:
    """Pagos fraccionados IS trimestral."""

    def test_modalidad_art40_2(self, calculador):
        resultado = calculador.calcular_202(
            cuota_is_anterior=40000.0,
            base_imponible_acumulada=0.0,
            modalidad="art40.2",
            ejercicio=2025,
        )
        assert resultado["modelo"] == "202"
        assert resultado["modalidad"] == "art40.2"
        assert resultado["ejercicio"] == 2025
        # pago = cuota_anterior * 18% = 40000 * 0.18 = 7200
        assert resultado["pago_fraccionado"] == 7200.0
        assert resultado["tipo"] == "automatico"

    def test_modalidad_art40_3(self, calculador):
        resultado = calculador.calcular_202(
            cuota_is_anterior=0.0,
            base_imponible_acumulada=90000.0,
            modalidad="art40.3",
            ejercicio=2025,
        )
        assert resultado["modalidad"] == "art40.3"
        # pago = base_acumulada * 17% = 90000 * 0.17 = 15300
        assert resultado["pago_fraccionado"] == 15300.0

    def test_resultado_no_negativo_art40_2(self, calculador):
        resultado = calculador.calcular_202(
            cuota_is_anterior=-5000.0,  # perdidas ejercicio anterior
            base_imponible_acumulada=0.0,
            modalidad="art40.2",
            ejercicio=2025,
        )
        assert resultado["pago_fraccionado"] == 0.0

    def test_resultado_no_negativo_art40_3(self, calculador):
        resultado = calculador.calcular_202(
            cuota_is_anterior=0.0,
            base_imponible_acumulada=-20000.0,  # perdidas acumuladas
            modalidad="art40.3",
            ejercicio=2025,
        )
        assert resultado["pago_fraccionado"] == 0.0


# ==================== MODELO 349 ====================

class TestCalculador349:
    """Declaracion recapitulativa operaciones intracomunitarias."""

    def test_solo_entregas(self, calculador):
        operaciones = [
            {"cif": "FR12345678901", "nombre": "Client FR",
             "pais": "FR", "importe": 10000.0, "tipo_operacion": "E"},
            {"cif": "DE987654321", "nombre": "Kunde DE",
             "pais": "DE", "importe": 5000.0, "tipo_operacion": "E"},
        ]
        resultado = calculador.calcular_349(operaciones, periodo="1T", ejercicio=2025)
        assert resultado["modelo"] == "349"
        assert resultado["periodo"] == "1T"
        assert resultado["ejercicio"] == 2025
        assert resultado["num_declarados"] == 2
        assert resultado["total_entregas"] == 15000.0
        assert resultado["total_adquisiciones"] == 0.0
        assert resultado["tipo"] == "automatico"

    def test_multiples_tipos(self, calculador):
        operaciones = [
            {"cif": "FR12345678901", "nombre": "Client FR",
             "pais": "FR", "importe": 8000.0, "tipo_operacion": "E"},
            {"cif": "IT12345678901", "nombre": "Fornitore IT",
             "pais": "IT", "importe": 3000.0, "tipo_operacion": "A"},
            {"cif": "PT123456789", "nombre": "Empresa PT",
             "pais": "PT", "importe": 2000.0, "tipo_operacion": "S"},
        ]
        resultado = calculador.calcular_349(operaciones, periodo="2T", ejercicio=2025)
        assert resultado["num_declarados"] == 3
        assert resultado["total_entregas"] == 8000.0
        assert resultado["total_adquisiciones"] == 3000.0
        assert resultado["total_servicios_prestados"] == 2000.0

    def test_sin_operaciones(self, calculador):
        resultado = calculador.calcular_349([], periodo="1T", ejercicio=2025)
        assert resultado["num_declarados"] == 0
        assert resultado["total_entregas"] == 0.0
        assert resultado["total_adquisiciones"] == 0.0


# ==================== MODELO 420 ====================

class TestCalculador420:
    """IGIC Canarias — equivalente al 303."""

    def test_basico(self, calculador):
        resultado = calculador.calcular_420(
            igic_repercutido=3000.0,
            igic_soportado=1200.0,
            trimestre="T1",
            ejercicio=2025,
        )
        assert resultado["modelo"] == "420"
        assert resultado["trimestre"] == "T1"
        assert resultado["ejercicio"] == 2025
        assert resultado["igic_repercutido"] == 3000.0
        assert resultado["igic_soportado"] == 1200.0
        assert resultado["resultado"] == 1800.0
        assert resultado["resultado_liquidacion"] == 1800.0
        assert resultado["tipo"] == "automatico"

    def test_resultado_negativo_con_compensacion(self, calculador):
        resultado = calculador.calcular_420(
            igic_repercutido=1000.0,
            igic_soportado=3000.0,
            trimestre="T2",
            ejercicio=2025,
            compensacion_anterior=0.0,
        )
        assert resultado["resultado"] == -2000.0

    def test_con_compensacion_anterior(self, calculador):
        resultado = calculador.calcular_420(
            igic_repercutido=5000.0,
            igic_soportado=2000.0,
            trimestre="T3",
            ejercicio=2025,
            compensacion_anterior=1000.0,
        )
        # resultado = 5000-2000 = 3000, liquidacion = 3000-1000 = 2000
        assert resultado["resultado"] == 3000.0
        assert resultado["resultado_liquidacion"] == 2000.0
        assert resultado["compensacion_anterior"] == 1000.0


# ==================== MODELO 210 ====================

class TestCalculador210:
    """IRNR sin establecimiento permanente."""

    def test_dividendos(self, calculador):
        resultado = calculador.calcular_210(
            tipo_renta="dividendos",
            base_imponible=10000.0,
            tipo_gravamen=19.0,
            ejercicio=2025,
        )
        assert resultado["modelo"] == "210"
        assert resultado["ejercicio"] == 2025
        assert resultado["tipo_renta"] == "dividendos"
        assert resultado["base_imponible"] == 10000.0
        assert resultado["tipo_gravamen"] == 19.0
        assert resultado["cuota_integra"] == 1900.0
        assert resultado["resultado"] == 1900.0
        assert resultado["tipo"] == "automatico"

    def test_royalties_convenio(self, calculador):
        # Tipo reducido por convenio de doble imposicion
        resultado = calculador.calcular_210(
            tipo_renta="royalties",
            base_imponible=5000.0,
            tipo_gravamen=10.0,
            ejercicio=2025,
        )
        assert resultado["tipo_renta"] == "royalties"
        assert resultado["tipo_gravamen"] == 10.0
        assert resultado["cuota_integra"] == 500.0

    def test_base_cero(self, calculador):
        resultado = calculador.calcular_210(
            tipo_renta="intereses",
            base_imponible=0.0,
            tipo_gravamen=19.0,
            ejercicio=2025,
        )
        assert resultado["cuota_integra"] == 0.0
        assert resultado["resultado"] == 0.0


# ==================== MODELO 216 ====================

class TestCalculador216:
    """Retenciones no residentes trimestrales."""

    def test_basico(self, calculador):
        resultado = calculador.calcular_216(
            retenciones_no_residentes=380.0,
            trimestre="T1",
            ejercicio=2025,
        )
        assert resultado["modelo"] == "216"
        assert resultado["trimestre"] == "T1"
        assert resultado["ejercicio"] == 2025
        assert resultado["total_retenciones"] == 380.0
        assert resultado["resultado"] == 380.0
        assert resultado["num_perceptores"] == 1
        assert resultado["tipo"] == "automatico"

    def test_sin_retenciones(self, calculador):
        resultado = calculador.calcular_216(
            retenciones_no_residentes=0.0,
            trimestre="T2",
            ejercicio=2025,
        )
        assert resultado["total_retenciones"] == 0.0
        assert resultado["num_perceptores"] == 0
        assert resultado["resultado"] == 0.0

    def test_base_calculada(self, calculador):
        # base = retenciones / 0.19
        retencion = 190.0
        resultado = calculador.calcular_216(
            retenciones_no_residentes=retencion,
            trimestre="T3",
            ejercicio=2025,
        )
        assert resultado["base_retenciones"] == round(retencion / 0.19, 2)
