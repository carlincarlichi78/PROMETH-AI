"""
Modulo de renderizado HTML a PDF usando Jinja2 + WeasyPrint.

Nucleo del generador de datos de prueba: carga plantillas HTML,
aplica datos y produce PDFs con estilos CSS.
"""

import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

# Raiz del proyecto CONTABILIDAD (4 niveles arriba de este archivo)
RAIZ = Path(__file__).resolve().parents[4]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from sfce.core.logger import crear_logger

logger = crear_logger("pdf_renderer")

DIR_GENERADOR = Path(__file__).resolve().parents[1]
DIR_PLANTILLAS = DIR_GENERADOR / "plantillas"
DIR_CSS = DIR_GENERADOR / "css"


# ---------------------------------------------------------------------------
# Filtros Jinja2
# ---------------------------------------------------------------------------

def _filtro_moneda(valor, divisa: str = "EUR") -> str:
    """
    Formatea un numero como moneda en formato espanol.

    Ejemplos:
        1234.56  -> "1.234,56 EUR"
        100      -> "100,00 EUR"
        0.5      -> "0,50 EUR"
    """
    # 1. Formatear con 2 decimales (usa punto decimal por defecto en Python)
    formateado = f"{float(valor):.2f}"
    # 2. Separar parte entera y decimal
    parte_entera, parte_decimal = formateado.split(".")
    # 3. Agregar separador de miles con punto en la parte entera
    parte_entera_con_miles = ""
    for i, digito in enumerate(reversed(parte_entera)):
        if i > 0 and i % 3 == 0:
            parte_entera_con_miles = "." + parte_entera_con_miles
        parte_entera_con_miles = digito + parte_entera_con_miles
    # 4. Unir con coma decimal y agregar simbolo de divisa
    return f"{parte_entera_con_miles},{parte_decimal} {divisa}"


def _filtro_fecha_es(fecha) -> str:
    """
    Formatea una fecha como 'dd/mm/yyyy'.

    Acepta objetos date, datetime o strings ISO (yyyy-mm-dd).
    """
    if fecha is None:
        return ""
    if isinstance(fecha, str):
        from datetime import date as _date
        try:
            fecha = _date.fromisoformat(fecha)
        except (ValueError, TypeError):
            return str(fecha)
    return fecha.strftime("%d/%m/%Y")


def _filtro_porcentaje(valor) -> str:
    """
    Formatea un numero como porcentaje en formato espanol.

    Ejemplos:
        21   -> "21,00%"
        0.5  -> "0,50%"
    """
    formateado = f"{float(valor):.2f}"
    # Reemplazar punto decimal por coma
    return formateado.replace(".", ",") + "%"


# ---------------------------------------------------------------------------
# Entorno Jinja2
# ---------------------------------------------------------------------------

_env = Environment(
    loader=FileSystemLoader(str(DIR_PLANTILLAS)),
    autoescape=False,
    trim_blocks=True,
    lstrip_blocks=True,
)
_env.filters["moneda"] = _filtro_moneda
_env.filters["fecha_es"] = _filtro_fecha_es
_env.filters["porcentaje"] = _filtro_porcentaje


# ---------------------------------------------------------------------------
# Funciones publicas
# ---------------------------------------------------------------------------

def renderizar_html(plantilla: str, datos: dict) -> str:
    """
    Carga una plantilla Jinja2 por nombre y la renderiza con los datos dados.

    Args:
        plantilla: Nombre del archivo de plantilla (ej: "factura_simple.html").
        datos: Diccionario con las variables a inyectar en la plantilla.

    Returns:
        HTML renderizado como string.
    """
    tmpl = _env.get_template(plantilla)
    html = tmpl.render(**datos)
    logger.debug(f"Plantilla '{plantilla}' renderizada ({len(html)} caracteres)")
    return html


def _construir_hojas_css(css_variante: str = "corporativo", css_base: str = None) -> list:
    """Construye la lista de hojas de estilo CSS para WeasyPrint.

    Args:
        css_variante: Nombre (sin extension) del CSS de variante.
        css_base: Nombre del CSS base (sin extension). None="base", "base_v2" para v2.

    Returns:
        Lista de objetos weasyprint.CSS.
    """
    import weasyprint

    nombre_base = css_base or "base"
    hojas_css = []
    rutas_css = [
        DIR_CSS / f"{nombre_base}.css",
        DIR_CSS / "variantes" / f"{css_variante}.css",
    ]
    for ruta_css in rutas_css:
        if ruta_css.exists():
            hojas_css.append(weasyprint.CSS(filename=str(ruta_css)))
            logger.debug(f"CSS cargado: {ruta_css.name}")
        else:
            if "variantes" not in str(ruta_css) or css_variante != "corporativo":
                logger.warning(f"CSS no encontrado, se omite: {ruta_css}")
    return hojas_css


def html_a_pdf(
    html: str,
    ruta_salida: Path,
    css_variante: str = "corporativo",
    css_base: str = None,
) -> Path:
    """
    Convierte un string HTML a PDF usando WeasyPrint.

    Carga el CSS base y la variante indicada si existen en DIR_CSS.

    Args:
        html: Contenido HTML como string.
        ruta_salida: Ruta donde guardar el PDF resultante.
        css_variante: Nombre (sin extension) del CSS de variante a cargar.
        css_base: Nombre del CSS base (sin extension). None="base", "base_v2" para v2.

    Returns:
        Ruta al PDF generado.
    """
    import weasyprint

    ruta_salida = Path(ruta_salida)
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)

    hojas_css = _construir_hojas_css(css_variante, css_base)

    doc = weasyprint.HTML(string=html)
    doc.write_pdf(str(ruta_salida), stylesheets=hojas_css if hojas_css else None)

    tamano_kb = ruta_salida.stat().st_size / 1024
    logger.info(f"PDF generado: {ruta_salida} ({tamano_kb:.1f} KB)")

    return ruta_salida


def html_a_pdf_bytes(
    html: str,
    css_variante: str = "corporativo",
    css_base: str = None,
) -> bytes:
    """
    Renderiza HTML a PDF y devuelve los bytes (sin guardar a archivo).

    Util para documentos compuestos que necesitan concatenarse.

    Args:
        html: Contenido HTML como string.
        css_variante: Nombre (sin extension) del CSS de variante.
        css_base: Nombre del CSS base. None="base", "base_v2" para v2.

    Returns:
        PDF como bytes.
    """
    import weasyprint

    hojas_css = _construir_hojas_css(css_variante, css_base)
    doc = weasyprint.HTML(string=html)
    return doc.write_pdf(stylesheets=hojas_css if hojas_css else None)


def generar_pdf(
    plantilla: str,
    datos: dict,
    ruta_salida: Path,
    css_variante: str = "corporativo",
    css_base: str = None,
) -> Path:
    """
    Shortcut que combina renderizar_html + html_a_pdf en un solo paso.

    Args:
        plantilla: Nombre del archivo de plantilla Jinja2.
        datos: Variables para la plantilla.
        ruta_salida: Ruta de destino del PDF.
        css_variante: Nombre del CSS de variante (sin extension).
        css_base: Nombre del CSS base. None="base", "base_v2" para v2.

    Returns:
        Ruta al PDF generado.
    """
    html = renderizar_html(plantilla, datos)
    return html_a_pdf(html, ruta_salida, css_variante, css_base=css_base)
