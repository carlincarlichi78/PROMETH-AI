"""Replica facturas de un snapshot contable en una empresa de prueba en FS.

Lee snapshot_contabilidad.json de la empresa original y crea las mismas
facturas en la empresa de prueba (idempresa diferente, mismo FS).

Uso:
  python scripts/replay_snapshot.py --snapshot clientes/pastorino-costa-del-sol/2025/snapshot_contabilidad.json --idempresa 3

Requisitos:
  - La empresa destino debe existir en FS con ejercicio y PGC importado
  - Los proveedores/clientes son compartidos entre empresas en FS
  - Variable FS_API_TOKEN o token hardcoded en fs_api.py
"""
import argparse
import json
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).parent.parent
sys.path.insert(0, str(RAIZ))

from scripts.core.fs_api import api_get, api_post, api_put
from scripts.core.logger import crear_logger

logger = crear_logger("replay")


def cargar_snapshot(ruta: Path) -> dict:
    """Carga el snapshot JSON."""
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)


def construir_lineas_factura(lineas_snapshot: list, idfactura_original: int) -> list:
    """Filtra y construye lineas para una factura especifica."""
    lineas = []
    for lin in lineas_snapshot:
        if lin.get("idfactura") != idfactura_original:
            continue
        linea = {
            "cantidad": lin.get("cantidad", 1),
            "descripcion": lin.get("descripcion", ""),
            "pvpunitario": lin.get("pvpunitario", 0),
            "codimpuesto": lin.get("codimpuesto", "IVA21"),
            "irpf": lin.get("irpf", 0),
        }
        if lin.get("suplido"):
            linea["suplido"] = True
        lineas.append(linea)
    return lineas


def crear_factura_proveedor(factura: dict, lineas: list, idempresa: int) -> dict | None:
    """Crea una factura de proveedor en FS via API."""
    form_data = {
        "codproveedor": factura["codproveedor"],
        "codserie": factura.get("codserie", "A"),
        "fecha": factura["fecha"],
        "codejercicio": factura.get("codejercicio", "2025"),
        "codalmacen": factura.get("codalmacen", "ALG"),
        "codpago": factura.get("codpago", "TRANS"),
        "idempresa": idempresa,
        "numproveedor": factura.get("numproveedor", ""),
        "observaciones": factura.get("observaciones", ""),
        "lineas": json.dumps(lineas),
    }

    # Divisa
    if factura.get("coddivisa") and factura["coddivisa"] != "EUR":
        form_data["coddivisa"] = factura["coddivisa"]
        form_data["tasaconv"] = factura.get("tasaconv", 1)

    try:
        resultado = api_post("crearFacturaProveedor", form_data)
        # La respuesta viene en {"doc": {...}, "lines": [...]}
        doc = resultado.get("doc", resultado)
        return doc
    except Exception as e:
        logger.error(f"Error creando factura proveedor {factura.get('codigo')}: {e}")
        return None


def crear_factura_cliente(factura: dict, lineas: list, idempresa: int) -> dict | None:
    """Crea una factura de cliente en FS via API."""
    form_data = {
        "codcliente": factura["codcliente"],
        "codserie": factura.get("codserie", "A"),
        "fecha": factura["fecha"],
        "codejercicio": factura.get("codejercicio", "2025"),
        "codalmacen": factura.get("codalmacen", "ALG"),
        "codpago": factura.get("codpago", "TRANS"),
        "idempresa": idempresa,
        "numero2": factura.get("numero2", ""),
        "observaciones": factura.get("observaciones", ""),
        "lineas": json.dumps(lineas),
    }

    # Divisa
    if factura.get("coddivisa") and factura["coddivisa"] != "EUR":
        form_data["coddivisa"] = factura["coddivisa"]
        form_data["tasaconv"] = factura.get("tasaconv", 1)

    try:
        resultado = api_post("crearFacturaCliente", form_data)
        doc = resultado.get("doc", resultado)
        return doc
    except Exception as e:
        logger.error(f"Error creando factura cliente {factura.get('codigo')}: {e}")
        return None


