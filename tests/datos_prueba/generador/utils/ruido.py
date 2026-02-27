"""Sistema de degradacion visual v2 para documentos generados.

13 capas de degradacion (D01-D13) y 6 perfiles de calidad.
Cada proveedor tiene un perfil fijo (determinista por seed).
Las degradaciones se aplican sobre el HTML pre-render.
"""

import random
from pathlib import Path
from typing import Optional

import yaml


DIR_DATOS = Path(__file__).resolve().parents[1] / "datos"

_formatos_cache: Optional[dict] = None


def _cargar_formatos() -> dict:
    """Carga formatos.yaml (contiene perfiles y degradaciones). Cachea."""
    global _formatos_cache
    if _formatos_cache is not None:
        return _formatos_cache
    ruta = DIR_DATOS / "formatos.yaml"
    with open(ruta, encoding="utf-8") as f:
        _formatos_cache = yaml.safe_load(f)
    return _formatos_cache


# ---------------------------------------------------------------------------
# Seleccion de perfil
# ---------------------------------------------------------------------------

def seleccionar_perfil(rng: random.Random) -> str:
    """Elige un perfil de calidad segun pesos del YAML."""
    formatos = _cargar_formatos()
    perfiles = formatos["perfiles_calidad"]
    nombres = list(perfiles.keys())
    pesos = [perfiles[n]["peso"] for n in nombres]
    return rng.choices(nombres, weights=pesos, k=1)[0]


def perfil_para_proveedor(nombre_proveedor: str, seed: int) -> str:
    """Asigna un perfil de calidad fijo a un proveedor (determinista)."""
    rng = random.Random(hash(nombre_proveedor) + seed + 3571)
    return seleccionar_perfil(rng)


# ---------------------------------------------------------------------------
# Capas de degradacion individuales (D01-D13)
# ---------------------------------------------------------------------------

def _d01_rotacion(datos: dict, rng: random.Random) -> list[str]:
    """D01: Rotacion scan — simula escaner desalineado."""
    angulo = rng.uniform(0.3, 3.0) * rng.choice([-1, 1])
    datos["rotacion_body"] = angulo
    return [f"D01:rotacion {angulo:.1f}°"]


def _d02_margen_descentrado(datos: dict, rng: random.Random) -> list[str]:
    """D02: Margen descentrado — simula escaneo desplazado."""
    extra_top = rng.randint(5, 25)
    extra_left = rng.randint(3, 15)
    datos["margen_extra_top"] = extra_top
    datos["margen_extra_left"] = extra_left
    return [f"D02:margen +{extra_top}mm top, +{extra_left}mm left"]


def _d03_fondo_sucio(datos: dict, rng: random.Random) -> list[str]:
    """D03: Fondo sucio — simula papel envejecido."""
    # Generar color entre #f5f0e0 y #e8e0d0
    r = rng.randint(0xe8, 0xf5)
    g = rng.randint(0xe0, 0xf0)
    b = rng.randint(0xd0, 0xe0)
    color = f"#{r:02x}{g:02x}{b:02x}"
    datos["fondo_sucio"] = color
    return [f"D03:fondo {color}"]


def _d04_manchas(datos: dict, rng: random.Random) -> list[str]:
    """D04: Manchas — circulos semitransparentes."""
    cantidad = rng.randint(1, 3)
    manchas = []
    for _ in range(cantidad):
        manchas.append({
            "top": rng.randint(5, 90),  # % de la pagina
            "left": rng.randint(5, 90),
            "size": rng.randint(15, 50),  # px
            "opacidad": rng.uniform(0.03, 0.10),
            "color": rng.choice(["#8B4513", "#696969", "#556B2F"]),
        })
    datos["manchas"] = manchas
    return [f"D04:{cantidad} manchas"]


def _d05_sello(datos: dict, rng: random.Random) -> list[str]:
    """D05: Sello PAGADO/RECIBIDO/CONFORME/CONTABILIZADO."""
    textos = ["PAGADO", "RECIBIDO", "CONFORME", "CONTABILIZADO"]
    texto = rng.choice(textos)
    rotacion = rng.uniform(-40, -15)
    opacidad = rng.uniform(0.08, 0.20)
    color = rng.choice(["rgba(0,128,0,", "rgba(0,0,180,", "rgba(180,0,0,"])
    datos["sello_texto"] = texto
    datos["sello_rotacion"] = rotacion
    datos["sello_opacidad"] = opacidad
    datos["sello_color"] = f"{color}{opacidad})"
    datos["sello_border_color"] = f"{color}{opacidad})"
    return [f"D05:sello {texto}"]


