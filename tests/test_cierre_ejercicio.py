"""Tests para sfce.core.cierre_ejercicio — regularizacion, IS, cierre, apertura."""
import pytest
from sfce.core.cierre_ejercicio import CierreEjercicio


class TestRegularizacion:
    def test_regularizacion_beneficio(self):
        """Cierra cuentas 6xx y 7xx contra 129 — beneficio."""
        cierre = CierreEjercicio()
        saldos = {
            "6000000000": {"debe": 50000, "haber": 0},     # compras
            "6420000000": {"debe": 10000, "haber": 0},     # SS empresa
            "7000000000": {"debe": 0, "haber": 80000},     # ventas
        }
        partidas = cierre.generar_regularizacion(saldos)
        # 600 HABER 50000, 642 HABER 10000, 700 DEBE 80000
        # 129 = 80000 - 60000 = 20000 beneficio (HABER)
        cuenta_129 = [p for p in partidas if "129" in p.subcuenta]
        assert len(cuenta_129) == 1
        assert cuenta_129[0].haber == 20000

    def test_regularizacion_perdida(self):
        """Cierra cuentas 6xx y 7xx contra 129 — perdida."""
        cierre = CierreEjercicio()
        saldos = {
            "6000000000": {"debe": 80000, "haber": 0},
            "7000000000": {"debe": 0, "haber": 50000},
        }
        partidas = cierre.generar_regularizacion(saldos)
        cuenta_129 = [p for p in partidas if "129" in p.subcuenta]
        assert cuenta_129[0].debe == 30000  # perdida al DEBE

    def test_regularizacion_ignora_cuentas_patrimoniales(self):
        """Solo cierra 6xx y 7xx, ignora el resto."""
        cierre = CierreEjercicio()
        saldos = {
            "5720000000": {"debe": 30000, "haber": 0},     # bancos — NO tocar
            "6000000000": {"debe": 50000, "haber": 0},
            "7000000000": {"debe": 0, "haber": 80000},
        }
        partidas = cierre.generar_regularizacion(saldos)
        subcuentas = [p.subcuenta for p in partidas]
        assert "5720000000" not in subcuentas

    def test_regularizacion_cuadre(self):
        cierre = CierreEjercicio()
        saldos = {
            "6000000000": {"debe": 50000, "haber": 0},
            "6200000000": {"debe": 15000, "haber": 0},
            "6420000000": {"debe": 10000, "haber": 0},
            "7000000000": {"debe": 0, "haber": 100000},
            "7590000000": {"debe": 0, "haber": 5000},
        }
        partidas = cierre.generar_regularizacion(saldos)
        total_debe = sum(p.debe for p in partidas)
        total_haber = sum(p.haber for p in partidas)
        assert abs(total_debe - total_haber) < 0.01


class TestGastoIS:
    def test_impuesto_sociedades(self):
        cierre = CierreEjercicio()
        partidas = cierre.generar_gasto_is(base_imponible=120000, tipo_is=25)
        assert len(partidas) == 2
        assert partidas[0].subcuenta == "6300000000"  # gasto IS
        assert partidas[0].debe == 30000
        assert partidas[1].subcuenta == "4752000000"  # HP acreedora IS
        assert partidas[1].haber == 30000

    def test_is_pymes_23(self):
        cierre = CierreEjercicio()
        partidas = cierre.generar_gasto_is(base_imponible=100000, tipo_is=23)
        assert partidas[0].debe == 23000

    def test_is_perdida_sin_asiento(self):
        cierre = CierreEjercicio()
        partidas = cierre.generar_gasto_is(base_imponible=-5000, tipo_is=25)
        assert len(partidas) == 0  # No hay IS con base negativa


class TestCierre:
    def test_cierre_cuadra(self):
        """Cierra TODAS las cuentas a 0."""
        cierre = CierreEjercicio()
        saldos = {
            "1000000000": {"debe": 0, "haber": 50000},     # capital
            "1290000000": {"debe": 0, "haber": 20000},     # resultado
            "5720000000": {"debe": 60000, "haber": 0},     # bancos
            "4000000001": {"debe": 0, "haber": 10000},     # proveedor
            "4300000001": {"debe": 20000, "haber": 0},     # cliente
        }
        partidas = cierre.generar_cierre(saldos)
        total_debe = sum(p.debe for p in partidas)
        total_haber = sum(p.haber for p in partidas)
        assert abs(total_debe - total_haber) < 0.01

    def test_cierre_invierte_saldos(self):
        """Cada cuenta se cierra invirtiendo su saldo."""
        cierre = CierreEjercicio()
        saldos = {
            "5720000000": {"debe": 30000, "haber": 0},
        }
        partidas = cierre.generar_cierre(saldos)
        # Bancos tiene saldo deudor -> cierra al haber
        assert partidas[0].subcuenta == "5720000000"
        assert partidas[0].haber == 30000


class TestApertura:
    def test_apertura_inverso_del_cierre(self):
        """Apertura = inverso del cierre."""
        cierre = CierreEjercicio()
        saldos = {
            "1000000000": {"debe": 0, "haber": 50000},
            "5720000000": {"debe": 30000, "haber": 0},
            "4300000001": {"debe": 20000, "haber": 0},
        }
        partidas = cierre.generar_apertura(saldos)
        # Lo que era HABER ahora es HABER (se reabre igual)
        assert any(p.subcuenta == "1000000000" and p.haber == 50000 for p in partidas)
        assert any(p.subcuenta == "5720000000" and p.debe == 30000 for p in partidas)

    def test_apertura_cuadra(self):
        cierre = CierreEjercicio()
        saldos = {
            "1000000000": {"debe": 0, "haber": 50000},
            "5720000000": {"debe": 60000, "haber": 0},
            "4000000001": {"debe": 0, "haber": 10000},
            "4300000001": {"debe": 20000, "haber": 0},
            "1290000000": {"debe": 0, "haber": 20000},
        }
        partidas = cierre.generar_apertura(saldos)
        total_debe = sum(p.debe for p in partidas)
        total_haber = sum(p.haber for p in partidas)
        assert abs(total_debe - total_haber) < 0.01
