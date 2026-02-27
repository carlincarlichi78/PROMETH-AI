"""Tests de integracion Fase B — motor central completo."""
from datetime import date

import pytest

from sfce.core.config import ConfigCliente
from sfce.core.motor_reglas import MotorReglas
from sfce.core.clasificador import Clasificador
from sfce.core.decision import DecisionContable
from sfce.core.calculador_modelos import CalculadorModelos
from sfce.core.notas_credito import ProcesadorNC
from sfce.normativa.vigente import Normativa


def _config_completa():
    return ConfigCliente({
        "empresa": {"nombre": "Empresa Integracion SL", "cif": "B12345678",
                     "tipo": "sl", "idempresa": 99, "ejercicio_activo": "2025"},
        "perfil_fiscal": {
            "tipo_persona": "juridica",
            "forma_juridica": "sl",
            "retiene_profesionales": True,
        },
        "proveedores": {
            "telefonica": {"cif": "A28015865",
                           "subcuenta": "6280000000", "codimpuesto": "IVA21"},
            "oceanline": {"cif": "DK12345678",
                          "subcuenta": "6000000000", "codimpuesto": "IVA0",
                          "regimen": "intracomunitario"},
            "abogado": {"cif": "12345678A",
                        "subcuenta": "6230000000", "codimpuesto": "IVA21",
                        "retencion": 15},
        },
    }, "test")


class TestFlujoCompletoFactura:
    """Motor + Clasificador + Decision: factura de compra end-to-end."""

    def test_factura_proveedor_conocido(self):
        config = _config_completa()
        motor = MotorReglas(config)

        # 1. Motor decide
        doc = {"emisor_cif": "A28015865", "tipo_doc": "FC",
               "concepto": "Linea telefonica", "base_imponible": 200}
        decision = motor.decidir_asiento(doc)

        # 2. Verificar decision
        assert decision.subcuenta_gasto == "6280000000"
        assert decision.codimpuesto == "IVA21"
        assert decision.confianza == 95
        assert not decision.cuarentena

        # 3. Generar partidas
        partidas = decision.generar_partidas(base=200)
        assert len(partidas) == 3  # gasto + IVA + proveedor
        total_debe = sum(p.debe for p in partidas)
        total_haber = sum(p.haber for p in partidas)
        assert abs(total_debe - total_haber) < 0.01

        # 4. Validar
        errores = motor.validar_asiento(decision)
        assert len(errores) == 0

    def test_factura_intracomunitaria_isp(self):
        config = _config_completa()
        motor = MotorReglas(config)

        doc = {"emisor_cif": "DK12345678", "tipo_doc": "FC",
               "concepto": "Transporte maritimo", "base_imponible": 1000}
        decision = motor.decidir_asiento(doc)

        assert decision.isp is True
        partidas = decision.generar_partidas(base=1000)
        # ISP: gasto + 472 soportado + 477 repercutido + proveedor
        iva_sop = [p for p in partidas if "472" in p.subcuenta]
        iva_rep = [p for p in partidas if "477" in p.subcuenta]
        assert len(iva_sop) == 1
        assert len(iva_rep) == 1
        assert iva_sop[0].debe == 210.0
        assert iva_rep[0].haber == 210.0

    def test_factura_profesional_con_retencion(self):
        config = _config_completa()
        motor = MotorReglas(config)

        doc = {"emisor_cif": "12345678A", "tipo_doc": "FC",
               "concepto": "Honorarios juridicos", "base_imponible": 2000}
        decision = motor.decidir_asiento(doc)

        assert decision.retencion_pct == 15.0
        partidas = decision.generar_partidas(base=2000)
        ret = [p for p in partidas if "475" in p.subcuenta]
        assert ret[0].haber == 300.0  # 2000 * 15%

        total_debe = sum(p.debe for p in partidas)
        total_haber = sum(p.haber for p in partidas)
        assert abs(total_debe - total_haber) < 0.01


