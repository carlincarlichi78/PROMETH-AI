"""Generador de variaciones CSS por proveedor.

Asigna custom properties CSS deterministas a cada proveedor
(mismo nombre + seed = mismas variaciones siempre).
"""

import random
from typing import Optional


# Paletas de color primario (hex) — inspiradas en marcas reales
PALETAS = [
    {"primario": "#003366", "secundario": "#e6f0ff", "nombre": "azul_corp"},
    {"primario": "#cc0000", "secundario": "#fff0f0", "nombre": "rojo"},
    {"primario": "#2e7d32", "secundario": "#e8f5e9", "nombre": "verde"},
    {"primario": "#424242", "secundario": "#f5f5f5", "nombre": "gris"},
    {"primario": "#1a1a1a", "secundario": "#fafafa", "nombre": "negro"},
    {"primario": "#800020", "secundario": "#fdf0f4", "nombre": "burdeos"},
    {"primario": "#e65100", "secundario": "#fff3e0", "nombre": "naranja"},
]

# Fuentes disponibles en WeasyPrint
FUENTES = [
    "Arial, sans-serif",
    "Helvetica, Arial, sans-serif",
    "Times New Roman, serif",
    "Georgia, serif",
    "Verdana, sans-serif",
    "Trebuchet MS, sans-serif",
    "Courier New, monospace",
    "Calibri, sans-serif",
    "Tahoma, sans-serif",
    "Palatino, serif",
]

# Tamanos base (pt)
TAMANOS_BASE = [8, 9, 10, 11, 12]

# Tamanos titulo (pt)
TAMANOS_TITULO = [14, 16, 18, 20, 24]

# Posiciones de logo
POSICIONES_LOGO = ["left", "center", "right"]

# Tamanos de logo (px)
TAMANOS_LOGO = [40, 60, 80, 100, 120]

# Estilos de tabla
ESTILOS_TABLA = [
    {"id": "borders", "border": "1px solid #ccc", "header_bg": None},
    {"id": "zebra", "border": "none", "header_bg": None, "zebra": True},
    {"id": "minimal", "border": "none", "header_bg": "transparent", "border_bottom": "1px solid #eee"},
    {"id": "none", "border": "none", "header_bg": "transparent"},
    {"id": "dotted", "border": "1px dotted #999", "header_bg": None},
]

# Spacings
SPACINGS = {
    "compact": {"padding": "4px 6px", "margin_section": "8px", "line_height": "1.2"},
    "normal": {"padding": "6px 10px", "margin_section": "15px", "line_height": "1.4"},
    "airy": {"padding": "10px 15px", "margin_section": "25px", "line_height": "1.6"},
}

# Radios de borde
RADIOS_BORDE = [0, 2, 4, 6, 8]

# Separadores entre secciones
SEPARADORES = ["hr", "border-bottom", "none", "doble-linea"]


def generar_variaciones_css(nombre_proveedor: str, familia: str, seed: int) -> dict:
    """Genera variaciones CSS deterministas para un proveedor.

    Args:
        nombre_proveedor: nombre de la empresa (determina el hash)
        familia: familia de plantilla (para ajustes especificos)
        seed: seed global del generador

    Returns:
        Dict con custom properties CSS y sus valores
    """
    rng = random.Random(hash(nombre_proveedor) + seed + 1013)

    paleta = rng.choice(PALETAS)
    fuente = rng.choice(FUENTES)
    tamano_base = rng.choice(TAMANOS_BASE)
    tamano_titulo = rng.choice(TAMANOS_TITULO)
    logo_pos = rng.choice(POSICIONES_LOGO)
    logo_tamano = rng.choice(TAMANOS_LOGO)
    estilo_tabla = rng.choice(ESTILOS_TABLA)
    spacing_key = rng.choice(list(SPACINGS.keys()))
    spacing = SPACINGS[spacing_key]
    radio = rng.choice(RADIOS_BORDE)
    separador = rng.choice(SEPARADORES)

    # Ajustes por familia
    if familia == "ticket_tpv":
        fuente = "Courier New, monospace"
        tamano_base = 9
        spacing_key = "compact"
        spacing = SPACINGS["compact"]
    elif familia == "autonomo_basico":
        estilo_tabla = {"id": "none", "border": "none", "header_bg": "transparent"}
    elif familia in ("corp_grande", "corp_limpia", "corp_industrial"):
        if tamano_base < 9:
            tamano_base = 9

    # Color header tabla: derivado del primario o neutro
    if estilo_tabla.get("header_bg") is None:
        header_bg = paleta["primario"] if rng.random() < 0.6 else "#333333"
    else:
        header_bg = estilo_tabla["header_bg"]

    return {
        "color_primario": paleta["primario"],
        "color_secundario": paleta["secundario"],
        "nombre_paleta": paleta["nombre"],
        "fuente_principal": fuente,
        "fuente_tamano_base": f"{tamano_base}pt",
        "fuente_tamano_titulo": f"{tamano_titulo}pt",
        "logo_posicion": logo_pos,
        "logo_tamano": f"{logo_tamano}px",
        "tabla_estilo": estilo_tabla["id"],
        "tabla_header_bg": header_bg,
        "tabla_header_color": "#ffffff" if header_bg not in ("transparent", "#f5f5f5") else "#333333",
        "tabla_border": estilo_tabla.get("border", "none"),
        "tabla_zebra": estilo_tabla.get("zebra", False),
        "bordes_radio": f"{radio}px",
        "spacing": spacing_key,
        "spacing_padding": spacing["padding"],
        "spacing_margin_section": spacing["margin_section"],
        "spacing_line_height": spacing["line_height"],
        "separador": separador,
        "alineacion_importes": "right",
    }


def css_custom_properties_str(variaciones: dict) -> str:
    """Convierte un dict de variaciones a un bloque CSS :root con custom properties.

    Args:
        variaciones: dict generado por generar_variaciones_css()

    Returns:
        String CSS listo para inyectar en <style>
    """
    # Mapeo de claves Python a custom properties CSS
    mapeo = {
        "color_primario": "--color-primario",
        "color_secundario": "--color-secundario",
        "fuente_principal": "--fuente-principal",
        "fuente_tamano_base": "--fuente-tamano-base",
        "fuente_tamano_titulo": "--fuente-tamano-titulo",
        "logo_posicion": "--logo-posicion",
        "logo_tamano": "--logo-tamano",
        "tabla_estilo": "--tabla-estilo",
        "tabla_header_bg": "--tabla-header-bg",
        "tabla_header_color": "--tabla-header-color",
        "tabla_border": "--tabla-border",
        "bordes_radio": "--bordes-radio",
        "spacing_padding": "--spacing-padding",
        "spacing_margin_section": "--spacing-margin-section",
        "spacing_line_height": "--spacing-line-height",
        "separador": "--separador",
        "alineacion_importes": "--alineacion-importes",
    }

    lineas = [":root {"]
    for clave_py, clave_css in mapeo.items():
        valor = variaciones.get(clave_py, "")
        lineas.append(f"  {clave_css}: {valor};")
    lineas.append("}")

    return "\n".join(lineas)
