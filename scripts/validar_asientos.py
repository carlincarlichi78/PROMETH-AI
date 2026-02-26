"""
Validacion automatica de asientos contables en FacturaScripts.

Detecta errores conocidos que FS genera al crear asientos:
1. Importes en divisa original (USD) en vez de EUR
2. Notas de credito (serie R) con DEBE/HABER sin invertir
3. Intracomunitarias sin autoliquidacion (472/477 vacios)
4. IVA portugues en cuenta 600 (deberia ir a 4709)
5. Cuadre general de todos los asientos

Uso:
  export FS_API_TOKEN='tu_token'
  python scripts/validar_asientos.py --empresa 1 --ejercicio 2025
  python scripts/validar_asientos.py --empresa 1 --ejercicio 2025 --fix  # corrige automaticamente
"""

import requests
import os
import sys
import argparse
from collections import defaultdict


API_BASE = os.environ.get(
    "FS_API_URL",
    "https://contabilidad.lemonfresh-tuc.com/api/3",
)


def api_get(token, endpoint, params=None):
    """GET con paginacion automatica."""
    url = f"{API_BASE}/{endpoint}"
    todos = []
    params = dict(params or {})
    params.setdefault("limit", 200)
    params.setdefault("offset", 0)
    while True:
        resp = requests.get(url, headers={"Token": token}, params=params)
        resp.raise_for_status()
        lote = resp.json()
        if not lote:
            break
        todos.extend(lote)
        if len(lote) < params["limit"]:
            break
        params["offset"] += params["limit"]
    return todos


def api_put(token, endpoint, data):
    """PUT form-encoded."""
    url = f"{API_BASE}/{endpoint}"
    resp = requests.put(url, headers={"Token": token}, data=data)
    return resp.status_code == 200


# --- Validaciones ---

def validar_cuadre(partidas_por_asiento):
    """Verifica que DEBE == HABER en cada asiento."""
    errores = []
    for idasiento, partidas in partidas_por_asiento.items():
        total_d = sum(float(p["debe"]) for p in partidas)
        total_h = sum(float(p["haber"]) for p in partidas)
        if abs(total_d - total_h) >= 0.01:
            errores.append({
                "tipo": "DESCUADRE",
                "asiento": idasiento,
                "debe": total_d,
                "haber": total_h,
                "diff": total_d - total_h,
                "msg": f"A{idasiento}: DEBE={total_d:.2f} HABER={total_h:.2f} diff={total_d - total_h:.2f}",
            })
    return errores


def validar_divisas(facturas, partidas_por_asiento):
    """Detecta asientos con importes en divisa original en vez de EUR."""
    errores = []
    for f in facturas:
        divisa = f.get("coddivisa", "EUR")
        if divisa == "EUR":
            continue
        tc = float(f.get("tasaconv", 1) or 1)
        if tc <= 0 or tc == 1:
            continue

        idasiento = f.get("idasiento")
        if not idasiento:
            continue

        total_usd = float(f.get("total", 0))
        total_eur = round(total_usd / tc, 2)
        partidas = partidas_por_asiento.get(idasiento, [])

        for p in partidas:
            debe = float(p["debe"])
            haber = float(p["haber"])
            importe = debe if debe > 0 else haber
            if importe <= 0:
                continue

            # Si el importe coincide con USD y NO con EUR, es error
            if abs(importe - total_usd) < 0.01 and abs(importe - total_eur) > 1:
                errores.append({
                    "tipo": "DIVISA",
                    "asiento": idasiento,
                    "partida": p["idpartida"],
                    "subcuenta": p["codsubcuenta"],
                    "importe_actual": importe,
                    "importe_correcto": total_eur,
                    "divisa": divisa,
                    "tc": tc,
                    "campo": "debe" if debe > 0 else "haber",
                    "msg": f"A{idasiento} P{p['idpartida']}: {p['codsubcuenta']} tiene {importe:.2f} ({divisa}) deberia ser {total_eur:.2f} (EUR)",
                })
    return errores


def validar_notas_credito(facturas, partidas_por_asiento):
    """Detecta NC (serie R) con asiento sin invertir."""
    errores = []
    for f in facturas:
        if f.get("codserie") != "R":
            continue

        idasiento = f.get("idasiento")
        if not idasiento:
            continue

        partidas = partidas_por_asiento.get(idasiento, [])
        for p in partidas:
            subcta = p["codsubcuenta"]
            debe = float(p["debe"])
            haber = float(p["haber"])

            # En una NC de proveedor:
            # - 400 (proveedor) deberia estar en DEBE (reduce deuda)
            # - 600 (compras) deberia estar en HABER (reduce gasto)
            if subcta.startswith("400") and haber > 0 and debe == 0:
                errores.append({
                    "tipo": "NC_PROVEEDOR",
                    "asiento": idasiento,
                    "partida": p["idpartida"],
                    "subcuenta": subcta,
                    "debe_actual": debe,
                    "haber_actual": haber,
                    "msg": f"A{idasiento} P{p['idpartida']}: NC serie R pero {subcta} en HABER={haber:.2f} (deberia estar en DEBE)",
                })
            if subcta.startswith("600") and debe > 0 and haber == 0:
                errores.append({
                    "tipo": "NC_COMPRAS",
                    "asiento": idasiento,
                    "partida": p["idpartida"],
                    "subcuenta": subcta,
                    "debe_actual": debe,
                    "haber_actual": haber,
                    "msg": f"A{idasiento} P{p['idpartida']}: NC serie R pero {subcta} en DEBE={debe:.2f} (deberia estar en HABER)",
                })
    return errores


