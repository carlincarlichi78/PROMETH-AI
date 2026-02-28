"""Comparativa asientos PRIMATRANSIT (emp 1) vs CARGAEXPRESS (emp 3).
Ambos son el agente aduanero con IVA mixto (IVA21 + IVA0 suplidos 'IVA ADUANA')."""
import requests

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
    # Mapeo proveedor por empresa
    PROVEEDORES = {
        1: {"nombre": "PRIMATRANSIT", "buscar": ["primatransit"]},
        3: {"nombre": "CARGAEXPRESS", "buscar": ["cargaexpress"]},
    }

    # 1. Obtener datos
    print("Obteniendo facturas proveedor...")
    facturas = api_get_all("facturaproveedores")
    print(f"  Total: {len(facturas)}")

    print("Obteniendo partidas...")
    partidas = api_get_all("partidas")
    print(f"  Total: {len(partidas)}")

    print("Obteniendo asientos...")
    asientos = api_get_all("asientos")
    print(f"  Total: {len(asientos)}")

    # Mapear idasiento -> idempresa
    asiento_empresa = {int(a["idasiento"]): int(a.get("idempresa", 0)) for a in asientos}

    # Intentar obtener lineas de factura
    print("Obteniendo lineas de factura proveedor...")
    try:
        lineas_fp = api_get_all("lineasfacturasproveedores")
        print(f"  Total lineas: {len(lineas_fp)}")
    except Exception:
        try:
            lineas_fp = api_get_all("lineasfacturaproveedores")
            print(f"  Total lineas: {len(lineas_fp)}")
        except Exception:
            print("  Endpoint lineas no encontrado, intentando alternativas...")
            # Listar endpoints disponibles que contengan "linea"
            resp = requests.get(f"{API_BASE}/", headers=HEADERS, timeout=30)
            eps = resp.json()
            linea_eps = [e for e in eps if "linea" in e.lower()]
            print(f"  Endpoints con 'linea': {linea_eps}")
            lineas_fp = []
            for ep in linea_eps:
                if "prov" in ep.lower():
                    try:
                        lineas_fp = api_get_all(ep)
                        print(f"  Endpoint '{ep}' OK: {len(lineas_fp)} lineas")
                        break
                    except Exception:
                        pass

    # 2. Para cada empresa, analizar
    for idempresa in [1, 3]:
        prov_info = PROVEEDORES[idempresa]
        facturas_emp = [f for f in facturas if int(f.get("idempresa", 0)) == idempresa]

        # Filtrar por nombre proveedor
        agente_facturas = []
        for f in facturas_emp:
            nombre = f.get("nombre", "").lower()
            if any(kw in nombre for kw in prov_info["buscar"]):
                agente_facturas.append(f)

        print(f"\n{'='*100}")
        print(f"EMPRESA {idempresa} — Proveedor: {prov_info['nombre']} — {len(agente_facturas)} facturas")
        print(f"{'='*100}")

        total_600_debe = 0.0
        total_600_haber = 0.0
        total_472_debe = 0.0
        total_472_haber = 0.0
        total_4709_debe = 0.0
        total_4709_haber = 0.0
        total_400_debe = 0.0
        total_400_haber = 0.0
        total_477_debe = 0.0
        total_477_haber = 0.0

        for f in sorted(agente_facturas, key=lambda x: x.get("fecha", "")):
            idfactura = int(f.get("idfactura", 0))
            idasiento = f.get("idasiento")
            n2 = f.get("numero2", "?")
            codigo = f.get("codigo", "?")

            print(f"\n  Factura: codigo={codigo} numero2={n2} | id={idfactura} | Fecha: {f.get('fecha')}")
            print(f"  Neto: {f.get('neto')} | IVA: {f.get('totaliva')} | Total: {f.get('total')} | Divisa: {f.get('coddivisa')}")
            print(f"  idasiento: {idasiento}")

            # --- Lineas de factura ---
            if lineas_fp:
                lineas_fact = [l for l in lineas_fp if int(l.get("idfactura", 0)) == idfactura]
                if lineas_fact:
                    print(f"\n  LINEAS DE FACTURA ({len(lineas_fact)} lineas):")
                    print(f"  {'Descripcion':<55} {'PVPTotal':>10} {'IVA%':>6} {'CodImp':>8}")
                    print(f"  {'-'*80}")
                    for l in lineas_fact:
                        desc = (l.get("descripcion") or "")[:55]
                        pvp = float(l.get("pvptotal", 0))
                        iva_pct = l.get("iva", "")
                        codimp = l.get("codimpuesto", "")
                        print(f"  {desc:<55} {pvp:>10.2f} {iva_pct:>6} {codimp:>8}")

            # --- Partidas del asiento ---
            if idasiento:
                idasiento = int(idasiento)
                partidas_asiento = [p for p in partidas if int(p.get("idasiento", 0)) == idasiento]

                print(f"\n  PARTIDAS ASIENTO {idasiento} ({len(partidas_asiento)} partidas):")
                print(f"  {'Subcuenta':<15} {'Concepto':<50} {'Debe':>12} {'Haber':>12}")
                print(f"  {'-'*89}")

                for p in sorted(partidas_asiento, key=lambda x: x.get("codsubcuenta", "")):
                    sub = p.get("codsubcuenta", "")
                    concepto = (p.get("concepto") or "")[:50]
                    debe = float(p.get("debe", 0))
                    haber = float(p.get("haber", 0))
                    print(f"  {sub:<15} {concepto:<50} {debe:>12.2f} {haber:>12.2f}")

                    # Acumular
                    if sub.startswith("600"):
                        total_600_debe += debe
                        total_600_haber += haber
                    elif sub.startswith("4720"):
                        total_472_debe += debe
                        total_472_haber += haber
                    elif sub.startswith("4709"):
                        total_4709_debe += debe
                        total_4709_haber += haber
                    elif sub.startswith("400") or sub.startswith("410"):
                        total_400_debe += debe
                        total_400_haber += haber
                    elif sub.startswith("477"):
                        total_477_debe += debe
                        total_477_haber += haber

                sum_d = sum(float(p.get("debe", 0)) for p in partidas_asiento)
                sum_h = sum(float(p.get("haber", 0)) for p in partidas_asiento)
                print(f"  {'TOTALES':<15} {'':<50} {sum_d:>12.2f} {sum_h:>12.2f}")
                diff = sum_d - sum_h
                if abs(diff) > 0.01:
                    print(f"  *** DESCUADRE: {diff:.2f} ***")

        print(f"\n{'='*100}")
        print(f"RESUMEN {prov_info['nombre']} (empresa {idempresa})")
        print(f"{'='*100}")
        print(f"  600* Gastos:          DEBE={total_600_debe:>12.2f}  HABER={total_600_haber:>12.2f}  SALDO={total_600_debe - total_600_haber:>12.2f}")
        print(f"  472* IVA soportado:   DEBE={total_472_debe:>12.2f}  HABER={total_472_haber:>12.2f}  SALDO={total_472_debe - total_472_haber:>12.2f}")
        print(f"  4709 IVA ext (PT):    DEBE={total_4709_debe:>12.2f}  HABER={total_4709_haber:>12.2f}  SALDO={total_4709_debe - total_4709_haber:>12.2f}")
        print(f"  400* Proveedores:     DEBE={total_400_debe:>12.2f}  HABER={total_400_haber:>12.2f}  SALDO={total_400_debe - total_400_haber:>12.2f}")
        print(f"  477* IVA repercutido: DEBE={total_477_debe:>12.2f}  HABER={total_477_haber:>12.2f}  SALDO={total_477_debe - total_477_haber:>12.2f}")

    # 3. Comparativa directa factura a factura
    print(f"\n\n{'='*100}")
    print("COMPARATIVA FACTURA A FACTURA (Pastorino Primatransit vs EMPRESA PRUEBA Cargaexpress)")
    print(f"{'='*100}")
    print("\nNOTA: Las facturas de Pastorino tienen numero2 (numero proveedor original).")
    print("Las de EMPRESA PRUEBA tienen numero2=None (generadas por SFCE testing).")
    print("\nLas 3 facturas originales de Primatransit (Pastorino):")
    facturas_past = [f for f in facturas
                     if int(f.get("idempresa", 0)) == 1
                     and "primatransit" in f.get("nombre", "").lower()
                     and f.get("codigo", "").startswith("FAC")]  # excluir NC
    for f in sorted(facturas_past, key=lambda x: x.get("fecha", "")):
        print(f"  {f.get('codigo')} n2={f.get('numero2')} fecha={f.get('fecha')} neto={f.get('neto')} iva={f.get('totaliva')} total={f.get('total')}")

    print("\nLas 3+1 facturas de Cargaexpress (EMPRESA PRUEBA):")
    facturas_ep = [f for f in facturas
                   if int(f.get("idempresa", 0)) == 3
                   and "cargaexpress" in f.get("nombre", "").lower()]
    for f in sorted(facturas_ep, key=lambda x: x.get("fecha", "")):
        print(f"  {f.get('codigo')} n2={f.get('numero2')} fecha={f.get('fecha')} neto={f.get('neto')} iva={f.get('totaliva')} total={f.get('total')}")


if __name__ == "__main__":
    main()
