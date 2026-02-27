"""Tests para sfce.core.decision — DecisionContable con trazabilidad."""
import pytest
from sfce.core.decision import DecisionContable, Partida


class TestCrearDecision:
    def test_decision_basica(self):
        decision = DecisionContable(
            subcuenta_gasto="6000000000",
            subcuenta_contrapartida="4000000001",
            codimpuesto="IVA21", tipo_iva=21.0,
            confianza=95, origen_decision="regla_cliente")
        assert decision.cuarentena is False
        assert decision.subcuenta_gasto == "6000000000"

    def test_cuarentena_baja_confianza(self):
        decision = DecisionContable(
            subcuenta_gasto="6220000000",
            subcuenta_contrapartida="4000000001",
            codimpuesto="IVA21", tipo_iva=21.0,
            confianza=50, origen_decision="ocr_keywords")
        assert decision.cuarentena is True
        assert "50%" in decision.motivo_cuarentena


class TestGenerarPartidas:
    def test_general_3_partidas(self):
        decision = DecisionContable(
            subcuenta_gasto="6000000000",
            subcuenta_contrapartida="4000000001",
            codimpuesto="IVA21", tipo_iva=21.0,
            confianza=95, origen_decision="test")
        partidas = decision.generar_partidas(base=1000.0)
        assert len(partidas) == 3  # gasto + IVA + proveedor
        total_debe = sum(p.debe for p in partidas)
        total_haber = sum(p.haber for p in partidas)
        assert abs(total_debe - total_haber) < 0.01

    def test_general_importes_correctos(self):
        decision = DecisionContable(
            subcuenta_gasto="6000000000",
            subcuenta_contrapartida="4000000001",
            codimpuesto="IVA21", tipo_iva=21.0,
            confianza=95, origen_decision="test")
        partidas = decision.generar_partidas(base=1000.0)
        gasto = [p for p in partidas if "600" in p.subcuenta][0]
        iva = [p for p in partidas if "472" in p.subcuenta][0]
        prov = [p for p in partidas if "400" in p.subcuenta][0]
        assert gasto.debe == 1000.0
        assert iva.debe == 210.0
        assert prov.haber == 1210.0

    def test_iva0_2_partidas(self):
        decision = DecisionContable(
            subcuenta_gasto="6000000000",
            subcuenta_contrapartida="4000000001",
            codimpuesto="IVA0", tipo_iva=0.0,
            confianza=95, origen_decision="test")
        partidas = decision.generar_partidas(base=500.0)
        assert len(partidas) == 2  # gasto + proveedor (sin IVA)
        assert partidas[0].debe == 500.0
        assert partidas[1].haber == 500.0

    def test_con_retencion(self):
        decision = DecisionContable(
            subcuenta_gasto="6230000000",
            subcuenta_contrapartida="4000000001",
            codimpuesto="IVA21", tipo_iva=21.0,
            retencion_pct=15.0,
            confianza=95, origen_decision="test")
        partidas = decision.generar_partidas(base=1000.0)
        # 4 partidas: gasto + IVA + retencion + proveedor
        assert len(partidas) == 4
        ret = [p for p in partidas if "475" in p.subcuenta][0]
        assert ret.haber == 150.0
        prov = [p for p in partidas if "400" in p.subcuenta][0]
        # proveedor = 1210 - 150 = 1060
        assert prov.haber == 1060.0
        total_debe = sum(p.debe for p in partidas)
        total_haber = sum(p.haber for p in partidas)
        assert abs(total_debe - total_haber) < 0.01

    def test_recargo_equivalencia(self):
        decision = DecisionContable(
            subcuenta_gasto="6000000000",
            subcuenta_contrapartida="4000000001",
            codimpuesto="IVA21", tipo_iva=21.0,
            recargo_equiv=5.2,
            confianza=95, origen_decision="test")
        partidas = decision.generar_partidas(base=1000.0)
        # 4 partidas: gasto + IVA + recargo + proveedor
        assert len(partidas) == 4
        recargo = [p for p in partidas if p.concepto and "Recargo" in p.concepto][0]
        assert recargo.debe == 52.0
        prov = [p for p in partidas if "400" in p.subcuenta][0]
        # 1000 + 210 + 52 = 1262
        assert prov.haber == 1262.0

    def test_isp_autorepercusion(self):
        decision = DecisionContable(
            subcuenta_gasto="6000000000",
            subcuenta_contrapartida="4000000001",
            codimpuesto="IVA0", tipo_iva=0.0,
            isp=True, isp_tipo_iva=21.0,
            confianza=95, origen_decision="test")
        partidas = decision.generar_partidas(base=1000.0)
        # gasto + IVA soportado ISP + IVA repercutido ISP + proveedor
        iva_sop = [p for p in partidas if "472" in p.subcuenta]
        iva_rep = [p for p in partidas if "477" in p.subcuenta]
        assert len(iva_sop) == 1
        assert len(iva_rep) == 1
        assert iva_sop[0].debe == 210.0
        assert iva_rep[0].haber == 210.0
        # Proveedor solo paga base (sin IVA en factura)
        prov = [p for p in partidas if "400" in p.subcuenta][0]
        assert prov.haber == 1000.0

    def test_iva_parcial_50(self):
        decision = DecisionContable(
            subcuenta_gasto="6290000000",
            subcuenta_contrapartida="4000000001",
            codimpuesto="IVA21", tipo_iva=21.0,
            pct_iva_deducible=50.0,
            confianza=95, origen_decision="regla_cliente")
        partidas = decision.generar_partidas(base=100.0)
        gasto = [p for p in partidas if "629" in p.subcuenta][0]
        # 100 + 10.50 IVA no deducible = 110.50
        assert gasto.debe == 110.50
        iva = [p for p in partidas if "472" in p.subcuenta][0]
        # Solo 50% deducible
        assert iva.debe == 10.50
        # Cuadre
        total_debe = sum(p.debe for p in partidas)
        total_haber = sum(p.haber for p in partidas)
        assert abs(total_debe - total_haber) < 0.01


class TestLogRazonamiento:
    def test_log_se_mantiene(self):
        decision = DecisionContable(
            subcuenta_gasto="6000000000",
            subcuenta_contrapartida="4000000001",
            codimpuesto="IVA21", tipo_iva=21.0,
            confianza=95, origen_decision="regla_cliente",
            log_razonamiento=["1. Regla cliente: CIF B99 -> 600",
                              "2. IVA general 21%"])
        assert len(decision.log_razonamiento) == 2
        assert "Regla cliente" in decision.log_razonamiento[0]


class TestToDict:
    def test_serializable(self):
        decision = DecisionContable(
            subcuenta_gasto="6000000000",
            subcuenta_contrapartida="4000000001",
            codimpuesto="IVA21", tipo_iva=21.0,
            confianza=95, origen_decision="test",
            log_razonamiento=["test log"])
        decision.generar_partidas(base=100.0)
        d = decision.to_dict()
        assert "log_razonamiento" in d
        assert "partidas" in d
        assert len(d["partidas"]) == 3
        assert d["partidas"][0]["subcuenta"] == "6000000000"
        assert d["confianza"] == 95