class TestFlujoDesconocidoCuarentena:
    """Proveedor desconocido -> cuarentena -> aprendizaje -> siguiente OK."""

    def test_cuarentena_y_aprendizaje(self):
        config = _config_completa()
        motor = MotorReglas(config)

        # 1. Primera vez: cuarentena
        doc = {"emisor_cif": "B99999999", "tipo_doc": "FC",
               "concepto": "Factura desconocida", "base_imponible": 500}
        d1 = motor.decidir_asiento(doc)
        assert d1.cuarentena is True

        # 2. Humano corrige
        motor.aprender(doc, subcuenta="6220000000", codimpuesto="IVA21")

        # 3. Segunda vez: usa aprendizaje
        d2 = motor.decidir_asiento(doc)
        assert d2.subcuenta_gasto == "6220000000"
        assert d2.confianza == 85
        assert not d2.cuarentena


class TestCalculadorConNormativa:
    """Calculador de modelos usa normativa real."""

    def test_303_y_390_coherentes(self):
        n = Normativa()
        calc = CalculadorModelos(n)

        # 4 trimestres
        r303_t1 = calc.calcular_303(1500, 1000, "T1", 2025)
        r303_t2 = calc.calcular_303(2000, 1200, "T2", 2025)
        r303_t3 = calc.calcular_303(1800, 900, "T3", 2025)
        r303_t4 = calc.calcular_303(1700, 1100, "T4", 2025)

        total_rep = 1500 + 2000 + 1800 + 1700
        total_sop = 1000 + 1200 + 900 + 1100
        total_ingresado = sum(r["casilla_69"] for r in
                              [r303_t1, r303_t2, r303_t3, r303_t4])

        # 390 debe cuadrar con suma trimestrales
        r390 = calc.calcular_390(
            total_bases_iva=0,  # no relevante para este check
            total_iva_devengado=total_rep,
            total_iva_deducible=total_sop,
            ejercicio=2025,
            ingresos_trimestrales=total_ingresado)
        assert r390["total_resultado"] == total_rep - total_sop
        assert r390["diferencia_regularizacion"] == 0

    def test_200_con_normativa_peninsula(self):
        n = Normativa()
        calc = CalculadorModelos(n)
        r200 = calc.borrador_200(
            resultado_contable=100000,
            ajustes_positivos=0, ajustes_negativos=0,
            bases_negativas_anteriores=0,
            pagos_a_cuenta=10000,
            ejercicio=2025)
        assert r200["tipo_is"] == 25
        assert r200["cuota_integra"] == 25000
        assert r200["a_ingresar"] == 15000


class TestNCConMotor:
    """Nota de credito: buscar + generar inverso."""

    def test_nc_flujo_completo(self):
        proc = ProcesadorNC()
        config = _config_completa()
        motor = MotorReglas(config)

        # Factura original
        doc_fc = {"emisor_cif": "A28015865", "tipo_doc": "FC",
                  "concepto": "Servicio", "base_imponible": 1000}
        decision_fc = motor.decidir_asiento(doc_fc)
        partidas_fc = decision_fc.generar_partidas(base=1000)

        # Convertir Partida -> dict
        partidas_dict = [{"codsubcuenta": p.subcuenta,
                          "debe": p.debe, "haber": p.haber,
                          "concepto": p.concepto} for p in partidas_fc]

        # NC total
        nc_partidas = proc.generar_asiento_inverso(
            partidas_dict, importe_nc=1210, total_original=1210)

        # Cuadre
        total_debe = sum(p["debe"] for p in nc_partidas)
        total_haber = sum(p["haber"] for p in nc_partidas)
        assert abs(total_debe - total_haber) < 0.01

        # Inversas
        gasto_nc = [p for p in nc_partidas if "628" in p["codsubcuenta"]][0]
        assert gasto_nc["haber"] == 1000  # gasto original era DEBE, NC en HABER


class TestImportsTodosFaseB:
    """Todos los modulos de Fase B son importables."""

    def test_clasificador(self):
        from sfce.core.clasificador import Clasificador, ResultadoClasificacion

    def test_motor_reglas(self):
        from sfce.core.motor_reglas import MotorReglas

    def test_calculador_modelos(self):
        from sfce.core.calculador_modelos import CalculadorModelos

    def test_notas_credito(self):
        from sfce.core.notas_credito import ProcesadorNC

    def test_pipeline_importa(self):
        from scripts.pipeline import main
