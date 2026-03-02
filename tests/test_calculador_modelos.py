"""Tests para sfce.core.calculador_modelos — modelos fiscales 3 categorias."""
from datetime import date

import pytest
from sfce.core.calculador_modelos import CalculadorModelos
from sfce.normativa.vigente import Normativa


class TestModelo303:
    """Automatico: IVA trimestral."""

    def test_303_basico(self):
        calc = CalculadorModelos(Normativa())
        resultado = calc.calcular_303(
            iva_repercutido=5000, iva_soportado=3000,
            trimestre="T3", ejercicio=2025)
        assert resultado["casilla_27"] == 5000  # IVA devengado
        assert resultado["casilla_37"] == 3000  # IVA deducible
        assert resultado["casilla_69"] == 2000  # resultado
        assert resultado["modelo"] == "303"
        assert resultado["trimestre"] == "T3"

    def test_303_resultado_negativo(self):
        calc = CalculadorModelos(Normativa())
        resultado = calc.calcular_303(
            iva_repercutido=2000, iva_soportado=5000,
            trimestre="T1", ejercicio=2025)
        assert resultado["casilla_69"] == -3000
        assert resultado["a_compensar"] == 3000

    def test_303_con_compensacion_anterior(self):
        calc = CalculadorModelos(Normativa())
        resultado = calc.calcular_303(
            iva_repercutido=5000, iva_soportado=3000,
            trimestre="T2", ejercicio=2025,
            compensacion_anterior=500)
        assert resultado["casilla_69"] == 2000
        assert resultado["casilla_78"] == 500  # compensacion anterior
        assert resultado["resultado_liquidacion"] == 1500


class TestModelo390:
    """Automatico: resumen anual IVA."""

    def test_390_basico(self):
        calc = CalculadorModelos(Normativa())
        resultado = calc.calcular_390(
            total_bases_iva=100000,
            total_iva_devengado=21000,
            total_iva_deducible=15000,
            ejercicio=2025)
        assert resultado["modelo"] == "390"
        assert resultado["total_resultado"] == 6000

    def test_390_con_trimestrales(self):
        calc = CalculadorModelos(Normativa())
        resultado = calc.calcular_390(
            total_bases_iva=100000,
            total_iva_devengado=21000,
            total_iva_deducible=15000,
            ejercicio=2025,
            ingresos_trimestrales=5500)
        assert resultado["diferencia_regularizacion"] == 500


class TestModelo111:
    """Automatico: retenciones IRPF."""

    def test_111_basico(self):
        calc = CalculadorModelos(Normativa())
        resultado = calc.calcular_111(
            retenciones_trabajo=3000,
            retenciones_profesionales=1500,
            trimestre="T1", ejercicio=2025)
        assert resultado["modelo"] == "111"
        assert resultado["total_retenciones"] == 4500

    def test_111_solo_trabajo(self):
        calc = CalculadorModelos(Normativa())
        resultado = calc.calcular_111(
            retenciones_trabajo=2000,
            retenciones_profesionales=0,
            trimestre="T2", ejercicio=2025)
        assert resultado["total_retenciones"] == 2000


class TestModelo130:
    """Automatico: pago fraccionado IRPF autonomo."""

    def test_130_basico(self):
        calc = CalculadorModelos(Normativa())
        resultado = calc.calcular_130(
            ingresos_acumulados=40000,
            gastos_acumulados=20000,
            pagos_anteriores=2000,
            trimestre="T2", ejercicio=2025)
        assert resultado["modelo"] == "130"
        # Rendimiento = 20000, 20% = 4000, menos pagos anteriores 2000 = 2000
        assert resultado["rendimiento_neto"] == 20000
        assert resultado["cuota_20pct"] == 4000
        assert resultado["resultado"] == 2000


class TestModelo347:
    """Automatico: operaciones con terceros >3.005,06."""

    def test_347_basico(self):
        calc = CalculadorModelos(Normativa())
        operaciones = {
            "A28015865": {"nombre": "Telefonica", "importe": 5000},
            "B12345678": {"nombre": "Proveedor menor", "importe": 2000},
            "C99887766": {"nombre": "Gran proveedor", "importe": 10000},
        }
        resultado = calc.calcular_347(operaciones, ejercicio=2025)
        assert resultado["modelo"] == "347"
        # Solo 2 superan 3005.06
        assert len(resultado["declarados"]) == 2
        assert resultado["excluidos"] == 1


