"""Tests de integracion Fase A — verificar que todos los modulos trabajan juntos."""
from datetime import date

import pytest

from sfce.normativa.vigente import Normativa
from sfce.core.perfil_fiscal import PerfilFiscal
from sfce.core.decision import DecisionContable
from sfce.core.operaciones_periodicas import OperacionesPeriodicas
from sfce.core.cierre_ejercicio import CierreEjercicio
from sfce.core.config import ConfigCliente
from sfce.core.backend import Backend


class TestNormativaAlimentaDecision:
    def test_iva_general_en_decision(self):
        n = Normativa()
        iva = n.iva_general(date(2025, 6, 15))
        decision = DecisionContable(
            subcuenta_gasto="6000000000", subcuenta_contrapartida="4000000001",
            codimpuesto="IVA21", tipo_iva=iva, confianza=95, origen_decision="test")
        partidas = decision.generar_partidas(base=1000.0)
        iva_p = [p for p in partidas if "472" in p.subcuenta][0]
        assert iva_p.debe == 210.0

    def test_normativa_navarra_is(self):
        n = Normativa()
        assert n.tipo_is("general", date(2025, 1, 1), "navarra") == 28

    def test_normativa_canarias_igic(self):
        n = Normativa()
        igic = n.impuesto_indirecto(date(2025, 6, 15), "canarias")
        assert igic["general"] == 7


class TestPerfilCanarias:
    def test_perfil_canarias_igic(self):
        pf = PerfilFiscal(tipo_persona="fisica", forma_juridica="autonomo",
                          territorio="canarias")
        assert pf.impuesto_indirecto == "igic"
        modelos = pf.modelos_obligatorios()
        assert "420" in modelos["trimestrales"]
        assert "303" not in modelos["trimestrales"]


class TestCierreConIS:
    def test_cierre_completo_con_is(self):
        cierre = CierreEjercicio()
        n = Normativa()
        tipo_is = n.tipo_is("general", date(2025, 12, 31))
        partidas_is = cierre.generar_gasto_is(40000, tipo_is)
        assert partidas_is[0].debe == 10000  # 40000 * 25%

    def test_flujo_regularizacion_mas_is(self):
        """Regularizacion -> IS -> cierre: flujo completo."""
        cierre = CierreEjercicio()
        n = Normativa()

        # 1. Regularizacion
        saldos_gyp = {
            "6000000000": {"debe": 60000, "haber": 0},
            "7000000000": {"debe": 0, "haber": 100000},
        }
        partidas_reg = cierre.generar_regularizacion(saldos_gyp)
        # Resultado: 40000 beneficio
        cuenta_129 = [p for p in partidas_reg if "129" in p.subcuenta]
        assert cuenta_129[0].haber == 40000

        # 2. IS
        tipo_is = n.tipo_is("general", date(2025, 12, 31))
        partidas_is = cierre.generar_gasto_is(40000, tipo_is)
        assert partidas_is[0].debe == 10000


class TestAmortizacionConNormativa:
    def test_tabla_normativa_en_amortizacion(self):
        n = Normativa()
        op = OperacionesPeriodicas(n)
        tabla = n.tabla_amortizacion("vehiculos", date(2025, 6, 15))
        partidas = op.generar_asiento_amortizacion(
            tipo_bien="vehiculos", valor=30000, residual=0,
            pct=tabla["pct_maximo_lineal"], subcuenta_activo="2180000000")
        # 30000 * 16% / 12 = 400
        assert partidas[0].debe == 400.0


class TestConfigPerfilDecision:
    def test_config_genera_perfil_que_informa_decision(self):
        """Config -> PerfilFiscal -> informa que modelos y tipo IVA usar."""
        config_data = {
            "empresa": {"nombre": "Test SL", "cif": "B12345678",
                        "tipo": "sl", "idempresa": 99, "ejercicio_activo": "2025"},
            "perfil_fiscal": {
                "tipo_persona": "juridica",
                "forma_juridica": "sl",
                "retiene_profesionales": True,
            }
        }
        config = ConfigCliente(config_data, "test")
        pf = config.perfil_fiscal
        modelos = pf.modelos_obligatorios()
        assert "303" in modelos["trimestrales"]
        assert "111" in modelos["trimestrales"]
        assert "200" in modelos["anuales"]


class TestImportsPipeline:
    def test_sfce_core_importable(self):
        from sfce.core import logger, errors, config, confidence
        from sfce.core import fs_api, aritmetica, reglas_pgc, prompts

    def test_sfce_phases_importable(self):
        from sfce.phases import intake, pre_validation, registration
        from sfce.phases import asientos, correction, cross_validation, output

    def test_sfce_nuevos_modulos_importable(self):
        from sfce.normativa.vigente import Normativa
        from sfce.core.perfil_fiscal import PerfilFiscal
        from sfce.core.decision import DecisionContable, Partida
        from sfce.core.backend import Backend
        from sfce.core.operaciones_periodicas import OperacionesPeriodicas
        from sfce.core.cierre_ejercicio import CierreEjercicio