def marcar_pagada(endpoint: str, idfactura: int) -> bool:
    """Marca una factura como pagada via PUT."""
    try:
        api_put(f"{endpoint}/{idfactura}", {"pagada": 1})
        return True
    except Exception as e:
        logger.error(f"Error marcando pagada {endpoint}/{idfactura}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Replica facturas de snapshot en empresa de prueba"
    )
    parser.add_argument("--snapshot", required=True,
                        help="Ruta al snapshot_contabilidad.json")
    parser.add_argument("--idempresa", required=True, type=int,
                        help="ID de empresa destino en FS")
    parser.add_argument("--dry-run", action="store_true",
                        help="Solo mostrar que se haria, sin crear nada")
    parser.add_argument("--solo-proveedores", action="store_true",
                        help="Solo crear facturas de proveedor")
    parser.add_argument("--solo-clientes", action="store_true",
                        help="Solo crear facturas de cliente")
    args = parser.parse_args()

    ruta_snapshot = Path(args.snapshot)
    if not ruta_snapshot.is_absolute():
        ruta_snapshot = RAIZ / ruta_snapshot

    if not ruta_snapshot.exists():
        logger.error(f"Snapshot no encontrado: {ruta_snapshot}")
        return 1

    snapshot = cargar_snapshot(ruta_snapshot)
    idempresa = args.idempresa

    # Verificar empresa destino existe
    try:
        empresas = api_get("empresas", params={"idempresa": idempresa})
        if not empresas:
            logger.error(f"Empresa {idempresa} no encontrada en FS")
            return 1
        logger.info(f"Empresa destino: {empresas[0].get('nombre')} (id={idempresa})")
    except Exception as e:
        logger.error(f"Error verificando empresa: {e}")
        return 1

    # Estadisticas
    stats = {
        "fp_creadas": 0, "fp_fallidas": 0, "fp_pagadas": 0,
        "fc_creadas": 0, "fc_fallidas": 0, "fc_pagadas": 0,
    }
    mapa_facturas = []  # original_id -> nuevo_id

    # === FACTURAS PROVEEDOR ===
    if not args.solo_clientes:
        facturas_prov = snapshot.get("facturas_proveedor", [])
        lineas_prov = snapshot.get("lineas_fact_proveedor", [])

        # Ordenar por fecha para respetar orden cronologico
        facturas_prov_sorted = sorted(facturas_prov, key=lambda f: f.get("fecha", ""))

        logger.info(f"\n{'='*60}")
        logger.info(f"FACTURAS PROVEEDOR: {len(facturas_prov_sorted)} a crear")
        logger.info(f"{'='*60}")

        for i, fac in enumerate(facturas_prov_sorted, 1):
            codigo_orig = fac.get("codigo", "?")
            idfactura_orig = fac["idfactura"]
            nombre = fac.get("nombre", "?")

            lineas = construir_lineas_factura(lineas_prov, idfactura_orig)
            if not lineas:
                logger.warning(f"  [{i}] {codigo_orig} ({nombre}) — SIN LINEAS, saltando")
                stats["fp_fallidas"] += 1
                continue

            total_orig = fac.get("total", 0)
            serie = fac.get("codserie", "A")
            divisa = fac.get("coddivisa", "EUR")

            if args.dry_run:
                logger.info(f"  [{i}] DRY-RUN: {codigo_orig} | {nombre} | "
                           f"{divisa} {total_orig} | serie={serie} | {len(lineas)} lineas")
                stats["fp_creadas"] += 1
                continue

            logger.info(f"  [{i}] Creando {codigo_orig} | {nombre} | "
                       f"{divisa} {total_orig} | serie={serie}...")

            resultado = crear_factura_proveedor(fac, lineas, idempresa)
            if resultado:
                nuevo_id = resultado.get("idfactura", "?")
                nuevo_codigo = resultado.get("codigo", "?")
                stats["fp_creadas"] += 1
                mapa_facturas.append({
                    "tipo": "proveedor",
                    "original_codigo": codigo_orig,
                    "original_id": idfactura_orig,
                    "nuevo_codigo": nuevo_codigo,
                    "nuevo_id": nuevo_id,
                })
                logger.info(f"       -> Creada: {nuevo_codigo} (id={nuevo_id})")

                # Marcar pagada si la original lo estaba
                if fac.get("pagada"):
                    if marcar_pagada("facturaproveedores", nuevo_id):
                        stats["fp_pagadas"] += 1
                        logger.info(f"       -> Pagada OK")

                # Pausa para no saturar API
                time.sleep(0.3)
            else:
                stats["fp_fallidas"] += 1

    # === FACTURAS CLIENTE ===
    if not args.solo_proveedores:
        facturas_cli = snapshot.get("facturas_cliente", [])
        lineas_cli = snapshot.get("lineas_fact_cliente", [])

        facturas_cli_sorted = sorted(facturas_cli, key=lambda f: f.get("fecha", ""))

        logger.info(f"\n{'='*60}")
        logger.info(f"FACTURAS CLIENTE: {len(facturas_cli_sorted)} a crear")
        logger.info(f"{'='*60}")

        for i, fac in enumerate(facturas_cli_sorted, 1):
            codigo_orig = fac.get("codigo", "?")
            idfactura_orig = fac["idfactura"]
            nombre = fac.get("nombre", "?")

            lineas = construir_lineas_factura(lineas_cli, idfactura_orig)
            if not lineas:
                logger.warning(f"  [{i}] {codigo_orig} ({nombre}) — SIN LINEAS, saltando")
                stats["fc_fallidas"] += 1
                continue

            total_orig = fac.get("total", 0)
            divisa = fac.get("coddivisa", "EUR")

            if args.dry_run:
                logger.info(f"  [{i}] DRY-RUN: {codigo_orig} | {nombre} | "
                           f"{divisa} {total_orig} | {len(lineas)} lineas")
                stats["fc_creadas"] += 1
                continue

            logger.info(f"  [{i}] Creando {codigo_orig} | {nombre} | "
                       f"{divisa} {total_orig}...")

            resultado = crear_factura_cliente(fac, lineas, idempresa)
            if resultado:
                nuevo_id = resultado.get("idfactura", "?")
                nuevo_codigo = resultado.get("codigo", "?")
                stats["fc_creadas"] += 1
                mapa_facturas.append({
                    "tipo": "cliente",
                    "original_codigo": codigo_orig,
                    "original_id": idfactura_orig,
                    "nuevo_codigo": nuevo_codigo,
                    "nuevo_id": nuevo_id,
                })
                logger.info(f"       -> Creada: {nuevo_codigo} (id={nuevo_id})")

                if fac.get("pagada"):
                    if marcar_pagada("facturaclientes", nuevo_id):
                        stats["fc_pagadas"] += 1
                        logger.info(f"       -> Pagada OK")

                time.sleep(0.3)
            else:
                stats["fc_fallidas"] += 1

    # === RESUMEN ===
    logger.info(f"\n{'='*60}")
    logger.info(f"RESUMEN REPLAY")
    logger.info(f"{'='*60}")
    logger.info(f"  Fact. proveedor: {stats['fp_creadas']} creadas, "
               f"{stats['fp_pagadas']} pagadas, {stats['fp_fallidas']} fallidas")
    logger.info(f"  Fact. cliente:   {stats['fc_creadas']} creadas, "
               f"{stats['fc_pagadas']} pagadas, {stats['fc_fallidas']} fallidas")

    # Guardar mapa de correspondencia
    if mapa_facturas and not args.dry_run:
        ruta_mapa = ruta_snapshot.parent / "replay_mapa.json"
        with open(ruta_mapa, "w", encoding="utf-8") as f:
            json.dump({
                "idempresa_origen": 1,
                "idempresa_destino": idempresa,
                "facturas": mapa_facturas,
                "stats": stats,
            }, f, indent=2, ensure_ascii=False)
        logger.info(f"\n  Mapa guardado en: {ruta_mapa}")

    total_fallidas = stats["fp_fallidas"] + stats["fc_fallidas"]
    return 1 if total_fallidas > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
