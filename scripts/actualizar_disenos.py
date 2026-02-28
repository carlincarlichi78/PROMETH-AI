"""Conversor Excel AEAT → YAML de diseño de registro (T23).

Uso:
    python scripts/actualizar_disenos.py --excel DR303e25v101.xlsx --modelo 303 --ejercicio 2025
    python scripts/actualizar_disenos.py --excel DR303e25v101.xlsx --modelo 303 --dry-run

El Excel de diseño de registro AEAT tiene columnas como:
  Posición inicio | Longitud | Tipo | Descripción | Casilla | ...
"""
import sys
import argparse
import yaml
from pathlib import Path

RAIZ = Path(__file__).parent.parent
sys.path.insert(0, str(RAIZ))

DISENOS_DIR = RAIZ / "sfce" / "modelos_fiscales" / "disenos"

# Mapeo de tipos AEAT a tipos internos
_TIPO_MAP = {
    "NS": "numerico_signo",
    "NUMERICO CON SIGNO": "numerico_signo",
    "AN": "alfanumerico",
    "ALFANUMERICO": "alfanumerico",
    "NUMERICO": "numerico",
    "N": "numerico",
    "A": "alfanumerico",
    "FECHA": "fecha",
    "F": "fecha",
}


def _inferir_tipo(tipo_str: str) -> str:
    tipo_norm = tipo_str.strip().upper()
    # Exact match primero
    if tipo_norm in _TIPO_MAP:
        return _TIPO_MAP[tipo_norm]
    # Substring match para descripciones largas (orden importa: mas especifico antes)
    if "CON SIGNO" in tipo_norm:
        return "numerico_signo"
    if "FECHA" in tipo_norm:
        return "fecha"
    if "ALFANUMERICO" in tipo_norm or "ALFA" in tipo_norm:
        return "alfanumerico"
    if "NUMERICO" in tipo_norm or "NUM" in tipo_norm:
        return "numerico"
    return "alfanumerico"


def _inferir_decimales(tipo_str: str, descripcion: str) -> int:
    """Infiere decimales desde tipo o descripción."""
    tipo_norm = tipo_str.strip().upper()
    if "2D" in tipo_norm or "2 DEC" in tipo_norm:
        return 2
    desc_norm = descripcion.upper()
    if "IMPORTE" in desc_norm or "BASE" in desc_norm or "CUOTA" in desc_norm:
        return 2
    return 0


def _es_casilla(nombre_campo: str) -> bool:
    """Detecta si el campo es una casilla fiscal (número)."""
    nombre = nombre_campo.strip()
    return nombre.isdigit() or (len(nombre) <= 5 and nombre.lstrip("0").isdigit())


def leer_excel_diseno(ruta_excel: Path) -> list[dict]:
    """Lee Excel AEAT y extrae campos de diseño de registro.

    Busca la hoja principal y las columnas relevantes.
    Retorna lista de dicts con keys: posicion_inicio, longitud, tipo, descripcion, casilla
    """
    try:
        import openpyxl
    except ImportError:
        print("ERROR: openpyxl no disponible. Instalar: pip install openpyxl")
        sys.exit(1)

    wb = openpyxl.load_workbook(ruta_excel, read_only=True, data_only=True)
    hoja = wb.active

    campos = []
    cabecera_fila = None
    col_indices = {}

    NOMBRES_COL = {
        "posicion": ["POS", "POSICI", "INICIO", "CAMPO", "CARACTER"],
        "longitud": ["LONG", "TAMAÑO", "TAMANO"],
        "tipo": ["TIPO", "FORMATO"],
        "descripcion": ["DESCRIPCION", "DESCRIPCIÓN", "CONCEPTO", "CONTENIDO"],
        "casilla": ["CASILLA", "NUM", "NUMERO"],
    }

    for i, row in enumerate(hoja.iter_rows(values_only=True)):
        if cabecera_fila is None:
            # Buscar fila de cabecera
            row_upper = [str(c).upper() if c else "" for c in row]
            if any("POSICI" in c or "CAMPO" in c or "LONG" in c for c in row_upper):
                cabecera_fila = i
                for j, celda in enumerate(row_upper):
                    for key, nombres in NOMBRES_COL.items():
                        if any(n in celda for n in nombres) and key not in col_indices:
                            col_indices[key] = j
            continue

        if not any(row):
            continue

        def _get(key):
            idx = col_indices.get(key)
            if idx is None:
                return ""
            val = row[idx] if idx < len(row) else None
            return str(val).strip() if val is not None else ""

        pos_str = _get("posicion")
        long_str = _get("longitud")
        tipo_str = _get("tipo") or "alfanumerico"
        descripcion = _get("descripcion")
        casilla_str = _get("casilla")

        try:
            pos_inicio = int(pos_str)
            longitud = int(long_str)
        except (ValueError, TypeError):
            continue

        pos_fin = pos_inicio + longitud - 1
        tipo = _inferir_tipo(tipo_str)
        decimales = _inferir_decimales(tipo_str, descripcion)

        nombre_campo = casilla_str or f"campo_{pos_inicio}"
        fuente = None
        if _es_casilla(casilla_str):
            fuente = f"casillas.{casilla_str.zfill(2)}"
            nombre_campo = f"casilla_{casilla_str.zfill(2)}"

        campo = {
            "nombre": nombre_campo,
            "posicion": [pos_inicio, pos_fin],
            "tipo": tipo,
        }
        if fuente:
            campo["fuente"] = fuente
        if decimales:
            campo["decimales"] = decimales
        if descripcion:
            campo["descripcion"] = descripcion

        campos.append(campo)

    wb.close()
    return campos