def validar_intracomunitarias(facturas_prov, proveedores, contactos, partidas_por_asiento):
    """Detecta intracomunitarias sin autoliquidacion 472/477."""
    # Mapear proveedores intracomunitarios
    prov_intra = set()
    for pr in proveedores:
        if pr.get("regimeniva") == "Intracomunitario":
            prov_intra.add(pr.get("codproveedor"))

    errores = []
    for f in facturas_prov:
        codprov = f.get("codproveedor")
        if codprov not in prov_intra:
            continue

        idasiento = f.get("idasiento")
        if not idasiento:
            continue

        neto = float(f.get("neto", 0))
        if neto <= 0:
            continue

        partidas = partidas_por_asiento.get(idasiento, [])
        tiene_472 = any(
            p["codsubcuenta"].startswith("472") and float(p["debe"]) > 0
            for p in partidas
        )
        tiene_477 = any(
            p["codsubcuenta"].startswith("477") and float(p["haber"]) > 0
            for p in partidas
        )

        if not tiene_472 or not tiene_477:
            errores.append({
                "tipo": "INTRACOMUNITARIA",
                "asiento": idasiento,
                "factura": f.get("codigo", ""),
                "proveedor": f.get("nombre", ""),
                "neto": neto,
                "tiene_472": tiene_472,
                "tiene_477": tiene_477,
                "msg": f"A{idasiento}: {f.get('nombre','')} intracomunitaria sin autoliquidacion (472={'SI' if tiene_472 else 'NO'}, 477={'SI' if tiene_477 else 'NO'})",
            })
    return errores


def validar_iva_portugues(facturas_prov, lineas_prov, partidas_por_asiento):
    """Detecta IVA portugues en cuenta 600 (deberia ir a 4709)."""
    # Buscar facturas con lineas "IVA ADUANA"
    errores = []
    for f in facturas_prov:
        idfactura = f["idfactura"]
        idasiento = f.get("idasiento")
        if not idasiento:
            continue

        lineas = [l for l in lineas_prov if l.get("idfactura") == idfactura]
        for linea in lineas:
            desc = (linea.get("descripcion") or "").upper()
            if "IVA ADUANA" not in desc and "IVA ADUANAS" not in desc:
                continue

            # Esta linea es IVA PT — verificar que NO este en 600
            importe_iva_pt = float(linea.get("pvptotal", 0))
            if importe_iva_pt <= 0:
                continue

            partidas = partidas_por_asiento.get(idasiento, [])
            # Verificar si hay partida 4709
            tiene_4709 = any(
                p["codsubcuenta"].startswith("4709") and float(p["debe"]) > 0
                for p in partidas
            )

            if not tiene_4709:
                errores.append({
                    "tipo": "IVA_PORTUGUES",
                    "asiento": idasiento,
                    "factura": f.get("codigo", ""),
                    "proveedor": f.get("nombre", ""),
                    "importe": importe_iva_pt,
                    "msg": f"A{idasiento}: {f.get('nombre','')} - IVA PT {importe_iva_pt:.2f} EUR en cuenta 600 (deberia ir a 4709)",
                })
    return errores


# --- Correcciones automaticas ---

def corregir_divisa(token, error):
    """Corrige una partida con importe en divisa original."""
    campo = error["campo"]
    correcto = error["importe_correcto"]
    return api_put(token, f"partidas/{error['partida']}", {campo: correcto})


def corregir_nc(token, error):
    """Invierte DEBE/HABER en partida de NC."""
    if error["tipo"] == "NC_PROVEEDOR":
        # 400 esta en HABER, mover a DEBE
        return api_put(token, f"partidas/{error['partida']}", {
            "debe": error["haber_actual"],
            "haber": 0,
        })
    elif error["tipo"] == "NC_COMPRAS":
        # 600 esta en DEBE, mover a HABER
        return api_put(token, f"partidas/{error['partida']}", {
            "debe": 0,
            "haber": error["debe_actual"],
        })
    return False


# --- Main ---

