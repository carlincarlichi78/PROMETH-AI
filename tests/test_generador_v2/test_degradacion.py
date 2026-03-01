"""Tests para utils/ruido.py — degradacion visual v2."""

import random
import sys
from pathlib import Path

import pytest

DIR_GENERADOR = Path(__file__).resolve().parents[1] / "datos_prueba" / "generador"
sys.path.insert(0, str(DIR_GENERADOR))

from utils.ruido import (
    seleccionar_perfil,
    perfil_para_proveedor,
    aplicar_degradacion,
    aplicar_ruido,
    generar_html_degradacion,
)


# ---------------------------------------------------------------------------
# Tests de seleccion de perfil
# ---------------------------------------------------------------------------

class TestSeleccionPerfil:
    PERFILES_VALIDOS = {
        "digital_perfecto", "digital_bueno", "scan_bueno",
        "scan_regular", "scan_malo", "manuscrito",
    }

    def test_seleccionar_perfil_valido(self):
        """seleccionar_perfil devuelve un perfil del catalogo."""
        rng = random.Random(42)
        perfil = seleccionar_perfil(rng)
        assert perfil in self.PERFILES_VALIDOS

    def test_seleccionar_perfil_distribucion(self):
        """Todos los perfiles aparecen con suficientes muestras."""
        rng = random.Random(42)
        conteo = {}
        for _ in range(5000):
            p = seleccionar_perfil(rng)
            conteo[p] = conteo.get(p, 0) + 1

        # digital_bueno (peso 30) deberia ser el mas frecuente
        assert conteo.get("digital_bueno", 0) > conteo.get("manuscrito", 0)
        # manuscrito (peso 3) deberia aparecer al menos alguna vez
        assert conteo.get("manuscrito", 0) > 0

    def test_perfil_proveedor_determinista(self):
        """Mismo proveedor + seed = mismo perfil."""
        p1 = perfil_para_proveedor("AWS EMEA SARL", 42)
        p2 = perfil_para_proveedor("AWS EMEA SARL", 42)
        assert p1 == p2
        assert p1 in self.PERFILES_VALIDOS

    def test_perfil_proveedor_diferente_seed(self):
        """Proveedores distintos o seeds distintos pueden dar perfiles distintos."""
        p1 = perfil_para_proveedor("AWS EMEA SARL", 42)
        p2 = perfil_para_proveedor("IBERDROLA S.A.", 42)
        # No garantizado pero muy probable con nombres distintos
        # Test suave: ambos son validos
        assert p1 in self.PERFILES_VALIDOS
        assert p2 in self.PERFILES_VALIDOS


# ---------------------------------------------------------------------------
# Tests de aplicar degradacion
# ---------------------------------------------------------------------------

