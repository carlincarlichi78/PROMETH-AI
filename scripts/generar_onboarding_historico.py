#!/usr/bin/env python3
"""
Genera paquete de documentación fiscal histórica para onboarding de cliente.

Uso:
    python scripts/generar_onboarding_historico.py --cliente marcos-ruiz --ejercicio 2024
    python scripts/generar_onboarding_historico.py --cliente restaurante-la-marea --ejercicio 2024
    python scripts/generar_onboarding_historico.py --todos --ejercicio 2024
"""
import argparse
import sys
from pathlib import Path
import yaml

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from sfce.modelos_fiscales.generador_pdf import GeneradorPDF


MODELOS_AUTONOMO = ["303", "390", "130", "111", "190"]
MODELOS_SL       = ["303", "390", "111", "190", "115", "180"]

# Secciones del YAML → código modelo
_SECCION_A_MODELO = {
    "modelo_303": "303",
    "modelo_390": "390",
    "modelo_130": "130",
    "modelo_111": "111",
    "modelo_190": "190",
    "modelo_115": "115",
    "modelo_180": "180",
    "modelo_347": "347",
    "modelo_349": "349",
}


def _empresa_para_generador(datos: dict) -> dict:
    """Adapta los datos del YAML al formato que espera GeneradorPDF."""
    e = datos["empresa"]
    return {
        "nif": e["nif"],
        "nombre": e["nombre"],
        "domicilio": e.get("domicilio", ""),
        "telefono": e.get("telefono", ""),
        "email": e.get("email", ""),
    }


def _generar_modelo_trimestral(
    gen: GeneradorPDF,
    modelo: str,
    datos_modelo: dict,
    empresa: dict,
    ejercicio: str,
    directorio: Path,
) -> list[Path]:
    """Genera un PDF por trimestre para modelos trimestrales."""
    generados = []
    trimestres = datos_modelo.get("trimestres", {})
    for periodo, datos_periodo in trimestres.items():
        casillas = datos_periodo.get("casillas", {})
        pdf_bytes = gen.generar(
            modelo=modelo,
            casillas={str(k): v for k, v in casillas.items()},
            empresa=empresa,
            ejercicio=ejercicio,
            periodo=periodo,
        )
        nombre = f"modelo_{modelo}_{periodo}_{ejercicio}"
        ruta = gen.guardar(pdf_bytes, directorio, nombre)
        print(f"  ✓ {ruta.name}")
        generados.append(ruta)
    return generados


def _generar_modelo_anual(
    gen: GeneradorPDF,
    modelo: str,
    datos_modelo: dict,
    empresa: dict,
    ejercicio: str,
    directorio: Path,
) -> Path:
    """Genera un PDF anual (resumen) para un modelo."""
    casillas = datos_modelo.get("casillas", {})
    pdf_bytes = gen.generar(
        modelo=modelo,
        casillas={str(k): v for k, v in casillas.items()},
        empresa=empresa,
        ejercicio=ejercicio,
        periodo="0A",
    )
    nombre = f"modelo_{modelo}_anual_{ejercicio}"
    ruta = gen.guardar(pdf_bytes, directorio, nombre)
    print(f"  ✓ {ruta.name}")
    return ruta


def _balance_a_casillas(datos_balance: dict, tipo: str) -> dict:
    """Convierte estructura balance/pyg a dict plano de casillas."""
    casillas = {}
    if tipo == "balance":
        n = 1
        for grupo_nombre, grupo in datos_balance.get("activo", {}).items():
            for item in grupo:
                casillas[str(n)] = item.get("valor_neto", item.get("importe", 0))
                casillas[f"{n}_desc"] = item.get("descripcion", "")
                n += 1
    elif tipo == "cuenta_pyg":
        for item in datos_balance.get("ingresos", []):
            casillas[item["cuenta"]] = item["importe"]
        for item in datos_balance.get("gastos", []):
            casillas[item["cuenta"]] = -item["importe"]
        casillas["resultado"] = datos_balance.get("resultado_ejercicio", 0)
    return casillas


def _generar_balance_pyg(datos: dict, ejercicio: str, directorio: Path) -> list[Path]:
    """Genera PDFs de balance de situación y cuenta P&G usando plantilla HTML."""
    gen = GeneradorPDF()
    generados = []

    for seccion, nombre_doc in [("balance", "balance_situacion"), ("cuenta_pyg", "cuenta_pyg")]:
        if seccion not in datos:
            continue
        casillas = _balance_a_casillas(datos[seccion], seccion)
        pdf_bytes = gen.generar(
            modelo=seccion,
            casillas=casillas,
            empresa=_empresa_para_generador(datos),
            ejercicio=ejercicio,
            periodo="0A",
        )
        nombre = f"{nombre_doc}_{ejercicio}"
        ruta = gen.guardar(pdf_bytes, directorio, nombre)
        print(f"  ✓ {ruta.name}")
        generados.append(ruta)

    return generados


def generar_onboarding(slug: str, ejercicio: str) -> list[Path]:
    """Genera todos los documentos de onboarding para un cliente."""
    datos_path = RAIZ / "clientes" / slug / f"datos_fiscales_{ejercicio}.yaml"
    if not datos_path.exists():
        print(f"ERROR: No existe {datos_path}")
        return []

    datos = yaml.safe_load(datos_path.read_text(encoding="utf-8"))
    empresa = _empresa_para_generador(datos)
    directorio = RAIZ / "clientes" / slug / f"onboarding_{ejercicio}"
    directorio.mkdir(parents=True, exist_ok=True)

    gen = GeneradorPDF()
    generados = []

    print(f"\n{'='*60}")
    print(f"Generando onboarding {slug} — ejercicio {ejercicio}")
    print(f"Destino: {directorio}")
    print(f"{'='*60}")

    for seccion, modelo in _SECCION_A_MODELO.items():
        if seccion not in datos:
            continue
        datos_modelo = datos[seccion]
        print(f"\n[Modelo {modelo}]")
        if "trimestres" in datos_modelo:
            rutas = _generar_modelo_trimestral(
                gen, modelo, datos_modelo, empresa, ejercicio, directorio
            )
            generados.extend(rutas)
        else:
            ruta = _generar_modelo_anual(
                gen, modelo, datos_modelo, empresa, ejercicio, directorio
            )
            generados.append(ruta)

    print("\n[Balance + P&G]")
    generados.extend(_generar_balance_pyg(datos, ejercicio, directorio))

    print(f"\n{'='*60}")
    print(f"TOTAL generados: {len(generados)} PDFs en {directorio}")
    return generados


def main():
    parser = argparse.ArgumentParser(description="Genera documentacion fiscal historica para onboarding")
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--cliente", help="Slug del cliente (ej: marcos-ruiz)")
    grupo.add_argument("--todos", action="store_true", help="Genera para todos los clientes con datos")
    parser.add_argument("--ejercicio", default="2024", help="Ejercicio fiscal (default: 2024)")
    args = parser.parse_args()

    if args.todos:
        slugs = [
            p.parent.name
            for p in (RAIZ / "clientes").glob(f"*/datos_fiscales_{args.ejercicio}.yaml")
        ]
        print(f"Clientes encontrados: {slugs}")
    else:
        slugs = [args.cliente]

    for slug in slugs:
        generar_onboarding(slug, args.ejercicio)


if __name__ == "__main__":
    main()
