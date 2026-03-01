"""Comparativa de asientos Cargaexpress entre Pastorino (emp 1) y EMPRESA PRUEBA (emp 3)."""
import requests
import json

API_BASE = "https://contabilidad.lemonfresh-tuc.com/api/3"
TOKEN = "iOXmrA1Bbn8RDWXLv91L"
HEADERS = {"Token": TOKEN}


def api_get_all(endpoint, limit=200):
    """GET con paginacion automatica."""
    todos = []
    offset = 0
    while True:
        resp = requests.get(
            f"{API_BASE}/{endpoint}",
            headers=HEADERS,
            params={"limit": limit, "offset": offset},
            timeout=30
        )
        resp.raise_for_status()
        lote = resp.json()
        if not lote:
            break
        todos.extend(lote)
        if len(lote) < limit:
            break
        offset += limit
    return todos


def main():
    # 1. Obtener todas las facturas de proveedor
    print("=== Obteniendo facturas de proveedor... ===")
    facturas = api_get_all("facturaproveedores")
    print(f"Total facturas proveedor en FS: {len(facturas)}")

    # 2. Filtrar por empresa y por Cargaexpress
    for idempresa, nombre_emp in [(1, "PASTORINO"), (3, "EMPRESA PRUEBA")]:
        facturas_emp = [f for f in facturas if int(f.get("idempresa", 0)) == idempresa]
        cargaexpress = [
            f for f in facturas_emp
            if "carga" in f.get("nombre", "").lower() or "cargaexpress" in f.get("nombre", "").lower()
        ]
        print(f"\n{'='*80}")
        print(f"EMPRESA {idempresa} ({nombre_emp}): {len(facturas_emp)} facturas proveedor, {len(cargaexpress)} de Cargaexpress")
        print(f"{'='*80}")

        if not cargaexpress:
            print("  (sin facturas Cargaexpress)")
            continue

        for f in sorted(cargaexpress, key=lambda x: x.get("numero2", "")):
            print(f"\n  Factura: {f.get('numero2', '?')} | ID: {f.get('idfactura')} | Fecha: {f.get('fecha')}")
            print(f"  Proveedor: {f.get('nombre')} | CIF: {f.get('cifnif')}")
            print(f"  Neto: {f.get('neto')} | IVA: {f.get('totaliva')} | Total: {f.get('total')} | Divisa: {f.get('coddivisa')}")
            print(f"  idasiento: {f.get('idasiento')}")

    # 3. Obtener TODAS las partidas
    print("\n\n=== Obteniendo todas las partidas... ===")
    partidas = api_get_all("partidas")
    print(f"Total partidas en FS: {len(partidas)}")

    # 4. Obtener todos los asientos para mapear idasiento -> idempresa
    print("=== Obteniendo todos los asientos... ===")
    asientos = api_get_all("asientos")
    print(f"Total asientos en FS: {len(asientos)}")
    asiento_empresa = {int(a["idasiento"]): int(a.get("idempresa", 0)) for a in asientos}

    # 5. Para cada empresa, mostrar partidas de facturas Cargaexpress
    for idempresa, nombre_emp in [(1, "PASTORINO"), (3, "EMPRESA PRUEBA")]:
        facturas_emp = [f for f in facturas if int(f.get("idempresa", 0)) == idempresa]
        cargaexpress = [
            f for f in facturas_emp
            if "carga" in f.get("nombre", "").lower() or "cargaexpress" in f.get("nombre", "").lower()
        ]

        print(f"\n{'='*80}")
        print(f"PARTIDAS CARGAEXPRESS - EMPRESA {idempresa} ({nombre_emp})")
        print(f"{'='*80}")

        total_600 = 0.0
        total_472 = 0.0
        total_410 = 0.0  # 410* = proveedores
        total_400 = 0.0  # 400* = proveedores

        for f in sorted(cargaexpress, key=lambda x: x.get("numero2", "")):
            idasiento = f.get("idasiento")
            if not idasiento:
                print(f"\n  Factura {f.get('numero2')}: SIN ASIENTO")
                continue

            idasiento = int(idasiento)
            # Filtrar partidas de este asiento
            partidas_asiento = [p for p in partidas if int(p.get("idasiento", 0)) == idasiento]

            print(f"\n  Factura: {f.get('numero2')} | idasiento: {idasiento}")
            print(f"  Neto: {f.get('neto')} | IVA: {f.get('totaliva')} | Total: {f.get('total')}")
            print(f"  {'Subcuenta':<15} {'Concepto':<40} {'Debe':>12} {'Haber':>12}")
            print(f"  {'-'*79}")

            for p in sorted(partidas_asiento, key=lambda x: x.get("codsubcuenta", "")):
                sub = p.get("codsubcuenta", "")
                concepto = p.get("concepto", "")[:40]
                debe = float(p.get("debe", 0))
                haber = float(p.get("haber", 0))
                print(f"  {sub:<15} {concepto:<40} {debe:>12.2f} {haber:>12.2f}")

                # Acumular por grupo de cuenta
                if sub.startswith("600"):
                    total_600 += debe - haber
                elif sub.startswith("472"):
                    total_472 += debe - haber
                elif sub.startswith("410") or sub.startswith("400"):
                    total_400 += debe - haber

            # Verificar cuadre
            sum_debe = sum(float(p.get("debe", 0)) for p in partidas_asiento)
            sum_haber = sum(float(p.get("haber", 0)) for p in partidas_asiento)
            print(f"  {'TOTALES':<15} {'':<40} {sum_debe:>12.2f} {sum_haber:>12.2f}")
            diff = sum_debe - sum_haber
            if abs(diff) > 0.01:
                print(f"  *** DESCUADRE: {diff:.2f} ***")

        print(f"\n  --- RESUMEN CARGAEXPRESS empresa {idempresa} ---")
        print(f"  Saldo neto 600* (gastos):        {total_600:>12.2f} EUR")
        print(f"  Saldo neto 472* (IVA soportado): {total_472:>12.2f} EUR")
        print(f"  Saldo neto 400*/410* (proveedor): {total_400:>12.2f} EUR")

    # 6. Comparar lineas de factura (detalle IVA)
    print(f"\n\n{'='*80}")
    print("DETALLE LINEAS DE FACTURA (IVA por linea)")
    print(f"{'='*80}")

    print("\n=== Obteniendo lineas de factura proveedor... ===")
    lineas = api_get_all("lineasfacturasprov")
    print(f"Total lineas factura proveedor: {len(lineas)}")

    for idempresa, nombre_emp in [(1, "PASTORINO"), (3, "EMPRESA PRUEBA")]:
        facturas_emp = [f for f in facturas if int(f.get("idempresa", 0)) == idempresa]
        cargaexpress = [
            f for f in facturas_emp
            if "carga" in f.get("nombre", "").lower() or "cargaexpress" in f.get("nombre", "").lower()
        ]

        print(f"\n--- LINEAS CARGAEXPRESS empresa {idempresa} ({nombre_emp}) ---")

        for f in sorted(cargaexpress, key=lambda x: x.get("numero2", "")):
            idfactura = int(f.get("idfactura", 0))
            lineas_fact = [l for l in lineas if int(l.get("idfactura", 0)) == idfactura]

            print(f"\n  Factura: {f.get('numero2')} (idfactura={idfactura})")
            print(f"  {'Descripcion':<50} {'PVP':>10} {'IVA%':>6} {'CodImp':>8} {'Neto':>10} {'TotalIVA':>10}")
            print(f"  {'-'*94}")

            for l in lineas_fact:
                desc = (l.get("descripcion") or "")[:50]
                pvp = float(l.get("pvptotal", 0))
                iva = l.get("iva", "")
                codimp = l.get("codimpuesto", "")
                neto = float(l.get("pvptotal", 0))
                totaliva_linea = float(l.get("totaliva", 0) if l.get("totaliva") else 0)
                print(f"  {desc:<50} {pvp:>10.2f} {iva:>6} {codimp:>8} {neto:>10.2f} {totaliva_linea:>10.2f}")


if __name__ == "__main__":
    main()