def _d06_anotaciones(datos: dict, rng: random.Random) -> list[str]:
    """D06: Anotaciones manuscritas — texto tipo handwriting."""
    textos = ["OK", "Contabilizado", "23/01", "Pdte cobro", "Archivo",
              "Revisado", "Conforme", "Ver 2T", "Cta 600"]
    texto = rng.choice(textos)
    datos["anotacion_manuscrita"] = {
        "texto": texto,
        "top": rng.randint(10, 80),
        "left": rng.randint(60, 90),
        "rotacion": rng.uniform(-15, 15),
        "tamano": rng.randint(12, 20),
        "color": rng.choice(["#0000cc", "#cc0000", "#006600"]),
    }
    return [f"D06:anotacion '{texto}'"]


def _d07_baja_resolucion(datos: dict, rng: random.Random) -> list[str]:
    """D07: Baja resolucion — reduce DPI del renderizado."""
    dpi = rng.randint(72, 96)
    datos["dpi_override"] = dpi
    return [f"D07:baja res {dpi}dpi"]


def _d08_doble_scan(datos: dict, rng: random.Random) -> list[str]:
    """D08: Doble scan — borde sombra y perspectiva leve."""
    datos["doble_scan"] = {
        "sombra_offset": rng.randint(2, 6),
        "perspectiva": rng.uniform(0.5, 2.0),
        "fondo_gris": f"#{rng.randint(0xd0, 0xe0):02x}" * 3,
    }
    return ["D08:doble scan"]


def _d09_texto_cortado(datos: dict, rng: random.Random) -> list[str]:
    """D09: Texto cortado — reduce el container por algun lado."""
    lado = rng.choice(["right", "bottom", "left"])
    recorte_mm = rng.randint(5, 15)
    datos["texto_cortado"] = {"lado": lado, "recorte_mm": recorte_mm}
    return [f"D09:cortado {recorte_mm}mm {lado}"]


def _d10_pliegue_grapa(datos: dict, rng: random.Random) -> list[str]:
    """D10: Pliegue o grapa — linea diagonal o circulo oscuro."""
    tipo = rng.choice(["pliegue", "grapa"])
    if tipo == "pliegue":
        datos["pliegue"] = {
            "angulo": rng.uniform(-5, 5),
            "posicion_y": rng.randint(20, 80),  # % vertical
            "opacidad": rng.uniform(0.05, 0.12),
        }
    else:
        esquina = rng.choice(["top-left", "top-right"])
        datos["grapa"] = {
            "esquina": esquina,
            "tamano": rng.randint(8, 15),
        }
    return [f"D10:{tipo}"]


def _d11_subrayado(datos: dict, rng: random.Random) -> list[str]:
    """D11: Subrayado con marcador — rectangulo semitransparente."""
    color = rng.choice(["rgba(255,255,0,0.25)", "rgba(255,105,180,0.20)"])
    nombre_color = "amarillo" if "255,255,0" in color else "rosa"
    datos["subrayado_marcador"] = {
        "color": color,
        "top": rng.randint(60, 85),  # % — zona de totales
        "width": rng.randint(30, 60),
        "height": rng.randint(15, 30),
    }
    return [f"D11:marcador {nombre_color}"]


def _d12_contraste_bajo(datos: dict, rng: random.Random) -> list[str]:
    """D12: Contraste bajo — texto gris claro (poco toner)."""
    gris = rng.randint(0x88, 0x99)
    color = f"#{gris:02x}{gris:02x}{gris:02x}"
    datos["contraste_bajo"] = color
    return [f"D12:contraste bajo {color}"]


def _d13_ruido_fotocopia(datos: dict, rng: random.Random) -> list[str]:
    """D13: Ruido de fotocopia — puntos negros aleatorios."""
    cantidad = rng.randint(20, 80)
    puntos = []
    for _ in range(cantidad):
        puntos.append({
            "top": rng.uniform(0, 100),
            "left": rng.uniform(0, 100),
            "size": rng.choice([1, 1, 1, 2]),
        })
    datos["ruido_fotocopia"] = puntos
    return [f"D13:{cantidad} puntos ruido"]


# Mapa de funciones por ID de degradacion
_DEGRADACIONES = {
    "D01": _d01_rotacion,
    "D02": _d02_margen_descentrado,
    "D03": _d03_fondo_sucio,
    "D04": _d04_manchas,
    "D05": _d05_sello,
    "D06": _d06_anotaciones,
    "D07": _d07_baja_resolucion,
    "D08": _d08_doble_scan,
    "D09": _d09_texto_cortado,
    "D10": _d10_pliegue_grapa,
    "D11": _d11_subrayado,
    "D12": _d12_contraste_bajo,
    "D13": _d13_ruido_fotocopia,
}


