"""Tests para sfce.normativa.vigente — parametros fiscales multi-territorio."""
from datetime import date

import pytest

from sfce.normativa.vigente import Normativa


class TestPeninsula:
    def setup_method(self):
        self.n = Normativa()

    def test_iva_general(self):
        assert self.n.iva_general(date(2025, 6, 15)) == 21.0

    def test_iva_reducido(self):
        assert self.n.iva_reducido(date(2025, 6, 15)) == 10.0

    def test_iva_superreducido(self):
        assert self.n.iva_superreducido(date(2025, 6, 15)) == 4.0

    def test_recargo_equivalencia_general(self):
        assert self.n.recargo_equivalencia("general", date(2025, 6, 15)) == 5.2

    def test_tipo_is_general(self):
        assert self.n.tipo_is("general", date(2025, 6, 15)) == 25

    def test_tipo_is_pymes(self):
        assert self.n.tipo_is("pymes", date(2025, 6, 15)) == 23

    def test_retencion_profesional(self):
        assert self.n.retencion_profesional(False, date(2025, 6, 15)) == 15

    def test_retencion_profesional_nuevo(self):
        assert self.n.retencion_profesional(True, date(2025, 6, 15)) == 7

    def test_umbral_modelo_347(self):
        assert self.n.umbral("modelo_347", date(2025, 6, 15)) == 3005.06

    def test_smi_mensual(self):
        assert self.n.smi_mensual(date(2025, 6, 15)) == 1134.00

    def test_plazo_303_t1(self):
        plazo = self.n.plazo_presentacion("303", "T1", 2025)
        assert plazo["desde"] == "04-01"
        assert plazo["hasta"] == "04-20"

    def test_pago_fraccionado_130(self):
        assert self.n.pago_fraccionado_130(date(2025, 6, 15)) == 20

    def test_tabla_amortizacion_vehiculos(self):
        tabla = self.n.tabla_amortizacion("vehiculos", date(2025, 6, 15))
        assert tabla["pct_maximo_lineal"] == 16

    def test_ss_cc_empresa(self):
        ss = self.n.seguridad_social(date(2025, 6, 15))
        assert ss["tipo_contingencias_comunes_empresa"] == 23.60


class TestCanarias:
    def setup_method(self):
        self.n = Normativa()

    def test_igic_general(self):
        imp = self.n.impuesto_indirecto(date(2025, 6, 15), "canarias")
        assert imp["general"] == 7

    def test_igic_reducido(self):
        imp = self.n.impuesto_indirecto(date(2025, 6, 15), "canarias")
        assert imp["reducido"] == 3

    def test_igic_tipo_cero(self):
        imp = self.n.impuesto_indirecto(date(2025, 6, 15), "canarias")
        assert imp["tipo_cero"] == 0


class TestNavarra:
    def setup_method(self):
        self.n = Normativa()

    def test_is_general(self):
        assert self.n.tipo_is("general", date(2025, 6, 15), "navarra") == 28

    def test_is_micro(self):
        assert self.n.tipo_is("micro", date(2025, 6, 15), "navarra") == 20

    def test_irpf_primer_tramo(self):
        tabla = self.n.tabla_irpf(date(2025, 6, 15), "navarra")
        assert tabla[0]["tipo"] == 13


class TestPaisVasco:
    def setup_method(self):
        self.n = Normativa()

    def test_is_general(self):
        assert self.n.tipo_is("general", date(2025, 6, 15), "pais_vasco") == 24

    def test_irpf_primer_tramo(self):
        tabla = self.n.tabla_irpf(date(2025, 6, 15), "pais_vasco")
        assert tabla[0]["tipo"] == 23


class TestCeutaMelilla:
    def setup_method(self):
        self.n = Normativa()

    def test_ipsi_general(self):
        imp = self.n.impuesto_indirecto(date(2025, 6, 15), "ceuta_melilla")
        assert imp["tipo_6"] == 10.0


class TestFallbacks:
    def setup_method(self):
        self.n = Normativa()

    def test_ano_no_existente_usa_mas_reciente(self):
        resultado = self.n.iva_general(date(2030, 1, 1))
        assert isinstance(resultado, float)

    def test_territorio_default_es_peninsula(self):
        assert self.n.tipo_is("general", date(2025, 6, 15)) == 25
