"""Tests para sfce.core.operaciones_periodicas — amortizacion, provisiones, regularizacion IVA."""
import pytest
from sfce.core.operaciones_periodicas import OperacionesPeriodicas
from sfce.normativa.vigente import Normativa


class TestAmortizacion:
    def test_cuota_mensual_lineal(self):
        op = OperacionesPeriodicas(Normativa())
        cuota = op.cuota_amortizacion_mensual(
            valor_adquisicion=30000, valor_residual=0, pct_amortizacion=16)
        assert cuota == 400.0  # 30000 * 16% / 12

    def test_cuota_con_residual(self):
        op = OperacionesPeriodicas(Normativa())
        cuota = op.cuota_amortizacion_mensual(
            valor_adquisicion=30000, valor_residual=6000, pct_amortizacion=16)
        # (30000 - 6000) * 16% / 12 = 320.0
        assert cuota == 320.0

    def test_asiento_amortizacion(self):
        op = OperacionesPeriodicas(Normativa())
        partidas = op.generar_asiento_amortizacion(
            tipo_bien="vehiculos", valor=30000, residual=0,
            pct=16, subcuenta_activo="2180000000")
        assert len(partidas) == 2
        assert partidas[0].subcuenta == "6810000000"  # gasto amortizacion
        assert partidas[0].debe == 400.0
        assert partidas[1].subcuenta == "2810000000"  # amortizacion acumulada
        assert partidas[1].haber == 400.0

    def test_asiento_amortizacion_equipos(self):
        op = OperacionesPeriodicas(Normativa())
        partidas = op.generar_asiento_amortizacion(
            tipo_bien="equipos_informaticos", valor=1200, residual=0,
            pct=25, subcuenta_activo="2170000000")
        assert partidas[0].debe == 25.0  # 1200 * 25% / 12


class TestProvisionPagasExtras:
    def test_14_pagas(self):
        op = OperacionesPeriodicas(Normativa())
        provision = op.provision_paga_extra_mensual(
            bruto_mensual=2500, pagas=14)
        # 2 pagas extra. Provision mensual = 2500 * 2 / 12 = 416.67
        assert abs(provision - 416.67) < 0.01

    def test_12_pagas_sin_provision(self):
        op = OperacionesPeriodicas(Normativa())
        provision = op.provision_paga_extra_mensual(
            bruto_mensual=2500, pagas=12)
        assert provision == 0.0

    def test_15_pagas(self):
        op = OperacionesPeriodicas(Normativa())
        provision = op.provision_paga_extra_mensual(
            bruto_mensual=2000, pagas=15)
        # 3 pagas extra. 2000 * 3 / 12 = 500.0
        assert provision == 500.0

    def test_asiento_provision_paga(self):
        op = OperacionesPeriodicas(Normativa())
        partidas = op.generar_asiento_provision_paga(
            bruto_mensual=2500, pagas=14)
        assert len(partidas) == 2
        assert partidas[0].subcuenta == "6400000000"  # sueldos
        assert partidas[0].debe == 416.67
        assert partidas[1].subcuenta == "4650000000"  # remuneraciones pendientes
        assert partidas[1].haber == 416.67

    def test_asiento_provision_12_pagas_vacio(self):
        op = OperacionesPeriodicas(Normativa())
        partidas = op.generar_asiento_provision_paga(
            bruto_mensual=2500, pagas=12)
        assert len(partidas) == 0


class TestRegularizacionIVA:
    def test_iva_a_pagar(self):
        op = OperacionesPeriodicas(Normativa())
        partidas = op.generar_regularizacion_iva(
            iva_repercutido=5000, iva_soportado=3000)
        assert len(partidas) == 3
        # 477 DEBE 5000, 472 HABER 3000, 4750 HABER 2000
        assert any(p.subcuenta == "4770000000" and p.debe == 5000 for p in partidas)
        assert any(p.subcuenta == "4720000000" and p.haber == 3000 for p in partidas)
        assert any(p.subcuenta == "4750000000" and p.haber == 2000 for p in partidas)

    def test_iva_a_compensar(self):
        op = OperacionesPeriodicas(Normativa())
        partidas = op.generar_regularizacion_iva(
            iva_repercutido=3000, iva_soportado=5000)
        assert any(p.subcuenta == "4700000000" and p.debe == 2000 for p in partidas)

    def test_iva_neutro(self):
        op = OperacionesPeriodicas(Normativa())
        partidas = op.generar_regularizacion_iva(
            iva_repercutido=3000, iva_soportado=3000)
        # Solo 2 partidas (477 debe, 472 haber), sin saldo
        assert len(partidas) == 2

    def test_iva_con_prorrata(self):
        op = OperacionesPeriodicas(Normativa())
        partidas = op.generar_regularizacion_iva(
            iva_repercutido=5000, iva_soportado=3000, prorrata=80)
        # IVA no deducible = 3000 * 20% = 600 -> gasto
        assert any(p.subcuenta == "6340000000" and p.debe == 600 for p in partidas)


class TestPeriodificacion:
    def test_gasto_anticipado(self):
        op = OperacionesPeriodicas(Normativa())
        partidas = op.generar_periodificacion(
            importe=1200, subcuenta_gasto="6250000000",
            meses_restantes=3, meses_totales=12)
        # 1200 * 3/12 = 300 -> periodificacion
        assert len(partidas) == 2
        assert partidas[0].subcuenta == "4800000000"  # gastos anticipados
        assert partidas[0].debe == 300.0
        assert partidas[1].subcuenta == "6250000000"
        assert partidas[1].haber == 300.0