# ---------------------------------------------------------------------------
# Funcion principal
# ---------------------------------------------------------------------------

def aplicar_degradacion(
    datos_plantilla: dict,
    perfil: str,
    rng: random.Random,
) -> tuple[dict, list[str]]:
    """Aplica degradaciones segun el perfil de calidad.

    No muta el dict original. Devuelve copia con datos de degradacion
    inyectados + lista de degradaciones aplicadas.

    Args:
        datos_plantilla: dict con variables para Jinja2
        perfil: nombre del perfil de calidad (ej: "scan_regular")
        rng: generador aleatorio con seed

    Returns:
        Tuple (datos_modificados, lista_degradaciones_aplicadas)
    """
    datos = dict(datos_plantilla)
    formatos = _cargar_formatos()

    perfil_config = formatos["perfiles_calidad"].get(perfil)
    if perfil_config is None:
        return datos, []

    degradaciones_habilitadas = perfil_config.get("degradaciones", [])
    degradaciones_config = formatos.get("degradaciones", {})
    aplicadas = []

    for deg_id in degradaciones_habilitadas:
        cfg = degradaciones_config.get(deg_id, {})
        prob = cfg.get("prob", 0.5)

        if rng.random() < prob:
            func = _DEGRADACIONES.get(deg_id)
            if func:
                resultado = func(datos, rng)
                aplicadas.extend(resultado)

    return datos, aplicadas


def aplicar_ruido(datos_plantilla: dict, tipo_doc: str, rng: random.Random) -> dict:
    """Compatibilidad con v1 — aplica ruido basico.

    Mantiene la interfaz original para que el motor.py v1 siga funcionando.
    En v2, usar aplicar_degradacion() directamente.
    """
    datos = dict(datos_plantilla)

    if tipo_doc in ("factura_compra", "factura_venta", "recibo_suministro"):
        if rng.random() < 0.4:
            datos["pagada"] = True
            datos["sello_rotacion"] = rng.uniform(-35, -25)
            datos["sello_opacidad"] = rng.uniform(0.10, 0.20)

    if tipo_doc in ("recibo_bancario", "impuesto_tasa"):
        if rng.random() < 0.3:
            datos["sello_recibido"] = True
            datos["sello_rotacion"] = rng.uniform(-40, -20)
            datos["sello_opacidad"] = rng.uniform(0.08, 0.15)

    if rng.random() < 0.15:
        datos["rotacion_body"] = rng.uniform(-0.8, 0.8)

    if rng.random() < 0.10:
        datos["margen_extra_top"] = rng.randint(5, 20)

    return datos


