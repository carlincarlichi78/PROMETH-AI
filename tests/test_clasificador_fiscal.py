"""Tests del Motor de Clasificación Fiscal (MCF).

Cubre 35 casos: detección país/régimen, categorías, wizard, suplidos,
divisas, confianza, a_entrada_config y ClasificacionFiscal helpers.
"""
from __future__ import annotations

import pytest
from pathlib import Path

from sfce.core.clasificador_fiscal import ClasificadorFiscal, ClasificacionFiscal

# ─────────────────────────── fixture ────────────────────────────────────────

@pytest.fixture(scope="module")
def clf():
    return ClasificadorFiscal()


# ═════════════════════════════════════════════════════════════════════════════
# BLOQUE 1: Detección país y régimen por CIF
# ═════════════════════════════════════════════════════════════════════════════

class TestDeteccionPaisRegimen:
    def test_cif_espanol_letra_b(self, clf):
        r = clf.clasificar("B12345678", "EMPRESA SL", {})
        assert r.pais == "ESP"
        assert r.regimen == "general"

    def test_cif_espanol_letra_a(self, clf):
        r = clf.clasificar("A28000000", "SOCIEDAD ANONIMA SA", {})
        assert r.pais == "ESP"
        assert r.regimen == "general"

    def test_nie_extranjero_residente(self, clf):
        r = clf.clasificar("X1234567Z", "EXTRANJERO RESIDENTE", {})
        assert r.pais == "ESP"
        assert r.tipo_persona == "fisica"

    def test_nie_y_prefijo(self, clf):
        r = clf.clasificar("Y9876543B", "OTRO NIE", {})
        assert r.pais == "ESP"

    def test_cif_vacio_desconocido(self, clf):
        r = clf.clasificar("", "PROVEEDOR SIN CIF", {})
        assert r.pais == "DESCONOCIDO"
        assert r.tipo_persona == "desconocida"
        assert r.confianza < 0.5  # menos confianza sin CIF

    def test_cif_vacio_regimen_desconocido(self, clf):
        r = clf.clasificar("", "PROVEEDOR", {})
        assert r.regimen == "desconocido"

    def test_nif_con_prefijo_es(self, clf):
        r = clf.clasificar("ESB12345678", "EMPRESA CON PREFIJO ES", {})
        assert r.pais == "ESP"
        assert r.regimen == "general"

    def test_persona_fisica_nif(self, clf):
        """NIF numérico → persona física."""
        r = clf.clasificar("12345678Z", "PERSONA FISICA", {})
        assert r.tipo_persona == "fisica"


# ═════════════════════════════════════════════════════════════════════════════
# BLOQUE 2: Categorías de gasto por keywords
# ═════════════════════════════════════════════════════════════════════════════

class TestCategoriasGasto:
    def test_telefono_movistar(self, clf):
        r = clf.clasificar("A80153195", "MOVISTAR TELEFONIA", {})
        assert r.categoria == "suministros_telefono"
        assert r.subcuenta == "6290000000"

    def test_telefono_vodafone(self, clf):
        r = clf.clasificar("A80153195", "VODAFONE ESPANA", {})
        assert r.categoria == "suministros_telefono"

    def test_combustible_repsol(self, clf):
        r = clf.clasificar("A78052469", "REPSOL COMBUSTIBLES", {
            "lineas": [{"descripcion": "Gasoil"}]
        })
        assert r.categoria == "suministros_combustible"
        assert "tipo_vehiculo" in r.preguntas_pendientes

    def test_combustible_linea_gasolina(self, clf):
        r = clf.clasificar("B12345678", "ESTACION SERVICIO", {
            "lineas": [{"descripcion": "Gasolina sin plomo 95"}]
        })
        assert r.categoria == "suministros_combustible"

    def test_electricidad(self, clf):
        r = clf.clasificar("A81948077", "ENDESA ENERGIA", {})
        assert r.categoria == "suministros_electricidad"
        assert r.subcuenta == "6280000000"

    def test_correos_exento(self, clf):
        r = clf.clasificar("Q2816022J", "CORREOS", {})
        assert r.categoria == "correos_exento"
        assert r.exento_art20 is True
        assert r.iva_codimpuesto == "IVA0"
        assert r.iva_tasa == 0

    def test_autonomo_persona_fisica_sin_categoria(self, clf):
        """Persona física española sin keywords → servicios_profesionales_autonomo."""
        r = clf.clasificar("12345678Z", "JUAN GARCIA CONSULTOR", {})
        assert r.categoria == "servicios_profesionales_autonomo"

    def test_asesoria_juridica(self, clf):
        r = clf.clasificar("B12345678", "ASESORIA JURIDICA Y FISCAL", {})
        assert r.categoria in ("servicios_asesoria_gestoria", "servicios_profesionales_autonomo")

    def test_transporte_mercancias(self, clf):
        r = clf.clasificar("B12345678", "TRANSPORTES GARCIA SL", {
            "lineas": [{"descripcion": "Flete terrestre"}]
        })
        assert r.categoria == "transporte_mercancias"

    def test_renting_pregunta_tipo_vehiculo(self, clf):
        r = clf.clasificar("B12345678", "ALD AUTOMOTIVE RENTING", {})
        assert r.categoria == "renting_leasing"
        assert "tipo_vehiculo" in r.preguntas_pendientes

    def test_peajes_autopista(self, clf):
        r = clf.clasificar("Q2817804D", "AP-7 AUTOPISTAS AUMAR", {
            "lineas": [{"descripcion": "Peaje autopista"}]
        })
        assert r.categoria == "peajes_autopista"
        assert "tipo_vehiculo" in r.preguntas_pendientes

    def test_categoria_default_cuando_no_hay_coincidencia(self, clf):
        r = clf.clasificar("B12345678", "PROVEEDOR DESCONOCIDO XYZ", {})
        assert r.categoria == "compras_mercancias_general"


