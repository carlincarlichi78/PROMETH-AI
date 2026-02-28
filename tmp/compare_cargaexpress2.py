"""Comparativa Cargaexpress: busca en ambas empresas con mas detalle."""
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
    # 1. Listar endpoints disponibles
    print("=== Endpoints API disponibles ===")
    resp = requests.get(f"{API_BASE}/", headers=HEADERS, timeout=30)
    endpoints = resp.json()
    # Buscar endpoints de lineas
    for ep in sorted(endpoints):
        if "linea" in ep.lower() or "line" in ep.lower():
            print(f"  {ep}")

    # 2. Ver todos los proveedores en ambas empresas
    print("\n=== Proveedores ===")
    proveedores = api_get_all("proveedores")
    for idempresa in [1, 3]:
        provs = [p for p in proveedores if int(p.get("idempresa", 0)) == idempresa]
        print(f"\nEmpresa {idempresa}: {len(provs)} proveedores")
        for p in provs:
            nombre = p.get("nombre", "")
            if "carga" in nombre.lower():
                print(f"  ** CARGAEXPRESS: codproveedor={p.get('codproveedor')} nombre={nombre} cifnif={p.get('cifnif')} codpais={p.get('codpais')}")

    # 3. Facturas proveedor — buscar todas con "carga" en nombre
    print("\n=== Facturas proveedor con 'carga' en nombre ===")
    facturas = api_get_all("facturaproveedores")

    for idempresa, nombre_emp in [(1, "PASTORINO"), (3, "EMPRESA PRUEBA")]:
        facturas_emp = [f for f in facturas if int(f.get("idempresa", 0)) == idempresa]
        print(f"\nEmpresa {idempresa} ({nombre_emp}): {len(facturas_emp)} facturas proveedor total")

        # Mostrar TODOS los nombres de proveedor unicos
        nombres_unicos = sorted(set(f.get("nombre", "") for f in facturas_emp))
        print(f"  Proveedores con facturas: {nombres_unicos}")

        # Buscar Cargaexpress con variantes
        cargaexpress = [
            f for f in facturas_emp
            if any(kw in f.get("nombre", "").lower() for kw in ["carga", "express", "2390"])
            or any(kw in str(f.get("numero2", "")).lower() for kw in ["2390"])
        ]
        if cargaexpress:
            print(f"  Facturas tipo Cargaexpress encontradas: {len(cargaexpress)}")
            for f in cargaexpress:
                print(f"    numero2={f.get('numero2')} nombre={f.get('nombre')} neto={f.get('neto')} total={f.get('total')}")

    # 4. Buscar en Pastorino por numero de factura (2390101398, etc)
    print("\n=== Busqueda directa por numero2 conteniendo '2390' ===")
    for f in facturas:
        n2 = str(f.get("numero2", ""))
        if "2390" in n2:
            print(f"  empresa={f.get('idempresa')} numero2={n2} nombre={f.get('nombre')} neto={f.get('neto')} total={f.get('total')} idasiento={f.get('idasiento')}")


if __name__ == "__main__":
    main()
