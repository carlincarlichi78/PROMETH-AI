"""Crea empresas en una instancia FS específica para una gestoría.

Uso:
    export FS_API_URL=https://fs-uralde.prometh-ai.es/api/3
    export FS_API_TOKEN=TOKEN_URALDE
    python scripts/setup_fs_instancia.py --gestoria-id 1

O directamente:
    python scripts/setup_fs_instancia.py --gestoria-id 1 \\
        --fs-url https://fs-uralde.prometh-ai.es/api/3 \\
        --fs-token TOKEN_URALDE

Opciones:
    --gestoria-id   ID de la gestoría en SFCE (obligatorio)
    --fs-url        URL base API FS. Alternativa: env FS_API_URL
    --fs-token      Token API FS. Alternativa: env FS_API_TOKEN
    --anio          Año del ejercicio a crear (default: 2025)
    --dry-run       Muestra lo que haría sin crear nada
"""
import sys
import io
import os
import argparse

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sfce.core.fs_setup import FsSetup
from sfce.db.base import crear_motor
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

ANIO_DEFAULT = 2025


def _pgc(forma_juridica: str) -> str:
    """PGC según forma jurídica: pymes para SL/SA, general para el resto."""
    if forma_juridica and forma_juridica.lower() in ("sl", "sa", "slu", "slp"):
        return "pymes"
    return "general"


def main():
    parser = argparse.ArgumentParser(
        description="Crea empresas de una gestoría en su instancia FS propia"
    )
    parser.add_argument("--gestoria-id", type=int, required=True, help="ID gestoría en SFCE")
    parser.add_argument(
        "--fs-url",
        help="URL base API FS (ej: https://fs-uralde.prometh-ai.es/api/3). Alternativa: env FS_API_URL",
    )
    parser.add_argument(
        "--fs-token",
        help="Token API FS. Alternativa: env FS_API_TOKEN",
    )
    parser.add_argument(
        "--anio", type=int, default=ANIO_DEFAULT, help=f"Año ejercicio (default: {ANIO_DEFAULT})"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Solo mostrar qué haría, sin crear nada"
    )
    args = parser.parse_args()

    fs_url = args.fs_url or os.getenv("FS_API_URL")
    fs_token = args.fs_token or os.getenv("FS_API_TOKEN")

    if not fs_url or not fs_token:
        print("ERROR: necesitas --fs-url + --fs-token o variables FS_API_URL + FS_API_TOKEN")
        sys.exit(1)

    motor = crear_motor({"tipo_bd": "sqlite", "ruta_bd": "sfce.db"})
    Session = sessionmaker(bind=motor)
    fs = FsSetup(base_url=fs_url, token=fs_token)

    print(f"FS URL: {fs_url}")
    print(f"Gestoría ID: {args.gestoria_id}")
    print(f"Año: {args.anio}")
    print()

    with Session() as s:
        empresas = s.execute(text("""
            SELECT id, nombre, cif, forma_juridica, idempresa_fs
            FROM empresas
            WHERE gestoria_id = :gid
            ORDER BY id
        """), {"gid": args.gestoria_id}).fetchall()

        if not empresas:
            print(f"No hay empresas para gestoria_id={args.gestoria_id}")
            return

        for sfce_id, nombre, cif, forma, idempresa_fs in empresas:
            if idempresa_fs:
                print(f"  [YA EN FS]  {nombre} (idempresa_fs={idempresa_fs})")
                continue

            cif_fs = cif if cif and not cif.startswith("PEND-") else ""
            pgc = _pgc(forma)

            print(f"  {'[DRY-RUN] ' if args.dry_run else ''}Creando: {nombre} | CIF={cif_fs or '(vacío)'} | PGC={pgc}")

            if args.dry_run:
                continue

            try:
                r = fs.setup_completo(nombre=nombre, cif=cif_fs, anio=args.anio, tipo_pgc=pgc)
                if r.idempresa_fs:
                    s.execute(text("""
                        UPDATE empresas SET idempresa_fs=:idf, codejercicio_fs=:cej
                        WHERE id=:sid
                    """), {"idf": r.idempresa_fs, "cej": r.codejercicio, "sid": sfce_id})
                    s.commit()
                    pgc_ok = "✓" if r.pgc_importado else "✗"
                    print(f"    ✓ idempresa_fs={r.idempresa_fs}, codejercicio={r.codejercicio}, PGC={pgc_ok}")
                else:
                    print(f"    ✗ Error: {r}")
            except Exception as e:
                print(f"    ✗ Excepción: {e}")


if __name__ == "__main__":
    main()
