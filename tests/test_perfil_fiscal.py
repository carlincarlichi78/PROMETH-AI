"""Tests para sfce.core.perfil_fiscal — derivacion automatica de modelos y libros."""
import pytest
from sfce.core.perfil_fiscal import PerfilFiscal


class TestSL:
    def test_sl_basica(self):
        pf = PerfilFiscal(tipo_persona="juridica", forma_juridica="sl")
        assert pf.tipo_is == 25
        assert pf.deposita_cuentas is True
        assert pf.impuesto_indirecto == "iva"

    def test_sl_modelos_obligatorios(self):
        pf = PerfilFiscal(tipo_persona="juridica", forma_juridica="sl",
                          retiene_profesionales=True)
        modelos = pf.modelos_obligatorios()
        assert "303" in modelos["trimestrales"]
        assert "111" in modelos["trimestrales"]
        assert "390" in modelos["anuales"]
        assert "190" in modelos["anuales"]
        assert "200" in modelos["anuales"]
        assert "347" in modelos["anuales"]
        # SL no tiene IRPF
        assert "130" not in modelos["trimestrales"]
        assert "100" not in modelos["anuales"]

    def test_sl_pymes_is(self):
        pf = PerfilFiscal(tipo_persona="juridica", forma_juridica="sl",
                          tipo_is=23)
        assert pf.tipo_is == 23


class TestAutonomo:
    def test_autonomo_directa(self):
        pf = PerfilFiscal(tipo_persona="fisica", forma_juridica="autonomo",
                          regimen_irpf="directa_simplificada")
        modelos = pf.modelos_obligatorios()
        assert "303" in modelos["trimestrales"]
        assert "130" in modelos["trimestrales"]
        assert "390" in modelos["anuales"]
        assert "100" in modelos["anuales"]
        # Autonomo no tiene IS
        assert "200" not in modelos["anuales"]

    def test_autonomo_modulos(self):
        pf = PerfilFiscal(tipo_persona="fisica", forma_juridica="autonomo",
                          regimen_irpf="objetiva")
        modelos = pf.modelos_obligatorios()
        assert "131" in modelos["trimestrales"]
        assert "130" not in modelos["trimestrales"]

    def test_profesional_con_retencion(self):
        pf = PerfilFiscal(tipo_persona="fisica", forma_juridica="profesional",
                          regimen_irpf="directa_simplificada",
                          retencion_emitidas=True, pct_retencion_emitidas=15)
        assert pf.retencion_emitidas is True
        assert pf.pct_retencion_emitidas == 15


class TestTerritorios:
    def test_canarias_igic(self):
        pf = PerfilFiscal(tipo_persona="fisica", forma_juridica="autonomo",
                          territorio="canarias")
        assert pf.impuesto_indirecto == "igic"
        modelos = pf.modelos_obligatorios()
        assert "420" in modelos["trimestrales"]
        assert "303" not in modelos["trimestrales"]

    def test_ceuta_melilla_ipsi(self):
        pf = PerfilFiscal(tipo_persona="juridica", forma_juridica="sl",
                          territorio="ceuta_melilla")
        assert pf.impuesto_indirecto == "ipsi"

    def test_navarra_peninsula_mismo_iva(self):
        pf = PerfilFiscal(tipo_persona="juridica", forma_juridica="sl",
                          territorio="navarra")
        assert pf.impuesto_indirecto == "iva"
        modelos = pf.modelos_obligatorios()
        assert "303" in modelos["trimestrales"]


class TestOperacionesEspeciales:
    def test_intracomunitario(self):
        pf = PerfilFiscal(tipo_persona="juridica", forma_juridica="sl",
                          operador_intracomunitario=True)
        modelos = pf.modelos_obligatorios()
        assert "349" in modelos["trimestrales"]

    def test_gran_empresa_mensual(self):
        pf = PerfilFiscal(tipo_persona="juridica", forma_juridica="sa",
                          gran_empresa=True)
        assert pf.periodicidad == "mensual"

    def test_pagos_fraccionados_is(self):
        pf = PerfilFiscal(tipo_persona="juridica", forma_juridica="sl",
                          pagos_fraccionados_is=True)
        modelos = pf.modelos_obligatorios()
        assert "202" in modelos["trimestrales"]


class TestRegimenesIVA:
    def test_recargo_equivalencia(self):
        pf = PerfilFiscal(tipo_persona="fisica", forma_juridica="autonomo",
                          regimen_iva="recargo_equivalencia")
        assert pf.regimen_iva == "recargo_equivalencia"

    def test_exento_sin_303(self):
        pf = PerfilFiscal(tipo_persona="juridica", forma_juridica="asociacion",
                          regimen_iva="exento")
        modelos = pf.modelos_obligatorios()
        assert "303" not in modelos["trimestrales"]
        assert "390" not in modelos["anuales"]

    def test_comunidad_propietarios(self):
        pf = PerfilFiscal(tipo_persona="juridica",
                          forma_juridica="comunidad_propietarios",
                          regimen_iva="exento")
        modelos = pf.modelos_obligatorios()
        assert "200" not in modelos["anuales"]  # no IS


class TestLibros:
    def test_libros_autonomo(self):
        pf = PerfilFiscal(tipo_persona="fisica", forma_juridica="autonomo",
                          regimen_irpf="directa_simplificada")
        libros = pf.libros_obligatorios()
        assert "registro_facturas_emitidas" in libros
        assert "registro_facturas_recibidas" in libros
        assert "libro_bienes_inversion" in libros

    def test_libros_sl(self):
        pf = PerfilFiscal(tipo_persona="juridica", forma_juridica="sl")
        libros = pf.libros_obligatorios()
        assert "libro_diario" in libros
        assert "libro_inventarios_cuentas_anuales" in libros


class TestDesdeDict:
    def test_desde_dict(self):
        datos = {
            "tipo_persona": "juridica",
            "forma_juridica": "sl",
            "territorio": "peninsula",
            "retiene_profesionales": True,
        }
        pf = PerfilFiscal.desde_dict(datos)
        assert pf.forma_juridica == "sl"
        assert pf.retiene_profesionales is True

    def test_desde_dict_minimo(self):
        pf = PerfilFiscal.desde_dict({"tipo_persona": "fisica",
                                       "forma_juridica": "autonomo"})
        assert pf.tipo_persona == "fisica"


class TestValidaciones:
    def test_juridica_sin_irpf(self):
        pf = PerfilFiscal(tipo_persona="juridica", forma_juridica="sl")
        assert pf.regimen_irpf is None

    def test_fisica_sin_is(self):
        pf = PerfilFiscal(tipo_persona="fisica", forma_juridica="autonomo")
        assert pf.tipo_is is None
        assert pf.pagos_fraccionados_is is False
