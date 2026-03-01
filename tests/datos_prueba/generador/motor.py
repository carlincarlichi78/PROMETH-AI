"""Motor principal del generador de datos de prueba SFCE.

Uso:
    python motor.py --todas --seed 42
    python motor.py --entidad aurora-digital
    python motor.py --entidad aurora-digital --trimestre T1
    python motor.py --todas --sin-errores
    python motor.py --todas --deploy
"""
import argparse
import json
import random
import shutil
import sys
import time
import yaml
from datetime import datetime, date
from pathlib import Path

# Setup paths
DIR_MOTOR = Path(__file__).resolve().parent
DIR_DATOS = DIR_MOTOR / "datos"
DIR_SALIDA = DIR_MOTOR / "salida"

sys.path.insert(0, str(DIR_MOTOR))
RAIZ = DIR_MOTOR.parents[2]  # raiz proyecto CONTABILIDAD
sys.path.insert(0, str(RAIZ))

from sfce.core.logger import crear_logger
from utils.pdf_renderer import renderizar_html, html_a_pdf, html_a_pdf_bytes
from utils.fechas import trimestre_de_fecha
from utils.ruido import aplicar_ruido, aplicar_degradacion, generar_html_degradacion
from utils.compuestos import concatenar_pdfs, insertar_pagina_blanca
from generadores.gen_facturas import generar_facturas_compra, generar_facturas_venta
from generadores.gen_nominas import generar_nominas, generar_ss
from generadores.gen_bancarios import generar_bancarios
from generadores.gen_suministros import generar_suministros
from generadores.gen_seguros import generar_seguros
from generadores.gen_impuestos import generar_impuestos
from generadores.gen_subvenciones import generar_subvenciones
from generadores.gen_intercompany import generar_intercompany
from generadores.gen_errores import inyectar_errores
from generadores.gen_provocaciones import aplicar_provocaciones
from generadores.gen_compuestos import generar_compuestos