class TestBorrador200:
    """Semi-automatico: Impuesto Sociedades."""

    def test_borrador_200_basico(self):
        calc = CalculadorModelos(Normativa())
        resultado = calc.borrador_200(
            resultado_contable=50000,
            ajustes_positivos=0,
            ajustes_negativos=0,
            bases_negativas_anteriores=0,
            pagos_a_cuenta=5000,
            ejercicio=2025)
        assert resultado["modelo"] == "200"
        assert resultado["base_imponible"] == 50000
        assert resultado["cuota_integra"] == 12500  # 25%
        assert resultado["a_ingresar"] == 7500  # 12500 - 5000
        assert resultado["campos_editables"] is not None

    def test_borrador_200_con_bases_negativas(self):
        calc = CalculadorModelos(Normativa())
        resultado = calc.borrador_200(
            resultado_contable=50000,
            ajustes_positivos=0,
            ajustes_negativos=0,
            bases_negativas_anteriores=10000,
            pagos_a_cuenta=0,
            ejercicio=2025)
        assert resultado["base_imponible"] == 40000
        assert resultado["cuota_integra"] == 10000

    def test_borrador_200_perdidas(self):
        calc = CalculadorModelos(Normativa())
        resultado = calc.borrador_200(
            resultado_contable=-10000,
            ajustes_positivos=0,
            ajustes_negativos=0,
            bases_negativas_anteriores=0,
            pagos_a_cuenta=0,
            ejercicio=2025)
        assert resultado["base_imponible"] == -10000
        assert resultado["cuota_integra"] == 0
        assert resultado["a_ingresar"] == 0


class TestInformeRendimientos:
    """Asistido: datos del negocio para modelo 100."""

    def test_informe_rendimientos(self):
        calc = CalculadorModelos(Normativa())
        resultado = calc.informe_rendimientos_actividad(
            ingresos=80000, gastos=40000,
            amortizaciones=5000, ejercicio=2025)
        assert resultado["rendimiento_neto"] == 35000
        assert resultado["tipo"] == "asistido"


class TestModelo190:
    """Automatico: resumen anual retenciones IRPF."""

    def _perceptor(self, nif, nombre, percepcion, retencion, clave="A"):
        return {
            "nif": nif,
            "nombre": nombre,
            "clave_percepcion": clave,
            "subclave": "01",
            "percepcion_dineraria": percepcion,
            "retencion_dineraria": retencion,
            "porcentaje_retencion": round(retencion / percepcion * 100, 2) if percepcion else 0,
            "ejercicio_devengo": 2025,
            "naturaleza": "F",
        }

    def test_190_basico(self):
        calc = CalculadorModelos(Normativa())
        perceptores = [
            self._perceptor("12345678A", "GARCIA JUAN", 24000, 3600),
            self._perceptor("87654321B", "LOPEZ ANA", 18000, 2700),
        ]
        resultado = calc.calcular_190(perceptores, ejercicio=2025)
        assert resultado["modelo"] == "190"
        assert resultado["num_registros"] == 2
        assert resultado["casilla_16"] == 42000.00
        assert resultado["casilla_18"] == 6300.00
        assert resultado["tipo"] == "automatico"

    def test_190_mezcla_trabajo_profesional(self):
        calc = CalculadorModelos(Normativa())
        perceptores = [
            self._perceptor("12345678A", "EMPLEADO S.A.", 24000, 3600, clave="A"),
            self._perceptor("99887766C", "ASESOR FISCAL", 5000, 750, clave="E"),
        ]
        resultado = calc.calcular_190(perceptores, ejercicio=2025)
        assert resultado["num_registros"] == 2
        assert resultado["casilla_16"] == 29000.00
        assert resultado["casilla_18"] == 4350.00

    def test_190_sin_perceptores(self):
        calc = CalculadorModelos(Normativa())
        resultado = calc.calcular_190([], ejercicio=2025)
        assert resultado["num_registros"] == 0
        assert resultado["casilla_16"] == 0.0
        assert resultado["casilla_18"] == 0.0

    def test_190_decimales_redondeo(self):
        calc = CalculadorModelos(Normativa())
        perceptores = [self._perceptor("11111111H", "TRABAJADOR", 1000.333, 150.111)]
        resultado = calc.calcular_190(perceptores, ejercicio=2025)
        assert resultado["casilla_16"] == 1000.33
        assert resultado["casilla_18"] == 150.11
