#!/usr/bin/env python3
"""Migra patrones evol_001..005 de reglas/aprendizaje.yaml a SupplierRule en BD.

Los patrones base_001..007 son genéricos (estrategias de resolución de errores)
y NO se migran a SupplierRule — pertenecen al motor de aprendizaje.

Los patrones evol_001..005 representan comportamientos específicos de tipo de
documento que sí encajan como SupplierRule globales (empresa_id=None).

Uso:
    python scripts/migrar_aprendizaje_yaml_a_supplier_rules.py [--dry-run]

Idempotente: no duplica reglas ya existentes.
"""
import argparse
import os
import sys
from pathlib import Path

# Añadir raíz del proyecto al path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


def _mapear_evol_a_supplier_rule(patron: dict) -> dict | None:
    """Convierte un patrón evol a campos de SupplierRule.

    Retorna None si el patrón no es migrable.
    """
    pat_id = patron.get("id", "")
    estrategia = patron.get("estrategia", "")
    descripcion = patron.get("descripcion", "")
    tipos_doc = patron.get("tipo_doc", [])

    # Mapeo evol_001: intracomunitario → IVA0
    if pat_id == "evol_001":
        return {
            "emisor_nombre_patron": "intracomunitario",
            "codimpuesto": "IVA0",
            "regimen": "intracomunitario",
            "nivel": "global_nombre",
        }

    # Mapeo evol_002: IVA incluido en líneas → no hay campo SupplierRule directo
    if pat_id == "evol_002":
        return {
            "emisor_nombre_patron": "iva_incluido_lineas",
            "nivel": "global_nombre",
        }

    # Mapeo evol_003: CIF vacío buscar por nombre → ya manejado por buscar_regla_aplicable nivel 3
    if pat_id == "evol_003":
        return {
            "emisor_nombre_patron": "cif_vacio_buscar_nombre",
            "nivel": "global_nombre",
        }

    # Mapeo evol_004: precio_unitario=0 → derivar de base
    if pat_id == "evol_004":
        return {
            "emisor_nombre_patron": "precio_unitario_cero",
            "nivel": "global_nombre",
        }

    # Mapeo evol_005: subcuenta genérica 6000000000
    if pat_id == "evol_005":
        return {
            "emisor_nombre_patron": "subcuenta_generica_6000",
            "subcuenta_gasto": "6000000000",
            "nivel": "global_nombre",
        }

    return None


def migrar(dry_run: bool = False) -> None:
    ruta_yaml = ROOT / "reglas" / "aprendizaje.yaml"
    if not ruta_yaml.exists():
        print(f"[ERROR] No se encontró {ruta_yaml}")
        sys.exit(1)

    import yaml
    with open(ruta_yaml, encoding="utf-8") as f:
        datos = yaml.safe_load(f)

    patrones = datos.get("patrones", [])
    evol_patrones = [p for p in patrones if p.get("id", "").startswith("evol_")]
    print(f"Patrones evol_* encontrados: {len(evol_patrones)}")

    # Configurar BD
    db_path = os.environ.get("SFCE_DB_PATH", str(ROOT / "sfce.db"))
    db_url = f"sqlite:///{db_path}"

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sfce.db.modelos import SupplierRule
    import sfce.db.modelos_auth  # noqa — registra gestorias en metadata
    from sfce.db.base import Base

    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    insertados = 0
    omitidos = 0

    with Session() as sesion:
        for patron in evol_patrones:
            campos = _mapear_evol_a_supplier_rule(patron)
            if not campos:
                print(f"  [SKIP] {patron['id']}: no es migrable")
                omitidos += 1
                continue

            patron_nombre = campos.get("emisor_nombre_patron")

            # Verificar si ya existe (idempotente)
            existente = sesion.query(SupplierRule).filter(
                SupplierRule.empresa_id.is_(None),
                SupplierRule.emisor_cif.is_(None),
                SupplierRule.emisor_nombre_patron == patron_nombre,
            ).first()

            if existente:
                print(f"  [OMITIDO] {patron['id']} - ya existe en BD (id={existente.id})")
                omitidos += 1
                continue

            if dry_run:
                print(f"  [DRY-RUN] {patron['id']} -> {campos}")
                insertados += 1
                continue

            regla = SupplierRule(
                empresa_id=None,
                emisor_cif=None,
                **campos,
            )
            sesion.add(regla)
            print(f"  [INSERTAR] {patron['id']} -> patron='{patron_nombre}', nivel={campos.get('nivel')}")
            insertados += 1

        if not dry_run:
            sesion.commit()

    print(f"\nResumen: {insertados} insertadas, {omitidos} omitidas")
    if dry_run:
        print("(dry-run: no se modificó la BD)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Solo muestra qué haría sin modificar la BD")
    args = parser.parse_args()
    migrar(dry_run=args.dry_run)