logger = crear_logger("motor")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    """Define y parsea los argumentos de linea de comandos."""
    parser = argparse.ArgumentParser(
        description="Generador de datos de prueba contable SFCE",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python motor.py --todas --seed 42
  python motor.py --entidad aurora-digital
  python motor.py --entidad aurora-digital --trimestre T1
  python motor.py --todas --sin-errores
  python motor.py --todas --deploy
        """,
    )
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument(
        "--todas",
        action="store_true",
        help="Genera documentos para las 11 entidades",
    )
    grupo.add_argument(
        "--entidad",
        metavar="NOMBRE",
        help="Slug de la entidad (ej: aurora-digital)",
    )
    parser.add_argument(
        "--trimestre",
        choices=["T1", "T2", "T3", "T4"],
        help="Filtra documentos por trimestre",
    )
    parser.add_argument(
        "--sin-errores",
        action="store_true",
        help="No inyecta errores deliberados en los documentos",
    )
    parser.add_argument(
        "--deploy",
        action="store_true",
        help="Copia salida/ a clientes/ del proyecto CONTABILIDAD",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Seed para reproducibilidad (default: aleatorio)",
    )
    parser.add_argument(
        "--anio",
        type=int,
        default=2025,
        help="Ejercicio fiscal a generar (default: 2025)",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Carga de datos
# ---------------------------------------------------------------------------

def cargar_datos() -> dict:
    """Carga los YAML de datos/ y devuelve dict unificado."""
    archivos = {
        "empresas": DIR_DATOS / "empresas.yaml",
        "errores": DIR_DATOS / "catalogo_errores.yaml",
        "edge_cases": DIR_DATOS / "edge_cases.yaml",
        "saldos": DIR_DATOS / "saldos_2024.yaml",
    }

    resultado = {}
    for clave, ruta in archivos.items():
        if ruta.exists():
            with open(ruta, encoding="utf-8") as f:
                resultado[clave] = yaml.safe_load(f) or {}
        else:
            logger.warning(f"Archivo de datos no encontrado: {ruta}")
            resultado[clave] = {}

    return resultado


# ---------------------------------------------------------------------------
# Generacion de entidad
# ---------------------------------------------------------------------------

def generar_entidad(
    nombre: str,
    entidad: dict,
    anio: int,
    rng: random.Random,
    catalogo_errores: dict,
    sin_errores: bool,
    seed: int = 42,
) -> list:
    """
    Genera todos los documentos de una entidad para el ejercicio dado.

    Ejecuta los generadores en orden, inyecta errores si corresponde,
    aplica provocaciones y marca documentos compuestos.
    Devuelve la lista de DocGenerado sin renderizar.
    """
    docs = []

    docs.extend(generar_facturas_compra(entidad, anio, rng, seed=seed))
    docs.extend(generar_facturas_venta(entidad, anio, rng, seed=seed))

    if entidad.get("empleados_detalle"):
        docs.extend(generar_nominas(entidad, anio, rng, seed=seed))
        docs.extend(generar_ss(entidad, anio, rng, seed=seed))

    docs.extend(generar_bancarios(entidad, anio, rng, seed=seed))

    gastos = entidad.get("gastos_recurrentes", {})
    if gastos.get("suministros"):
        docs.extend(generar_suministros(entidad, anio, rng, seed=seed))
    if gastos.get("seguros"):
        docs.extend(generar_seguros(entidad, anio, rng, seed=seed))
    if gastos.get("impuestos"):
        docs.extend(generar_impuestos(entidad, anio, rng))

    if entidad.get("subvenciones"):
        docs.extend(generar_subvenciones(entidad, anio, rng))
    if entidad.get("intercompany"):
        docs.extend(generar_intercompany(entidad, anio, rng))

    if not sin_errores:
        docs = inyectar_errores(docs, catalogo_errores, rng)

    # v2: provocaciones de aprendizaje + documentos compuestos
    docs = aplicar_provocaciones(docs, rng)
    docs = generar_compuestos(docs, rng)

    return docs


# ---------------------------------------------------------------------------
# Helpers de inyeccion HTML
# ---------------------------------------------------------------------------

def _inyectar_css(html: str, css_str: str) -> str:
    """Inyecta un bloque <style> con CSS custom properties antes de </head>."""
    css_block = f"<style>\n{css_str}\n</style>"
    if "</head>" in html:
        return html.replace("</head>", f"{css_block}\n</head>", 1)
    return css_block + "\n" + html


def _inyectar_antes_body_end(html: str, fragmento: str) -> str:
    """Inyecta fragmento HTML (degradacion) justo antes de </body>."""
    if "</body>" in html:
        return html.replace("</body>", f"{fragmento}\n</body>", 1)
    return html + "\n" + fragmento


# ---------------------------------------------------------------------------
# Renderizado de un doc individual a HTML
# ---------------------------------------------------------------------------

def _renderizar_doc_a_html(doc, rng: random.Random) -> tuple[str, str]:
    """Renderiza un DocGenerado a HTML con degradaciones y variaciones CSS.

    Returns:
        Tuple (html_completo, css_base_nombre) donde css_base_nombre
        es "base_v2" para v2 o None para v1.
    """
    datos = _normalizar_datos(doc.datos_plantilla)

    # v2: degradacion avanzada segun perfil
    if doc.familia:
        datos, _degs = aplicar_degradacion(datos, doc.perfil_calidad, rng)
        degradacion_html = generar_html_degradacion(datos)
    else:
        datos = aplicar_ruido(datos, doc.tipo, rng)
        degradacion_html = ""

    html = renderizar_html(doc.plantilla, datos)

    # v2: inyectar CSS custom properties + degradacion visual
    if doc.familia:
        css_props = doc.datos_plantilla.get("variaciones_css_str", "")
        if css_props:
            html = _inyectar_css(html, css_props)
        if degradacion_html:
            html = _inyectar_antes_body_end(html, degradacion_html)

    css_base = "base_v2" if doc.familia else None
    return html, css_base


# ---------------------------------------------------------------------------
# Renderizado de documentos compuestos
# ---------------------------------------------------------------------------

def _renderizar_compuesto(
    ruta_pdf: Path,
    doc,
    compuesto: dict,
    docs_por_archivo: dict,
    rng: random.Random,
) -> None:
    """Aplica procesamiento de documento compuesto al PDF ya renderizado.

    Lee el PDF principal ya en disco, renderiza paginas extra segun el tipo
    de compuesto (M01-M06), concatena y sobreescribe el archivo.
    """
    tipo = compuesto["tipo"]
    pdf_principal = ruta_pdf.read_bytes()

    if tipo == "M01":
        # Multi-factura: concatenar PDFs de docs agrupados
        archivos_grupo = compuesto.get("docs_agrupados", [])
        pdfs = [pdf_principal]
        for archivo in archivos_grupo[1:]:  # [0] ya es el doc principal
            doc_extra = docs_por_archivo.get(archivo)
            if doc_extra:
                html_extra, css_base = _renderizar_doc_a_html(doc_extra, rng)
                pdf_bytes = html_a_pdf_bytes(html_extra, doc_extra.css_variante, css_base)
                pdfs.append(pdf_bytes)
        if len(pdfs) > 1:
            ruta_pdf.write_bytes(concatenar_pdfs(pdfs))

    elif tipo in ("M02", "M03", "M06"):
        # Renderizar pagina HTML extra (albaran, condiciones, publicidad)
        extra_html = compuesto.get("pagina_extra_html", "")
        if extra_html:
            extra_pdf = html_a_pdf_bytes(extra_html)
            posicion = compuesto.get("posicion", "despues")
            if posicion == "antes":
                ruta_pdf.write_bytes(concatenar_pdfs([extra_pdf, pdf_principal]))
            else:
                ruta_pdf.write_bytes(concatenar_pdfs([pdf_principal, extra_pdf]))

    elif tipo == "M04":
        # Email como primera pagina
        email_html = compuesto.get("email_html", "")
        if email_html:
            email_pdf = html_a_pdf_bytes(email_html)
            ruta_pdf.write_bytes(concatenar_pdfs([email_pdf, pdf_principal]))

    elif tipo == "M05":
        # Pagina en blanco
        posicion = compuesto.get("posicion", "antes")
        ruta_pdf.write_bytes(insertar_pagina_blanca(pdf_principal, posicion))


# ---------------------------------------------------------------------------
# Renderizado de PDFs
# ---------------------------------------------------------------------------

class _CallableDict(dict):
    """Dict que tambien es callable: .items() funciona y () retorna self.

    Las plantillas v2 acceden a resumen.desglose_iva.items() (como dict).
    Las plantillas v1 llaman resumen.desglose_iva() (como funcion).
    Esta clase soporta ambos usos.
    """
    def __call__(self):
        return self


def _normalizar_datos(datos: dict) -> dict:
    """Adapta keys del generador al formato que esperan las plantillas.

    Las plantillas usan factura.numero, factura.fecha, factura.serie.
    Los generadores ponen numero, fecha como keys de primer nivel.
    Esta funcion crea el sub-dict 'factura' si no existe.
    Tambien asegura que resumen.desglose_iva() funcione como metodo.
    """
    d = dict(datos)

    # Crear sub-dict 'factura' si no existe
    if "factura" not in d:
        d["factura"] = {
            "numero": d.get("numero", ""),
            "fecha": d.get("fecha", ""),
            "serie": d.get("serie", ""),
        }

    # Asegurar variables comunes con defaults
    d.setdefault("divisa", "EUR")
    d.setdefault("forma_pago", "Transferencia bancaria")
    d.setdefault("cuenta_bancaria", "")
    d.setdefault("notas", [])
    d.setdefault("pagada", False)
    d.setdefault("retencion_pct", 0)

    # Si resumen es dict (no objeto), asegurar campos y desglose_iva
    if "resumen" in d and isinstance(d["resumen"], dict):
        resumen_dict = d["resumen"]
        resumen_dict.setdefault("total_recargo", 0)
        resumen_dict.setdefault("total_retencion", 0)
        if "desglose_iva" in resumen_dict and isinstance(resumen_dict["desglose_iva"], dict):
            # Envolver en _CallableDict para que funcione como dict (.items()) y callable ()
            resumen_dict["desglose_iva"] = _CallableDict(resumen_dict["desglose_iva"])
        elif "desglose_iva" not in resumen_dict:
            # Construir desglose desde datos disponibles
            iva_tipo = resumen_dict.get("iva_tipo", 21)
            resumen_dict["desglose_iva"] = _CallableDict({
                iva_tipo: {
                    "base": resumen_dict.get("base_imponible", 0),
                    "cuota": resumen_dict.get("total_iva", 0),
                }
            })

    return d


def renderizar_docs(docs: list, dir_inbox: Path, rng: random.Random) -> int:
    """
    Renderiza cada DocGenerado a PDF en dir_inbox.

    Aplica degradacion visual (v2) o ruido (v1) segun familia.
    Maneja documentos compuestos (M01-M06) y omite docs absorbidos.

    Returns:
        Numero de PDFs generados exitosamente.
    """
    generados = 0
    # Indice para buscar docs por archivo (necesario para M01)
    docs_por_archivo = {doc.archivo: doc for doc in docs}

    for doc in docs:
        # Omitir docs absorbidos en un M01 (ya estan dentro de otro PDF)
        if doc.metadatos.get("absorbido"):
            continue

        ruta_pdf = dir_inbox / doc.archivo
        try:
            html, css_base = _renderizar_doc_a_html(doc, rng)
            html_a_pdf(html, ruta_pdf, doc.css_variante, css_base=css_base)

            # Documentos compuestos: concatenar paginas extra
            compuesto = doc.metadatos.get("compuesto")
            if compuesto:
                _renderizar_compuesto(ruta_pdf, doc, compuesto, docs_por_archivo, rng)

            generados += 1
        except Exception as exc:
            logger.warning(
                f"Error renderizando {doc.archivo} (plantilla={doc.plantilla}): {exc}"
            )

    return generados


# ---------------------------------------------------------------------------
# Manifiesto
# ---------------------------------------------------------------------------

def generar_manifiesto(
    nombre: str,
    docs: list,
    seed,
    anio: int,
) -> dict:
    """Genera el dict de manifiesto.json para una entidad."""
    # Resumen por tipo
    resumen: dict[str, int] = {}
    for d in docs:
        resumen[d.tipo] = resumen.get(d.tipo, 0) + 1

    # Errores inyectados
    docs_error = [d for d in docs if d.error_inyectado]
    conteo_errores: dict[str, int] = {}
    for d in docs_error:
        conteo_errores[d.error_inyectado] = conteo_errores.get(d.error_inyectado, 0) + 1

    # Edge cases
    docs_edge = [d for d in docs if d.edge_case]
    conteo_edge: dict[str, int] = {}
    for d in docs_edge:
        conteo_edge[d.edge_case] = conteo_edge.get(d.edge_case, 0) + 1

    # v2: Provocaciones
    docs_provocados = [d for d in docs if d.provocaciones]
    conteo_provocaciones: dict[str, int] = {}
    for d in docs_provocados:
        for p in d.provocaciones:
            conteo_provocaciones[p] = conteo_provocaciones.get(p, 0) + 1

    # v2: Compuestos
    docs_compuestos = [d for d in docs if d.metadatos.get("compuesto")]
    conteo_compuestos: dict[str, int] = {}
    for d in docs_compuestos:
        tipo_comp = d.metadatos["compuesto"]["tipo"]
        conteo_compuestos[tipo_comp] = conteo_compuestos.get(tipo_comp, 0) + 1

    # v2: Perfiles de calidad
    conteo_perfiles: dict[str, int] = {}
    for d in docs:
        if d.perfil_calidad:
            conteo_perfiles[d.perfil_calidad] = conteo_perfiles.get(d.perfil_calidad, 0) + 1

    # v2: Familias
    conteo_familias: dict[str, int] = {}
    for d in docs:
        if d.familia:
            conteo_familias[d.familia] = conteo_familias.get(d.familia, 0) + 1

    return {
        "entidad": nombre,
        "generado": datetime.now().isoformat(),
        "seed": seed,
        "anio": anio,
        "total_documentos": len(docs),
        "resumen": resumen,
        "errores_inyectados": {
            "total": len(docs_error),
            "detalle": conteo_errores,
        },
        "edge_cases": {
            "total": len(docs_edge),
            "detalle": conteo_edge,
        },
        "provocaciones": {
            "total": len(docs_provocados),
            "detalle": conteo_provocaciones,
        },
        "compuestos": {
            "total": len(docs_compuestos),
            "detalle": conteo_compuestos,
        },
        "perfiles_calidad": conteo_perfiles,
        "familias": conteo_familias,
        "documentos": [
            {
                "archivo": d.archivo,
                "tipo": d.tipo,
                "subtipo": d.subtipo,
                "fecha": d.metadatos.get("fecha", ""),
                "base": d.metadatos.get("base", 0),
                "iva_tipo": d.metadatos.get("iva_tipo", 0),
                "iva_cuota": d.metadatos.get("iva_cuota", 0),
                "total": d.metadatos.get("total", 0),
                "error_inyectado": d.error_inyectado,
                "edge_case": d.edge_case,
                "familia": d.familia,
                "perfil_calidad": d.perfil_calidad,
                "degradaciones": d.degradaciones if d.degradaciones else None,
                "provocaciones": d.provocaciones if d.provocaciones else None,
                "formato_fecha": d.formato_fecha,
                "formato_numero": d.formato_numero,
                "compuesto": d.metadatos.get("compuesto", {}).get("tipo") if d.metadatos.get("compuesto") else None,
                "absorbido": d.metadatos.get("absorbido", False),
            }
            for d in docs
        ],
    }


# ---------------------------------------------------------------------------
# Deploy
# ---------------------------------------------------------------------------

def deploy(dir_salida: Path, dir_clientes: Path) -> None:
    """Copia el contenido de salida/ a clientes/ del proyecto."""
    if not dir_salida.exists():
        logger.warning(f"Directorio de salida no existe: {dir_salida}")
        return

    for entidad_dir in dir_salida.iterdir():
        if not entidad_dir.is_dir():
            continue

        destino = dir_clientes / entidad_dir.name / "inbox_prueba"
        destino.mkdir(parents=True, exist_ok=True)

        inbox_origen = entidad_dir / "inbox"
        if inbox_origen.exists():
            for pdf in inbox_origen.glob("*.pdf"):
                shutil.copy2(pdf, destino / pdf.name)

        manifiesto_origen = entidad_dir / "manifiesto.json"
        if manifiesto_origen.exists():
            shutil.copy2(manifiesto_origen, destino / "manifiesto.json")

        logger.info(f"Deploy: {entidad_dir.name} -> {destino}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    args = parse_args()
    seed_int = args.seed if args.seed is not None else random.randint(1, 999999)
    rng = random.Random(seed_int)
    seed_usado = seed_int

    logger.info("=== Generador Datos Prueba SFCE v2 ===")
    logger.info(f"Seed: {seed_usado}, Anio: {args.anio}")

    datos = cargar_datos()
    entidades = datos["empresas"].get("entidades", {})

    if not entidades:
        logger.error("No se encontraron entidades en datos/empresas.yaml")
        sys.exit(1)

    if args.entidad:
        if args.entidad not in entidades:
            disponibles = list(entidades.keys())
            logger.error(
                f"Entidad '{args.entidad}' no encontrada. "
                f"Disponibles: {disponibles}"
            )
            sys.exit(1)
        entidades = {args.entidad: entidades[args.entidad]}

    total_docs = 0
    total_errores = 0
    total_provocaciones = 0
    total_compuestos = 0
    inicio = time.time()

    for nombre, entidad in entidades.items():
        logger.info(f"\n--- {entidad.get('nombre', nombre)} ({nombre}) ---")

        docs = generar_entidad(
            nombre,
            entidad,
            args.anio,
            rng,
            datos["errores"],
            args.sin_errores,
            seed=seed_usado,
        )

        # Filtrar por trimestre si se especifico
        if args.trimestre:
            docs = [
                d for d in docs
                if trimestre_de_fecha(
                    date.fromisoformat(d.metadatos.get("fecha", f"{args.anio}-01-01"))
                    if isinstance(d.metadatos.get("fecha"), str)
                    else d.metadatos.get("fecha", date(args.anio, 1, 1))
                ) == args.trimestre
            ]

        # Renderizar PDFs
        dir_inbox = DIR_SALIDA / nombre / "inbox"
        dir_inbox.mkdir(parents=True, exist_ok=True)
        generados = renderizar_docs(docs, dir_inbox, rng)

        # Manifiesto
        manifiesto = generar_manifiesto(nombre, docs, seed_usado, args.anio)
        ruta_manifiesto = DIR_SALIDA / nombre / "manifiesto.json"
        with open(ruta_manifiesto, "w", encoding="utf-8") as f:
            json.dump(manifiesto, f, ensure_ascii=False, indent=2, default=str)

        n_errores = len([d for d in docs if d.error_inyectado])
        n_prov = len([d for d in docs if d.provocaciones])
        n_comp = len([d for d in docs if d.metadatos.get("compuesto")])
        logger.info(
            f"  {len(docs)} docs generados, {generados} PDFs renderizados "
            f"({n_errores} errores, {n_prov} provocaciones, {n_comp} compuestos)"
        )
        total_docs += len(docs)
        total_errores += n_errores
        total_provocaciones += n_prov
        total_compuestos += n_comp

    elapsed = time.time() - inicio
    logger.info(
        f"\n=== COMPLETADO: {total_docs} docs, {total_errores} errores, "
        f"{total_provocaciones} provocaciones, {total_compuestos} compuestos, "
        f"{elapsed:.1f}s ==="
    )

    if args.deploy:
        deploy(DIR_SALIDA, RAIZ / "clientes")
        logger.info("Deploy a clientes/ completado")


if __name__ == "__main__":
    main()