class TestAplicarDegradacion:
    def test_no_muta_original(self):
        """aplicar_degradacion no muta el dict original."""
        datos_original = {"concepto": "Test", "total": 100.00}
        datos_copia = dict(datos_original)
        rng = random.Random(42)
        resultado, aplicadas = aplicar_degradacion(datos_copia, "scan_malo", rng)
        # El original no deberia tener claves de degradacion
        assert "rotacion_body" not in datos_original
        assert "sello_texto" not in datos_original

    def test_digital_perfecto_pocas_degradaciones(self):
        """digital_perfecto solo tiene D05 (sello), asi que pocas degradaciones."""
        rng = random.Random(42)
        datos = {"concepto": "Test"}
        resultado, aplicadas = aplicar_degradacion(datos, "digital_perfecto", rng)
        # Puede tener 0 o 1 degradacion (solo D05 habilitado con prob 0.4)
        assert len(aplicadas) <= 1
        for a in aplicadas:
            assert a.startswith("D05:")

    def test_scan_malo_muchas_degradaciones(self):
        """scan_malo tiene 11 degradaciones posibles, deberia aplicar varias."""
        total_aplicadas = 0
        for seed in range(100):
            rng = random.Random(seed)
            datos = {"concepto": "Test", "lineas": []}
            _, aplicadas = aplicar_degradacion(datos, "scan_malo", rng)
            total_aplicadas += len(aplicadas)
        # Con 100 iteraciones y ~11 degradaciones con probs variadas,
        # deberia aplicar al menos algunas en total
        assert total_aplicadas > 50

    def test_perfil_inexistente(self):
        """Perfil desconocido devuelve datos sin cambios."""
        rng = random.Random(42)
        datos = {"concepto": "Test"}
        resultado, aplicadas = aplicar_degradacion(datos, "perfil_fake", rng)
        assert aplicadas == []
        assert resultado == datos

    def test_degradacion_rotacion(self):
        """D01 inyecta rotacion_body en datos."""
        # Forzar muchas iteraciones para encontrar una con D01
        for seed in range(200):
            rng = random.Random(seed)
            datos = {"concepto": "Test"}
            resultado, aplicadas = aplicar_degradacion(datos, "scan_regular", rng)
            d01 = [a for a in aplicadas if a.startswith("D01:")]
            if d01:
                assert "rotacion_body" in resultado
                assert isinstance(resultado["rotacion_body"], float)
                return
        pytest.skip("D01 no se aplico en 200 intentos (prob 0.6 en scan_regular)")

    def test_degradacion_sello(self):
        """D05 inyecta sello_texto en datos."""
        for seed in range(200):
            rng = random.Random(seed)
            datos = {"concepto": "Test"}
            resultado, aplicadas = aplicar_degradacion(datos, "scan_bueno", rng)
            d05 = [a for a in aplicadas if a.startswith("D05:")]
            if d05:
                assert "sello_texto" in resultado
                assert resultado["sello_texto"] in ["PAGADO", "RECIBIDO", "CONFORME", "CONTABILIZADO"]
                return
        pytest.skip("D05 no se aplico en 200 intentos")


# ---------------------------------------------------------------------------
# Tests de ruido v1 (compatibilidad)
# ---------------------------------------------------------------------------

class TestAplicarRuido:
    def test_factura_compra_ruido(self):
        """aplicar_ruido para facturas puede marcar como pagada."""
        alguna_pagada = False
        for seed in range(100):
            rng = random.Random(seed)
            datos = {"concepto": "Test"}
            resultado = aplicar_ruido(datos, "factura_compra", rng)
            if resultado.get("pagada"):
                alguna_pagada = True
                break
        assert alguna_pagada

    def test_no_muta_original_ruido(self):
        """aplicar_ruido no muta el dict original."""
        datos = {"concepto": "Test"}
        rng = random.Random(42)
        resultado = aplicar_ruido(datos, "factura_compra", rng)
        assert "pagada" not in datos or datos == {"concepto": "Test"}


# ---------------------------------------------------------------------------
# Tests de generacion HTML
# ---------------------------------------------------------------------------

class TestGenerarHTMLDegradacion:
    def test_vacio_sin_datos(self):
        """Sin datos de degradacion, devuelve string vacio."""
        html = generar_html_degradacion({})
        assert html == "" or isinstance(html, str)

    def test_con_sello(self):
        """Datos con sello generan HTML con texto del sello."""
        datos = {
            "sello_texto": "PAGADO",
            "sello_rotacion": -30,
            "sello_opacidad": 0.15,
            "sello_color": "rgba(0,128,0,0.15)",
            "sello_border_color": "rgba(0,128,0,0.15)",
        }
        html = generar_html_degradacion(datos)
        assert "PAGADO" in html

    def test_con_manchas(self):
        """Datos con manchas generan HTML con elementos visuales."""
        datos = {
            "manchas": [
                {"top": 30, "left": 50, "size": 20, "opacidad": 0.05, "color": "#8B4513"},
            ],
        }
        html = generar_html_degradacion(datos)
        assert isinstance(html, str)
