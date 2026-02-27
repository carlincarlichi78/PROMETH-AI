"""Generador de PDFs visuales para modelos fiscales AEAT.

Estrategia dual:
1. PDF rellenable (primario): rellena formulario PDF oficial AEAT con pypdf
2. HTML→PDF (fallback): genera HTML con Jinja2 y renderiza con WeasyPrint
"""
import io
import os
from datetime import date
from pathlib import Path
from typing import Any

# pypdf para rellenar PDFs de formulario
try:
    from pypdf import PdfReader, PdfWriter
    _PYPDF_OK = True
except ImportError:
    _PYPDF_OK = False

# jinja2 para plantilla HTML
try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    _JINJA2_OK = True
except ImportError:
    _JINJA2_OK = False

# WeasyPrint para HTML→PDF
try:
    import weasyprint
    _WEASYPRINT_OK = True
except ImportError:
    _WEASYPRINT_OK = False


_DIR_PLANTILLAS_PDF = Path(__file__).parent / "plantillas_pdf"
_DIR_PLANTILLAS_HTML = Path(__file__).parent / "plantillas_html"

# Nombres descriptivos de modelos
_NOMBRES_MODELOS = {
    "303": "Autoliquidación IVA (trimestral)",
    "390": "Resumen anual IVA",
    "349": "Operaciones intracomunitarias",
    "347": "Operaciones con terceros >3.005 €",
    "340": "Libros registro IVA (SII)",
    "420": "IGIC Canarias",
    "111": "Retenciones trabajo/actividades profesionales",
    "190": "Resumen anual retenciones",
    "115": "Retenciones arrendamientos",
    "180": "Resumen anual arrendamientos",
    "123": "Retenciones capital mobiliario",
    "193": "Resumen anual capital mobiliario",
    "130": "Pago fraccionado IRPF (estimación directa)",
    "131": "Pago fraccionado IRPF (módulos)",
    "200": "Impuesto sobre Sociedades",
    "202": "Pagos fraccionados IS",
    "100": "Renta — datos actividad económica",
    "036": "Declaración censal (alta/modificación)",
    "037": "Declaración censal simplificada",
    "210": "IRNR sin establecimiento permanente",
    "216": "Retenciones no residentes",
    "296": "Resumen anual no residentes",
    "720": "Bienes y derechos en el extranjero",
    "360": "Devolución IVA extranjero",
}

_NOMBRES_PERIODOS = {
    "1T": "1.er Trimestre", "2T": "2.º Trimestre",
    "3T": "3.er Trimestre", "4T": "4.º Trimestre",
    "0A": "Resumen anual", "1M": "Enero", "2M": "Febrero",
    "3M": "Marzo", "4M": "Abril", "5M": "Mayo", "6M": "Junio",
    "7M": "Julio", "8M": "Agosto", "9M": "Septiembre",
    "10M": "Octubre", "11M": "Noviembre", "12M": "Diciembre",
}

# Descripciones de casillas principales
_DESCRIPCIONES_CASILLAS = {
    "303": {
        "01": "Base imponible — Tipo general (21%)",
        "02": "Tipo impositivo (%)",
        "03": "Cuota — Tipo general",
        "04": "Base imponible — Tipo reducido (10%)",
        "06": "Cuota — Tipo reducido",
        "07": "Base imponible — Tipo superreducido (4%)",
        "09": "Cuota — Tipo superreducido",
        "27": "Total cuotas devengadas",
        "28": "Base — IVA deducible bienes y servicios",
        "29": "Cuota — IVA deducible bienes y servicios",
        "37": "Total a deducir",
        "45": "Diferencia (casilla 27 – 37)",
        "64": "Resultado de la liquidación",
        "69": "Resultado a ingresar / a devolver",
        "71": "A devolver",
        "77": "IVA diferido importaciones",
        "78": "Compensación de saldos anteriores",
    },
    "111": {
        "02": "Rendimientos del trabajo — Importe satisfecho",
        "03": "Rendimientos del trabajo — Retenciones",
        "05": "Rendimientos actividades económicas — Importe",
        "06": "Rendimientos actividades económicas — Retenciones",
        "28": "Total retenciones e ingresos a cuenta",
        "29": "Retenciones ingresadas trimestres anteriores",
        "30": "Resultado",
    },
    "130": {
        "01": "Ingresos actividades acumulados",
        "02": "Gastos deducibles acumulados",
        "03": "Rendimiento neto (01 – 02)",
        "04": "Porcentaje aplicable (%)",
        "05": "Importe (03 × 04 / 100)",
        "07": "Pagos fraccionados trimestres anteriores",
        "13": "Resultado parcial (05 – 07)",
        "16": "Retenciones soportadas",
        "17": "Retenciones ya ingresadas",
        "18": "Resultado (13 – 16 – 17)",
        "19": "Resultado de la liquidación",
    },
    "115": {
        "01": "Número de arrendadores",
        "02": "Base imponible",
        "03": "Retenciones practicadas",
        "04": "Resultado",
    },
    "347": {
        "num_declarados": "Número de declarados",
    },
    "349": {
        "num_declarados": "Número de declarados",
        "total_entregas": "Total entregas intracomunitarias (E)",
        "total_adquisiciones": "Total adquisiciones intracomunitarias (A)",
        "total_servicios_prestados": "Servicios prestados (S)",
        "total_servicios_recibidos": "Servicios recibidos (I)",
    },
}


