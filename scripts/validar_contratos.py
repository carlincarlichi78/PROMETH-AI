"""Valida JSONs intermedios del pipeline contra sus contratos.

Uso:
  python scripts/validar_contratos.py --cliente pastorino-costa-del-sol
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from sfce.core.contracts import validar_json_pipeline, _CONTRATOS_POR_ARCHIVO


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cliente", required=True)
    args = parser.parse_args()

    ruta = Path("clientes") / args.cliente
    if not ruta.exists():
        print(f"No existe: {ruta}")
        return 1

    total, ok, fail = 0, 0, 0
    for nombre in _CONTRATOS_POR_ARCHIVO:
        ruta_json = ruta / nombre
        if not ruta_json.exists():
            continue
        total += 1
        valido, errores = validar_json_pipeline(str(ruta_json))
        if valido:
            ok += 1
            print(f"  [OK] {nombre}")
        else:
            fail += 1
            print(f"  [FAIL] {nombre}")
            for e in errores[:3]:
                print(f"    → {e[:200]}")

    print(f"\nResultado: {ok}/{total} válidos, {fail} con errores")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
