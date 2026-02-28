"""Tests para utils/variaciones.py — variaciones CSS por proveedor."""

import sys
from pathlib import Path

import pytest

DIR_GENERADOR = Path(__file__).resolve().parents[1] / "datos_prueba" / "generador"
sys.path.insert(0, str(DIR_GENERADOR))

from utils.variaciones import (
    generar_variaciones_css,
    css_custom_properties_str,
    PALETAS,
    FUENTES,
    TAMANOS_BASE,
    TAMANOS_TITULO,
    ESTILOS_TABLA,
    SPACINGS,
)


class TestGenerarVariaciones:
    def test_determinista(self):
        """Mismo proveedor + familia + seed = mismas variaciones."""
        v1 = generar_variaciones_css("AWS EMEA SARL", "pyme_clasica", 42)
        v2 = generar_variaciones_css("AWS EMEA SARL", "pyme_clasica", 42)
        assert v1 == v2

    def test_diferentes_proveedores(self):
        """Proveedores distintos generan variaciones distintas."""
        v1 = generar_variaciones_css("AWS EMEA SARL", "pyme_clasica", 42)
        v2 = generar_variaciones_css("IBERDROLA S.A.", "pyme_clasica", 42)
        assert v1 != v2

    def test_campos_obligatorios(self):
        """El dict contiene todos los campos esperados."""
        v = generar_variaciones_css("TEST S.L.", "corp_grande", 42)
        campos = [
            "color_primario", "color_secundario", "nombre_paleta",
            "fuente_principal", "fuente_tamano_base", "fuente_tamano_titulo",
            "logo_posicion", "logo_tamano", "tabla_estilo",
            "tabla_header_bg", "tabla_header_color", "tabla_border",
            "bordes_radio", "spacing", "spacing_padding",
            "spacing_margin_section", "spacing_line_height",
            "separador", "alineacion_importes",
        ]
        for campo in campos:
            assert campo in v, f"Campo '{campo}' falta en variaciones"

    def test_color_primario_hex(self):
        """Color primario es un hex valido."""
        v = generar_variaciones_css("TEST S.L.", "corp_grande", 42)
        color = v["color_primario"]
        assert color.startswith("#")
        assert len(color) == 7

    def test_fuente_tamano_con_pt(self):
        """Tamanos de fuente incluyen la unidad pt."""
        v = generar_variaciones_css("TEST S.L.", "corp_grande", 42)
        assert v["fuente_tamano_base"].endswith("pt")
        assert v["fuente_tamano_titulo"].endswith("pt")

    def test_ajuste_ticket_tpv(self):
        """Familia ticket_tpv fuerza Courier New y compacto."""
        v = generar_variaciones_css("BAR ESQUINA", "ticket_tpv", 42)
        assert "Courier New" in v["fuente_principal"]
        assert v["fuente_tamano_base"] == "9pt"
        assert v["spacing"] == "compact"

    def test_ajuste_corp_grande_tamano_minimo(self):
        """Familias corp_* fuerzan tamano base >= 9pt."""
        v = generar_variaciones_css("GRAN CORP S.A.", "corp_grande", 42)
        tamano = int(v["fuente_tamano_base"].replace("pt", ""))
        assert tamano >= 9


class TestCSSCustomProperties:
    def test_genera_bloque_root(self):
        """Genera un bloque :root con custom properties CSS."""
        variaciones = generar_variaciones_css("TEST S.L.", "pyme_clasica", 42)
        css = css_custom_properties_str(variaciones)
        assert css.startswith(":root {")
        assert css.endswith("}")
        assert "--color-primario:" in css
        assert "--fuente-principal:" in css
        assert "--tabla-header-bg:" in css

    def test_todas_las_propiedades_presentes(self):
        """El bloque CSS contiene todas las custom properties mapeadas."""
        variaciones = generar_variaciones_css("TEST S.L.", "pyme_clasica", 42)
        css = css_custom_properties_str(variaciones)
        propiedades_esperadas = [
            "--color-primario", "--color-secundario", "--fuente-principal",
            "--fuente-tamano-base", "--fuente-tamano-titulo", "--logo-posicion",
            "--tabla-estilo", "--tabla-header-bg", "--bordes-radio",
            "--spacing-padding", "--separador", "--alineacion-importes",
        ]
        for prop in propiedades_esperadas:
            assert prop in css, f"Propiedad CSS '{prop}' no encontrada"

    def test_dict_vacio(self):
        """Dict vacio produce un :root con valores vacios."""
        css = css_custom_properties_str({})
        assert ":root {" in css
        assert "}" in css