# ═════════════════════════════════════════════════════════════════════════════
# BLOQUE 3: Suplidos aduaneros
# ═════════════════════════════════════════════════════════════════════════════

class TestSuplidos:
    def test_iva_aduana_en_linea(self, clf):
        r = clf.clasificar("B12345678", "DHL LOGISTICS", {
            "lineas": [
                {"descripcion": "Flete aéreo"},
                {"descripcion": "IVA ADUANA"},
            ]
        })
        assert r.categoria == "suplidos_aduaneros"
        assert r.iva_codimpuesto == "IVA0"

    def test_derechos_arancel(self, clf):
        r = clf.clasificar("B12345678", "AGENCIA ADUANERA", {
            "lineas": [{"descripcion": "Derechos Arancel importacion"}]
        })
        assert r.categoria == "suplidos_aduaneros"

    def test_despacho_aduana(self, clf):
        r = clf.clasificar("B12345678", "TRANSITARIO", {
            "lineas": [{"descripcion": "Gastos despacho aduana"}]
        })
        assert r.categoria == "suplidos_aduaneros"


# ═════════════════════════════════════════════════════════════════════════════
# BLOQUE 4: Wizard — tipo_vehiculo
# ═════════════════════════════════════════════════════════════════════════════

class TestWizardTipoVehiculo:
    def test_turismo_50pct_deducible(self, clf):
        r = clf.clasificar("B12345678", "GALP ENERGIA", {
            "lineas": [{"descripcion": "Gasoil"}]
        })
        clf.aplicar_respuestas(r, {"tipo_vehiculo": "turismo"})
        assert r.iva_deducible_pct == 50
        assert "iva_turismo_50" in r.operaciones_extra
        assert "tipo_vehiculo" not in r.preguntas_pendientes

    def test_comercial_100pct_deducible(self, clf):
        r = clf.clasificar("B12345678", "GALP ENERGIA", {
            "lineas": [{"descripcion": "Gasoil"}]
        })
        clf.aplicar_respuestas(r, {"tipo_vehiculo": "comercial"})
        assert r.iva_deducible_pct == 100
        assert "iva_turismo_50" not in r.operaciones_extra
        assert "tipo_vehiculo" not in r.preguntas_pendientes

    def test_pregunta_eliminada_tras_respuesta(self, clf):
        r = clf.clasificar("B12345678", "ALD RENTING", {})
        assert "tipo_vehiculo" in r.preguntas_pendientes
        clf.aplicar_respuestas(r, {"tipo_vehiculo": "turismo"})
        assert r.es_completa()

    def test_respuesta_no_aplica_si_no_habia_pregunta(self, clf):
        """Wizard no modifica nada si la pregunta no estaba pendiente."""
        r = clf.clasificar("A81948077", "ENDESA", {})
        ded_antes = r.iva_deducible_pct
        clf.aplicar_respuestas(r, {"tipo_vehiculo": "turismo"})
        assert r.iva_deducible_pct == ded_antes


