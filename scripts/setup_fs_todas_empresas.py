"""Crea en FacturaScripts todas las empresas del SFCE que aun no tienen idempresa_fs.
Luego actualiza sfce.db con idempresa_fs y codejercicio_fs.

Uso:
    export $(grep -v '^#' .env | xargs)
    python scripts/setup_fs_todas_empresas.py
"""
import sys
import io
import os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sfce.db.base import crear_motor
from sfce.core.fs_setup import FsSetup
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

_CONFIG_BD = {"tipo_bd": "sqlite", "ruta_bd": "sfce.db"}

# Ejercicio para empresas nuevas (las historicas ya tienen 2024)
ANIO_DEFAULT = 2025

# PGC por forma juridica
def _pgc(forma):
    if forma in ("sl", "sa"):
        return "pymes"
    return "general"

def main():
    motor = crear_motor(_CONFIG_BD)
    Session = sessionmaker(bind=motor)
    fs = FsSetup()

    print(f"FS URL: {fs._base}")
    print()

    with Session() as s:
        empresas = s.execute(text(
            "SELECT id, nombre, cif, forma_juridica, idempresa_fs FROM empresas ORDER BY id"
        )).fetchall()

        for emp in empresas:
            sfce_id, nombre, cif, forma, idempresa_fs = emp

            if idempresa_fs:
                print(f"  [OK ya en FS]  {nombre} (idempresa={idempresa_fs})")
                continue

            # CIF: usar "" si es placeholder PEND-
            cif_fs = cif if not cif.startswith("PEND-") else ""
            pgc = _pgc(forma)

            print(f"  Creando: {nombre} | CIF={cif_fs or '(vacio)'} | PGC={pgc} | anio={ANIO_DEFAULT}")
            try:
                r = fs.setup_completo(
                    nombre=nombre,
                    cif=cif_fs,
                    anio=ANIO_DEFAULT,
                    tipo_pgc=pgc,
                )
                s.execute(text(
                    "UPDATE empresas SET idempresa_fs=:idfs, codejercicio_fs=:cej WHERE id=:id"
                ), {"idfs": r.idempresa_fs, "cej": r.codejercicio, "id": sfce_id})
                s.commit()
                pgc_str = "PGC OK" if r.pgc_importado else "PGC FALLO"
                print(f"    -> idempresa={r.idempresa_fs}, codejercicio={r.codejercicio}, {pgc_str}")
            except Exception as e:
                print(f"    ERROR: {e}")

        print()
        print("=== ESTADO FINAL ===")
        rows = s.execute(text(
            "SELECT e.id, e.nombre, e.idempresa_fs, e.codejercicio_fs, g.nombre "
            "FROM empresas e LEFT JOIN gestorias g ON g.id=e.gestoria_id ORDER BY e.id"
        )).fetchall()
        for r in rows:
            gname = r[4] or "Javier (sin gestoria)"
            fs_info = f"FS={r[2]}/{r[3]}" if r[2] else "FS=pendiente"
            print(f"  [{r[0]:2d}] {r[1]:<40} {fs_info:<20} {gname}")

if __name__ == "__main__":
    main()
