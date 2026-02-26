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

from scripts.core.logger import crear_logger
from utils.pdf_renderer import renderizar_html, html_a_pdf
from utils.fechas import trimestre_de_fecha
from utils.ruido import aplicar_ruido
from generadores.gen_facturas import generar_facturas_compra, generar_facturas_venta
from generadores.gen_nominas import generar_nominas, generar_ss
from generadores.gen_bancarios import generar_bancarios
from generadores.gen_suministros import generar_suministros
from generadores.gen_seguros import generar_seguros
from generadores.gen_impuestos import generar_impuestos
from generadores.gen_subvenciones import generar_subvenciones
from generadores.gen_intercompany import generar_intercompany
from generadores.gen_errores import inyectar_errores

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
) -> list:
    """
    Genera todos los documentos de una entidad para el ejercicio dado.

    Ejecuta los generadores en orden, inyecta errores si corresponde
    y devuelve la lista de DocGenerado sin renderizar.
    """
    docs = []

    docs.extend(generar_facturas_compra(entidad, anio, rng))
    docs.extend(generar_facturas_venta(entidad, anio, rng))

    if entidad.get("empleados_detalle"):
        docs.extend(generar_nominas(entidad, anio, rng))
        docs.extend(generar_ss(entidad, anio, rng))

    docs.extend(generar_bancarios(entidad, anio, rng))

    gastos = entidad.get("gastos_recurrentes", {})
    if gastos.get("suministros"):
        docs.extend(generar_suministros(entidad, anio, rng))
    if gastos.get("seguros"):
        docs.extend(generar_seguros(entidad, anio, rng))
    if gastos.get("impuestos"):
        docs.extend(generar_impuestos(entidad, anio, rng))

    if entidad.get("subvenciones"):
        docs.extend(generar_subvenciones(entidad, anio, rng))
    if entidad.get("intercompany"):
        docs.extend(generar_intercompany(entidad, anio, rng))

    if not sin_errores:
        docs = inyectar_errores(docs, catalogo_errores, rng)

    return docs


# ---------------------------------------------------------------------------
# Renderizado de PDFs
# ---------------------------------------------------------------------------

def renderizar_docs(docs: list, dir_inbox: Path, rng: random.Random) -> int:
    """
    Renderiza cada DocGenerado a PDF en dir_inbox.

    Aplica ruido visual antes del renderizado. Captura errores de renderizado
    individuales, los logea como warning y continua con el siguiente documento.

    Returns:
        Numero de PDFs generados exitosamente.
    """
    generados = 0
    for doc in docs:
        ruta_pdf = dir_inbox / doc.archivo
        try:
            datos = aplicar_ruido(doc.datos_plantilla, doc.tipo, rng)
            html = renderizar_html(doc.plantilla, datos)
            html_a_pdf(html, ruta_pdf, doc.css_variante)
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
    rng = random.Random(args.seed) if args.seed else random.Random()
    seed_usado = args.seed if args.seed is not None else "aleatorio"

    logger.info("=== Generador Datos Prueba SFCE ===")
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
        logger.info(
            f"  {len(docs)} docs generados, {generados} PDFs renderizados "
            f"({n_errores} con errores)"
        )
        total_docs += len(docs)
        total_errores += n_errores

    elapsed = time.time() - inicio
    logger.info(
        f"\n=== COMPLETADO: {total_docs} docs, {total_errores} errores, "
        f"{elapsed:.1f}s ==="
    )

    if args.deploy:
        deploy(DIR_SALIDA, RAIZ / "clientes")
        logger.info("Deploy a clientes/ completado")


if __name__ == "__main__":
    main()