def generar_html_degradacion(datos: dict) -> str:
    """Genera fragmentos HTML para los efectos de degradacion.

    Llamar DESPUES de aplicar_degradacion(). Lee los campos inyectados
    en el dict y genera el CSS/HTML correspondiente.

    Returns:
        String con <style> + divs de degradacion para inyectar en el HTML
    """
    fragmentos_css = []
    fragmentos_html = []

    # D01: Rotacion
    if "rotacion_body" in datos:
        angulo = datos["rotacion_body"]
        fragmentos_css.append(
            f"body {{ transform: rotate({angulo}deg); transform-origin: center center; }}"
        )

    # D02: Margen descentrado
    if "margen_extra_top" in datos:
        top = datos.get("margen_extra_top", 0)
        left = datos.get("margen_extra_left", 0)
        fragmentos_css.append(f"body {{ padding-top: {top}mm; padding-left: {left}mm; }}")

    # D03: Fondo sucio
    if "fondo_sucio" in datos:
        fragmentos_css.append(f"body {{ background-color: {datos['fondo_sucio']}; }}")

    # D04: Manchas
    for i, mancha in enumerate(datos.get("manchas", [])):
        fragmentos_css.append(
            f".mancha-{i} {{ position: absolute; top: {mancha['top']}%; "
            f"left: {mancha['left']}%; width: {mancha['size']}px; "
            f"height: {mancha['size']}px; border-radius: 50%; "
            f"background: {mancha['color']}; opacity: {mancha['opacidad']}; "
            f"pointer-events: none; z-index: 999; }}"
        )
        fragmentos_html.append(f'<div class="mancha-{i}"></div>')

    # D05: Sello
    if "sello_texto" in datos:
        rot = datos.get("sello_rotacion", -30)
        color = datos.get("sello_color", "rgba(0,128,0,0.15)")
        border_color = datos.get("sello_border_color", color)
        fragmentos_css.append(
            f".sello-degradacion {{ position: absolute; top: 35%; left: 25%; "
            f"transform: rotate({rot}deg); font-size: 48pt; font-weight: bold; "
            f"color: {color}; border: 4px solid {border_color}; "
            f"padding: 10px 30px; text-transform: uppercase; "
            f"pointer-events: none; z-index: 998; }}"
        )
        fragmentos_html.append(f'<div class="sello-degradacion">{datos["sello_texto"]}</div>')

    # D06: Anotacion manuscrita
    if "anotacion_manuscrita" in datos:
        anot = datos["anotacion_manuscrita"]
        fragmentos_css.append(
            f".anotacion-deg {{ position: absolute; top: {anot['top']}%; "
            f"left: {anot['left']}%; transform: rotate({anot['rotacion']}deg); "
            f"font-size: {anot['tamano']}pt; color: {anot['color']}; "
            f"font-family: 'Comic Sans MS', cursive, sans-serif; "
            f"font-style: italic; pointer-events: none; z-index: 997; }}"
        )
        fragmentos_html.append(f'<div class="anotacion-deg">{anot["texto"]}</div>')

    # D09: Texto cortado
    if "texto_cortado" in datos:
        tc = datos["texto_cortado"]
        lado = tc["lado"]
        recorte = tc["recorte_mm"]
        if lado == "right":
            fragmentos_css.append(f"body {{ margin-right: -{recorte}mm; overflow: hidden; }}")
        elif lado == "bottom":
            fragmentos_css.append(f"@page {{ size: A4; margin-bottom: -{recorte}mm; }}")
        elif lado == "left":
            fragmentos_css.append(f"body {{ margin-left: -{recorte}mm; overflow: hidden; }}")

    # D10: Pliegue
    if "pliegue" in datos:
        pl = datos["pliegue"]
        fragmentos_css.append(
            f".pliegue-deg {{ position: absolute; top: {pl['posicion_y']}%; left: 0; "
            f"width: 100%; height: 2px; background: rgba(0,0,0,{pl['opacidad']}); "
            f"transform: rotate({pl['angulo']}deg); pointer-events: none; z-index: 996; }}"
        )
        fragmentos_html.append('<div class="pliegue-deg"></div>')

    # D10: Grapa
    if "grapa" in datos:
        gr = datos["grapa"]
        pos_css = "top: 10px; left: 10px;" if gr["esquina"] == "top-left" else "top: 10px; right: 10px;"
        fragmentos_css.append(
            f".grapa-deg {{ position: absolute; {pos_css} "
            f"width: {gr['tamano']}px; height: {gr['tamano'] // 2}px; "
            f"background: #888; border-radius: 2px; "
            f"transform: rotate(45deg); pointer-events: none; z-index: 996; }}"
        )
        fragmentos_html.append('<div class="grapa-deg"></div>')

    # D11: Subrayado marcador
    if "subrayado_marcador" in datos:
        sub = datos["subrayado_marcador"]
        fragmentos_css.append(
            f".marcador-deg {{ position: absolute; top: {sub['top']}%; left: 20%; "
            f"width: {sub['width']}%; height: {sub['height']}px; "
            f"background: {sub['color']}; pointer-events: none; z-index: 995; }}"
        )
        fragmentos_html.append('<div class="marcador-deg"></div>')

    # D12: Contraste bajo
    if "contraste_bajo" in datos:
        fragmentos_css.append(f"body {{ color: {datos['contraste_bajo']}; }}")

    # D13: Ruido fotocopia
    puntos = datos.get("ruido_fotocopia", [])
    if puntos:
        puntos_css = []
        for i, p in enumerate(puntos[:50]):  # limitar a 50 para no inflar el HTML
            puntos_css.append(
                f".ruido-{i} {{ position: absolute; top: {p['top']:.1f}%; "
                f"left: {p['left']:.1f}%; width: {p['size']}px; "
                f"height: {p['size']}px; background: #000; "
                f"border-radius: 50%; pointer-events: none; z-index: 994; }}"
            )
            fragmentos_html.append(f'<div class="ruido-{i}"></div>')
        fragmentos_css.extend(puntos_css)

    # Construir resultado
    resultado = ""
    if fragmentos_css:
        resultado += "<style>\n" + "\n".join(fragmentos_css) + "\n</style>\n"
    if fragmentos_html:
        resultado += "\n".join(fragmentos_html) + "\n"

    return resultado