class GeneradorPDF:
    """Genera PDFs visuales de modelos fiscales.

    Intenta rellenar el PDF formulario oficial de la AEAT.
    Si no existe plantilla PDF, usa fallback HTML→PDF.
    """

    def __init__(
        self,
        directorio_plantillas_pdf: Path | None = None,
        directorio_plantillas_html: Path | None = None,
    ):
        self._dir_pdf = directorio_plantillas_pdf or _DIR_PLANTILLAS_PDF
        self._dir_html = directorio_plantillas_html or _DIR_PLANTILLAS_HTML

    def generar(
        self,
        modelo: str,
        casillas: dict,
        empresa: dict,
        ejercicio: str,
        periodo: str,
    ) -> bytes:
        """Genera PDF del modelo fiscal.

        Intenta primero rellenar PDF oficial. Si no existe, genera HTML→PDF.

        Args:
            modelo: Código del modelo ("303", "111", etc.)
            casillas: Dict con valores de casillas
            empresa: Datos empresa {nif, nombre, ...}
            ejercicio: Año fiscal
            periodo: Período (1T, 2T, 3T, 4T, 0A)

        Returns:
            bytes del PDF generado
        """
        ruta_pdf = self._dir_pdf / f"{modelo}.pdf"

        if _PYPDF_OK and ruta_pdf.exists():
            try:
                return self._rellenar_pdf_formulario(
                    ruta_pdf, modelo, casillas, empresa, ejercicio, periodo
                )
            except Exception:
                pass  # fallback a HTML

        return self._generar_html_pdf(modelo, casillas, empresa, ejercicio, periodo)

    def guardar(
        self,
        pdf_bytes: bytes,
        directorio: Path,
        nombre: str,
    ) -> Path:
        """Guarda PDF en disco.

        Args:
            pdf_bytes: Contenido del PDF
            directorio: Carpeta destino (se crea si no existe)
            nombre: Nombre del archivo (sin extensión .pdf)

        Returns:
            Path al archivo creado
        """
        directorio.mkdir(parents=True, exist_ok=True)
        nombre_archivo = nombre if nombre.endswith(".pdf") else f"{nombre}.pdf"
        ruta = directorio / nombre_archivo
        ruta.write_bytes(pdf_bytes)
        return ruta

    def _rellenar_pdf_formulario(
        self,
        ruta_plantilla: Path,
        modelo: str,
        casillas: dict,
        empresa: dict,
        ejercicio: str,
        periodo: str,
    ) -> bytes:
        """Rellena los campos de un formulario PDF oficial AEAT."""
        reader = PdfReader(str(ruta_plantilla))
        writer = PdfWriter()

        for page in reader.pages:
            writer.add_page(page)

        # Mapear casillas a campos del formulario PDF
        campos_pdf = self._construir_campos_pdf(modelo, casillas, empresa, ejercicio, periodo)

        if writer.pages:
            writer.update_page_form_field_values(writer.pages[0], campos_pdf)

        buffer = io.BytesIO()
        writer.write(buffer)
        return buffer.getvalue()

    def _construir_campos_pdf(
        self,
        modelo: str,
        casillas: dict,
        empresa: dict,
        ejercicio: str,
        periodo: str,
    ) -> dict[str, str]:
        """Construye el mapa campo_pdf → valor para el formulario."""
        campos: dict[str, str] = {}

        # Campos comunes
        campos["NIF"] = empresa.get("nif", "")
        campos["APELLIDOS_NOMBRE"] = empresa.get("nombre_fiscal", empresa.get("nombre", ""))
        campos["EJERCICIO"] = ejercicio
        campos["PERIODO"] = periodo
        campos["MODELO"] = modelo

        # Casillas numericas
        for clave, valor in casillas.items():
            if isinstance(valor, (int, float)):
                # Formato europeo: 1.234,56
                campos[f"CASILLA_{clave.upper()}"] = _formatear_importe(float(valor))
            else:
                campos[f"CASILLA_{clave.upper()}"] = str(valor)

        return campos

    def _generar_html_pdf(
        self,
        modelo: str,
        casillas: dict,
        empresa: dict,
        ejercicio: str,
        periodo: str,
    ) -> bytes:
        """Genera PDF desde plantilla HTML con WeasyPrint."""
        html = self._renderizar_html(modelo, casillas, empresa, ejercicio, periodo)

        if _WEASYPRINT_OK:
            return _html_a_pdf_bytes(html)
        else:
            raise RuntimeError(
                "WeasyPrint no disponible y no hay PDF template para este modelo. "
                "Instala weasyprint o añade el PDF oficial a plantillas_pdf/"
            )

    def _renderizar_html(
        self,
        modelo: str,
        casillas: dict,
        empresa: dict,
        ejercicio: str,
        periodo: str,
    ) -> str:
        """Renderiza la plantilla HTML con los datos del modelo."""
        if _JINJA2_OK and self._dir_html.exists():
            env = Environment(
                loader=FileSystemLoader(str(self._dir_html)),
                autoescape=select_autoescape(["html"])
            )
            template = env.get_template("base_modelo.html")
        else:
            # Plantilla inline de emergencia
            return self._html_emergencia(modelo, casillas, empresa, ejercicio, periodo)

        descripciones = _DESCRIPCIONES_CASILLAS.get(modelo, {})
        secciones = _agrupar_casillas_en_secciones(modelo, casillas, descripciones)

        return template.render(
            modelo=modelo,
            nombre_modelo=_NOMBRES_MODELOS.get(modelo, f"Modelo {modelo}"),
            ejercicio=ejercicio,
            periodo=periodo,
            periodo_nombre=_NOMBRES_PERIODOS.get(periodo, periodo),
            empresa=empresa,
            secciones=secciones,
            fecha_generacion=date.today().strftime("%d/%m/%Y"),
        )

    def _html_emergencia(
        self,
        modelo: str,
        casillas: dict,
        empresa: dict,
        ejercicio: str,
        periodo: str,
    ) -> str:
        """Plantilla HTML minima de emergencia (sin Jinja2)."""
        filas = ""
        for k, v in sorted(casillas.items()):
            if isinstance(v, (int, float)):
                filas += f"<tr><td>[{k}]</td><td>{_formatear_importe(float(v))}</td></tr>"

        return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>body{{font-family:Arial;font-size:10px;padding:20px}}