def main():
    parser = argparse.ArgumentParser(
        description="Validacion automatica de asientos en FacturaScripts"
    )
    parser.add_argument("--empresa", type=int, required=True)
    parser.add_argument("--ejercicio", type=str, required=True)
    parser.add_argument(
        "--fix", action="store_true",
        help="Corregir automaticamente errores de DIVISA y NC"
    )
    args = parser.parse_args()

    token = os.environ.get("FS_API_TOKEN")
    if not token:
        print("Error: FS_API_TOKEN no configurado")
        sys.exit(1)

    print(f"Validando asientos empresa {args.empresa}, ejercicio {args.ejercicio}...")
    print()

    # Obtener datos
    fact_cli = api_get(token, "facturaclientes")
    fact_prov = api_get(token, "facturaproveedores")
    lineas_prov = api_get(token, "lineafacturaproveedores")
    partidas = api_get(token, "partidas")
    proveedores = api_get(token, "proveedores")
    contactos = api_get(token, "contactos")

    # Filtrar por empresa
    fact_cli = [f for f in fact_cli if f.get("idempresa") == args.empresa]
    fact_prov = [f for f in fact_prov if f.get("idempresa") == args.empresa]

    # Agrupar partidas por asiento
    asientos_ids = set(
        f.get("idasiento") for f in fact_cli + fact_prov if f.get("idasiento")
    )
    partidas_por_asiento = defaultdict(list)
    for p in partidas:
        if p["idasiento"] in asientos_ids:
            partidas_por_asiento[p["idasiento"]].append(p)

    todas_facturas = fact_cli + fact_prov

    print(f"  Facturas: {len(fact_cli)} cliente + {len(fact_prov)} proveedor")
    print(f"  Asientos: {len(partidas_por_asiento)}")
    print(f"  Partidas: {sum(len(v) for v in partidas_por_asiento.values())}")
    print()

    # Ejecutar validaciones
    todos_errores = []

    print("=" * 60)
    print("  1. CUADRE (DEBE == HABER)")
    print("=" * 60)
    errores = validar_cuadre(partidas_por_asiento)
    if errores:
        for e in errores:
            print(f"  ERROR: {e['msg']}")
        todos_errores.extend(errores)
    else:
        print(f"  OK - {len(partidas_por_asiento)} asientos cuadran")
    print()

    print("=" * 60)
    print("  2. DIVISAS (importes en EUR, no en divisa original)")
    print("=" * 60)
    errores = validar_divisas(todas_facturas, partidas_por_asiento)
    if errores:
        for e in errores:
            print(f"  ERROR: {e['msg']}")
            if args.fix:
                ok = corregir_divisa(token, e)
                print(f"         -> {'CORREGIDO' if ok else 'FALLO'}")
        todos_errores.extend(errores)
    else:
        print("  OK - Todos los importes en EUR")
    print()

    print("=" * 60)
    print("  3. NOTAS DE CREDITO (serie R con DEBE/HABER invertidos)")
    print("=" * 60)
    errores = validar_notas_credito(fact_prov, partidas_por_asiento)
    if errores:
        for e in errores:
            print(f"  ERROR: {e['msg']}")
            if args.fix:
                ok = corregir_nc(token, e)
                print(f"         -> {'CORREGIDO' if ok else 'FALLO'}")
        todos_errores.extend(errores)
    else:
        print("  OK - Notas de credito correctas")
    print()

    print("=" * 60)
    print("  4. INTRACOMUNITARIAS (autoliquidacion 472/477)")
    print("=" * 60)
    errores = validar_intracomunitarias(fact_prov, proveedores, contactos, partidas_por_asiento)
    if errores:
        for e in errores:
            print(f"  AVISO: {e['msg']}")
        todos_errores.extend(errores)
    else:
        print("  OK - Autoliquidaciones presentes")
    print()

    print("=" * 60)
    print("  5. IVA PORTUGUES (cuenta 4709, no 600)")
    print("=" * 60)
    errores = validar_iva_portugues(fact_prov, lineas_prov, partidas_por_asiento)
    if errores:
        for e in errores:
            print(f"  AVISO: {e['msg']}")
        todos_errores.extend(errores)
    else:
        print("  OK - IVA portugues en cuenta 4709")
    print()

    # Resumen
    print("=" * 60)
    print("  RESUMEN")
    print("=" * 60)
    if todos_errores:
        por_tipo = defaultdict(int)
        for e in todos_errores:
            por_tipo[e["tipo"]] += 1
        for tipo, n in sorted(por_tipo.items()):
            etiqueta = {
                "DESCUADRE": "Descuadres",
                "DIVISA": "Importes en divisa original",
                "NC_PROVEEDOR": "NC proveedor sin invertir",
                "NC_COMPRAS": "NC compras sin invertir",
                "INTRACOMUNITARIA": "Intracom. sin autoliquidacion",
                "IVA_PORTUGUES": "IVA PT en cuenta incorrecta",
            }.get(tipo, tipo)
            print(f"  {etiqueta}: {n}")
        print(f"  TOTAL: {len(todos_errores)} problemas")
        if not args.fix:
            autocorregibles = sum(1 for e in todos_errores if e["tipo"] in ("DIVISA", "NC_PROVEEDOR", "NC_COMPRAS"))
            if autocorregibles:
                print(f"\n  Usa --fix para corregir automaticamente {autocorregibles} errores (DIVISA + NC)")
    else:
        print("  TODO OK - Sin errores detectados")
    print()


if __name__ == "__main__":
    main()