def generar_yaml(modelo: str, ejercicio: str, campos: list[dict]) -> dict:
    """Genera estructura YAML a partir de campos leídos."""
    longitud = max((c["posicion"][1] for c in campos), default=500)

    return {
        "modelo": modelo,
        "version": ejercicio,
        "tipo_formato": "posicional",
        "longitud_registro": longitud,
        "registros": [
            {
                "tipo": "datos",
                "campos": campos,
            }
        ],
        "validaciones": [],
    }


def comparar_con_existente(modelo: str, nuevo_yaml: dict) -> list[str]:
    """Compara con versión anterior y reporta cambios."""
    yaml_path = DISENOS_DIR / f"{modelo}.yaml"
    if not yaml_path.exists():
        return [f"NUEVO: no existe YAML previo para {modelo}"]

    with open(yaml_path, encoding="utf-8") as f:
        existente = yaml.safe_load(f)

    cambios = []
    if existente.get("longitud_registro") != nuevo_yaml.get("longitud_registro"):
        cambios.append(
            f"Longitud cambió: {existente.get('longitud_registro')} → {nuevo_yaml.get('longitud_registro')}"
        )

    campos_prev = {
        c["nombre"] for r in existente.get("registros", []) for c in r.get("campos", [])
    }
    campos_nuevo = {
        c["nombre"] for r in nuevo_yaml.get("registros", []) for c in r.get("campos", [])
    }
    añadidos = campos_nuevo - campos_prev
    eliminados = campos_prev - campos_nuevo
    if añadidos:
        cambios.append(f"Campos añadidos: {sorted(añadidos)}")
    if eliminados:
        cambios.append(f"Campos eliminados: {sorted(eliminados)}")

    return cambios or ["Sin cambios detectados"]


def main():
    parser = argparse.ArgumentParser(
        description="Convierte Excel diseño de registro AEAT a YAML"
    )
    parser.add_argument("--excel", required=True, help="Ruta al fichero Excel AEAT")
    parser.add_argument("--modelo", required=True, help="Número de modelo (ej: 303)")
    parser.add_argument("--ejercicio", default="2025", help="Ejercicio fiscal (default: 2025)")
    parser.add_argument("--dry-run", action="store_true", help="Solo muestra sin guardar")
    parser.add_argument("--force", action="store_true", help="Sobreescribe sin preguntar")
    args = parser.parse_args()

    excel_path = Path(args.excel)
    if not excel_path.exists():
        print(f"ERROR: No se encuentra el fichero {excel_path}")
        sys.exit(1)

    print(f"Leyendo {excel_path}...")
    campos = leer_excel_diseno(excel_path)
    print(f"  {len(campos)} campos leídos")

    if not campos:
        print("ERROR: No se encontraron campos válidos en el Excel")
        sys.exit(1)

    nuevo_yaml = generar_yaml(args.modelo, args.ejercicio, campos)

    print(f"\nCambios respecto a {args.modelo}.yaml:")
    cambios = comparar_con_existente(args.modelo, nuevo_yaml)
    for c in cambios:
        print(f"  - {c}")

    if args.dry_run:
        print("\n[DRY-RUN] YAML generado:")
        print(yaml.dump(nuevo_yaml, allow_unicode=True, default_flow_style=False))
        return

    yaml_path = DISENOS_DIR / f"{args.modelo}.yaml"
    if yaml_path.exists() and not args.force:
        resp = input(f"\n¿Sobreescribir {yaml_path}? [s/N]: ").strip().lower()
        if resp != "s":
            print("Cancelado.")
            return

    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(nuevo_yaml, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    print(f"\nGuardado: {yaml_path}")


if __name__ == "__main__":
    main()