# ═════════════════════════════════════════════════════════════════════════════
# BLOQUE 5: Wizard — inicio_actividad_autonomo
# ═════════════════════════════════════════════════════════════════════════════

class TestWizardInicioActividad:
    def test_pregunta_pendiente_autonomo(self, clf):
        r = clf.clasificar("12345678Z", "CARLOS GARCIA ASESOR", {})
        assert r.categoria == "servicios_profesionales_autonomo"
        assert "inicio_actividad_autonomo" in r.preguntas_pendientes

    def test_irpf_15_actividad_consolidada(self, clf):
        r = clf.clasificar("12345678Z", "CARLOS GARCIA ASESOR", {})
        clf.aplicar_respuestas(r, {"inicio_actividad_autonomo": "no"})
        assert r.irpf_pct == 15
        assert "inicio_actividad_autonomo" not in r.preguntas_pendientes

    def test_irpf_7_inicio_actividad(self, clf):
        r = clf.clasificar("12345678Z", "CARLOS GARCIA ASESOR", {})
        clf.aplicar_respuestas(r, {"inicio_actividad_autonomo": "si"})
        assert r.irpf_pct == 7

    def test_auto_detecta_7pct_en_texto_factura(self, clf):
        """Si el texto ya dice '7%', no preguntar inicio actividad."""
        r = clf.clasificar("12345678Z", "PEDRO MARTINEZ", {
            "lineas": [{"descripcion": "Honorarios retención 7%"}]
        })
        assert "inicio_actividad_autonomo" not in r.preguntas_pendientes

    def test_auto_detecta_inicio_actividad_texto(self, clf):
        r = clf.clasificar("12345678Z", "PEDRO MARTINEZ", {
            "lineas": [{"descripcion": "INICIO DE ACTIVIDAD honorarios"}]
        })
        assert "inicio_actividad_autonomo" not in r.preguntas_pendientes


# ═════════════════════════════════════════════════════════════════════════════
# BLOQUE 6: Wizard — pct_afectacion
# ═════════════════════════════════════════════════════════════════════════════

class TestWizardPctAfectacion:
    def test_pct_afectacion_string_con_porcentaje(self, clf):
        """pct_afectacion '40%' → iva_deducible_pct = 40."""
        r = clf.clasificar("B12345678", "INMOBILIARIA", {
            "lineas": [{"descripcion": "alquiler local mixto vivienda despacho"}]
        })
        # Añadir pregunta artificialmente para probar la lógica
        r.preguntas_pendientes.append("pct_afectacion")
        clf.aplicar_respuestas(r, {"pct_afectacion": "40%"})
        assert r.iva_deducible_pct == 40
        assert "pct_afectacion" not in r.preguntas_pendientes

    def test_pct_afectacion_numero(self, clf):
        r = clf.clasificar("B12345678", "ARRENDADOR", {})
        r.preguntas_pendientes.append("pct_afectacion")
        clf.aplicar_respuestas(r, {"pct_afectacion": 75})
        assert r.iva_deducible_pct == 75

    def test_pct_afectacion_invalido_no_modifica(self, clf):
        r = clf.clasificar("B12345678", "ARRENDADOR", {})
        r.preguntas_pendientes.append("pct_afectacion")
        old_pct = r.iva_deducible_pct
        clf.aplicar_respuestas(r, {"pct_afectacion": "no_sabe"})
        assert r.iva_deducible_pct == old_pct


# ═════════════════════════════════════════════════════════════════════════════
# BLOQUE 7: Divisa extranjera
# ═════════════════════════════════════════════════════════════════════════════

class TestDivisaExtranjera:
    def test_usd_fuerza_extracomunitario(self, clf):
        r = clf.clasificar("B12345678", "PROVEEDOR", {"divisa": "USD"})
        assert r.regimen == "extracomunitario"

    def test_eur_mantiene_regimen(self, clf):
        r = clf.clasificar("B12345678", "TELEFONICA", {"divisa": "EUR"})
        assert r.regimen == "general"

    def test_divisa_vacia_mantiene_regimen(self, clf):
        r = clf.clasificar("B12345678", "PROVEEDOR", {"divisa": ""})
        assert r.regimen == "general"


# ═════════════════════════════════════════════════════════════════════════════
# BLOQUE 8: Confianza y trazabilidad
# ═════════════════════════════════════════════════════════════════════════════