h1{{font-size:14px}}table{{border-collapse:collapse;width:100%}}
td{{border:1px solid #ccc;padding:4px 8px}}</style>
</head><body>
<h1>Modelo {modelo} — {_NOMBRES_MODELOS.get(modelo, modelo)}</h1>
<p><strong>NIF:</strong> {empresa.get('nif','')} &nbsp;
<strong>Nombre:</strong> {empresa.get('nombre','')} &nbsp;
<strong>Ejercicio:</strong> {ejercicio} &nbsp;
<strong>Periodo:</strong> {periodo}</p>
<table><tr><th>Casilla</th><th>Importe (€)</th></tr>{filas}</table>
</body></html>"""


# ─────────────────────────── helpers ───────────────────────────

def _formatear_importe(valor: float) -> str:
    """Formatea importe en euros con separadores europeos."""
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _html_a_pdf_bytes(html: str) -> bytes:
    """Convierte HTML a PDF usando WeasyPrint."""
    if not _WEASYPRINT_OK:
        raise RuntimeError("WeasyPrint no disponible")
    buf = io.BytesIO()
    weasyprint.HTML(string=html).write_pdf(buf)
    return buf.getvalue()


def _agrupar_casillas_en_secciones(
    modelo: str,
    casillas: dict,
    descripciones: dict,
) -> list[dict]:
    """Organiza casillas en secciones para la plantilla HTML."""
    # Casillas que representan resultado (se destacan)
    casillas_resultado = {"45", "64", "69", "71", "19", "30", "resultado", "04"}

    items = []
    for clave, valor in sorted(casillas.items(), key=lambda x: str(x[0]).zfill(5)):
        if not isinstance(valor, (int, float)):
            continue
        items.append({
            "numero": str(clave),
            "descripcion": descripciones.get(str(clave), f"Casilla {clave}"),
            "valor_fmt": _formatear_importe(float(valor)),
            "destacada": str(clave) in casillas_resultado,
        })

    if not items:
        return []

    return [{"titulo": "Datos del modelo", "casillas": items}]
