"""Migra config.yaml de todos los clientes a BD directorio."""

import sys
from pathlib import Path

RAIZ = Path(__file__).parent.parent
sys.path.insert(0, str(RAIZ))

import yaml
from sfce.db.base import crear_motor, crear_sesion, inicializar_bd
from sfce.db.repositorio import Repositorio
from sfce.db.modelos import Empresa


def migrar_cliente(ruta_cliente: Path, repo: Repositorio) -> dict:
    """Migra un config.yaml a BD directorio + overlays.

    Args:
        ruta_cliente: ruta a la carpeta del cliente (con config.yaml)
        repo: repositorio de BD

    Returns:
        dict con stats de migracion
    """
    config_path = ruta_cliente / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    emp_data = data.get("empresa", {})
    stats = {
        "proveedores_directorio": 0, "clientes_directorio": 0,
        "overlays_creados": 0, "ya_existentes": 0,
    }

    # Obtener o crear empresa
    empresa = repo.buscar_empresa_por_cif(emp_data["cif"])
    if not empresa:
        empresa = repo.crear(Empresa(
            cif=emp_data["cif"], nombre=emp_data["nombre"],
            forma_juridica=emp_data.get("tipo", "sl"),
            territorio="peninsula",
            idempresa_fs=emp_data.get("idempresa"),
            codejercicio_fs=emp_data.get("codejercicio"),
        ))

    # Migrar proveedores
    for nombre_corto, prov in data.get("proveedores", {}).items():
        cif = prov.get("cif", "").strip() or None
        aliases_prov = prov.get("aliases", [])
        if nombre_corto not in aliases_prov:
            aliases_prov = [nombre_corto] + aliases_prov

        dir_ent, creado = repo.obtener_o_crear_directorio(
            cif=cif, nombre=prov.get("nombre_fs", nombre_corto),
            pais=prov.get("pais", "ESP"),
            aliases=aliases_prov,
        )
        if creado:
            stats["proveedores_directorio"] += 1
        else:
            stats["ya_existentes"] += 1

        # Crear overlay si no existe (buscar siempre, incluso con CIF vacio)
        existente = repo.buscar_overlay_por_cif(
            empresa.id, dir_ent.cif or "", "proveedor"
        )
        if not existente:
            repo.crear_overlay(
                empresa_id=empresa.id, directorio_id=dir_ent.id,
                tipo="proveedor",
                subcuenta_gasto=prov.get("subcuenta", "6000000000"),
                codimpuesto=prov.get("codimpuesto", "IVA21"),
                regimen=prov.get("regimen", "general"),
                retencion_pct=prov.get("retencion"),
                pais=prov.get("pais", "ESP"),
                aliases=[nombre_corto],
            )
            stats["overlays_creados"] += 1

    # Migrar clientes
    for nombre_corto, cli in data.get("clientes", {}).items():
        cif = cli.get("cif", "").strip() or None
        aliases_cli = cli.get("aliases", [])
        if nombre_corto not in aliases_cli:
            aliases_cli = [nombre_corto] + aliases_cli

        dir_ent, creado = repo.obtener_o_crear_directorio(
            cif=cif, nombre=cli.get("nombre_fs", nombre_corto),
            pais=cli.get("pais", "ESP"),
            aliases=aliases_cli,
        )
        if creado:
            stats["clientes_directorio"] += 1
        else:
            stats["ya_existentes"] += 1

        existente = repo.buscar_overlay_por_cif(
            empresa.id, dir_ent.cif or "", "cliente"
        )
        if not existente:
            repo.crear_overlay(
                empresa_id=empresa.id, directorio_id=dir_ent.id,
                tipo="cliente",
                codimpuesto=cli.get("codimpuesto", "IVA21"),
                regimen=cli.get("regimen", "general"),
                pais=cli.get("pais", "ESP"),
                aliases=[nombre_corto],
            )
            stats["overlays_creados"] += 1

    return stats


def migrar_todos():
    """Migra todos los clientes con config.yaml."""
    engine = crear_motor({"tipo_bd": "sqlite", "ruta_bd": str(RAIZ / "sfce.db")})
    inicializar_bd(engine)
    Session = crear_sesion(engine)
    repo = Repositorio(Session)

    clientes_dir = RAIZ / "clientes"
    total = {
        "proveedores_directorio": 0, "clientes_directorio": 0,
        "overlays_creados": 0, "ya_existentes": 0,
    }

    for config_path in sorted(clientes_dir.glob("*/config.yaml")):
        ruta_cliente = config_path.parent
        print(f"Migrando: {ruta_cliente.name}")
        stats = migrar_cliente(ruta_cliente, repo)
        for k, v in stats.items():
            total[k] += v
        print(f"  {stats}")

    print(f"\nTotal: {total}")


if __name__ == "__main__":
    migrar_todos()