class TestConfianzaTrazabilidad:
    def test_confianza_alta_telefono(self, clf):
        r = clf.clasificar("A80153195", "MOVISTAR TELECOMUNICACIONES", {})
        assert r.confianza >= 0.7

    def test_confianza_baja_sin_cif(self, clf):
        r = clf.clasificar("", "PROVEEDOR RARO", {})
        assert r.confianza < 0.5

    def test_razonamiento_incluye_cif(self, clf):
        r = clf.clasificar("B12345678", "PROVEEDOR", {})
        assert "B12345678" in r.razonamiento

    def test_razonamiento_sin_cif(self, clf):
        r = clf.clasificar("", "PROVEEDOR", {})
        assert "Sin CIF" in r.razonamiento

    def test_base_legal_poblada(self, clf):
        r = clf.clasificar("Q2816022J", "CORREOS", {})
        assert r.base_legal  # no vacío

    def test_es_completa_true_sin_preguntas(self, clf):
        r = clf.clasificar("A81948077", "ENDESA", {})
        assert r.es_completa()

    def test_es_completa_false_con_preguntas(self, clf):
        r = clf.clasificar("B12345678", "GALP", {
            "lineas": [{"descripcion": "Gasoil"}]
        })
        assert not r.es_completa()

    def test_resumen_format(self, clf):
        r = clf.clasificar("A81948077", "ENDESA", {})
        resumen = r.resumen()
        assert "|" in resumen
        assert r.categoria in resumen


# ═════════════════════════════════════════════════════════════════════════════
# BLOQUE 9: a_entrada_config
# ═════════════════════════════════════════════════════════════════════════════

class TestAEntradaConfig:
    def test_entrada_basica_telefono(self, clf):
        r = clf.clasificar("A80153195", "TELEFONICA SA", {})
        entrada = clf.a_entrada_config("telefonica", "TELEFÓNICA SA", "A80153195", r)
        assert entrada["cif"] == "A80153195"
        assert entrada["nombre_fs"] == "TELEFÓNICA SA"
        assert entrada["codimpuesto"] == "IVA21"

    def test_entrada_incluye_retencion_autonomo(self, clf):
        r = clf.clasificar("12345678Z", "PEDRO GARCIA CONSULTOR", {})
        clf.aplicar_respuestas(r, {"inicio_actividad_autonomo": "no"})
        entrada = clf.a_entrada_config("pgarcia", "PEDRO GARCIA CONSULTOR", "12345678Z", r)
        assert entrada.get("retencion_irpf") == 15

    def test_entrada_incluye_iva_deducible_pct_50(self, clf):
        r = clf.clasificar("B12345678", "GALP", {
            "lineas": [{"descripcion": "Gasoil"}]
        })
        clf.aplicar_respuestas(r, {"tipo_vehiculo": "turismo"})
        entrada = clf.a_entrada_config("galp", "GALP ENERGÍA", "B12345678", r)
        assert entrada["iva_deducible_pct"] == 50
        assert any(re["tipo"] == "iva_turismo_50"
                   for re in entrada.get("reglas_especiales", []))

    def test_entrada_100pct_no_incluye_campo(self, clf):
        """Si deducible=100%, no se incluye el campo (valor por defecto)."""
        r = clf.clasificar("A81948077", "ENDESA", {})
        entrada = clf.a_entrada_config("endesa", "ENDESA", "A81948077", r)
        assert "iva_deducible_pct" not in entrada

    def test_entrada_correos_exento(self, clf):
        r = clf.clasificar("Q2816022J", "CORREOS", {})
        entrada = clf.a_entrada_config("correos", "CORREOS SA", "Q2816022J", r)
        assert entrada["codimpuesto"] == "IVA0"

    def test_entrada_notas_incluye_confianza(self, clf):
        r = clf.clasificar("A80153195", "TELEFONICA", {})
        entrada = clf.a_entrada_config("tel", "TELEFONICA", "A80153195", r)
        assert "%" in entrada["notas"]
        assert "MCF" in entrada["notas"]

    def test_entrada_cif_vacio_usa_esp(self, clf):
        r = clf.clasificar("", "PROVEEDOR", {})
        entrada = clf.a_entrada_config("prov", "PROVEEDOR", "", r)
        assert entrada["pais"] == "ESP"
        assert entrada["cif"] == ""
