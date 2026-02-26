"""Fix asientos Cargaexpress en EMPRESA PRUEBA (empresa 3).

Las lineas "IVA ADUANA" se registraron correctamente con IVA0,
pero su importe quedo en cuenta 6000000000 (gastos) cuando deberia
estar en 4709000000 (HP deudora IVA importaciones).

El IVA21 y la cuenta del proveedor (400*) ya son correctos.

Correccion por asiento:
- REDUCIR 6000000000 DEBE por importe IVA ADUANA
- CREAR partida 4709000000 DEBE por importe IVA ADUANA
- El asiento sigue cuadrando (mismo total DEBE, solo reclasificacion)
"""

import sys
sys.path.insert(0, "C:/Users/carli/PROYECTOS/CONTABILIDAD")

from scripts.core.fs_api import api_get, api_put, api_post

ID_EMPRESA = 3


def obtener_facturas_cargaexpress():
    """Obtiene facturas de proveedor de Cargaexpress para empresa 3."""
    todas = api_get("facturaproveedores")
    facturas = [
        f for f in todas
        if int(f.get("idempresa", 0)) == ID_EMPRESA
        and "cargaexpress" in f.get("nombre", "").lower()
    ]
    print(f"Facturas Cargaexpress encontradas: {len(facturas)}")
    for f in facturas:
        print(f"  - idfactura={f['idfactura']} codigo={f.get('codigo','')} "
              f"total={f.get('total','')} fecha={f.get('fecha','')}")
    return facturas


def identificar_lineas_iva_aduana(lineas):
    """Identifica lineas con 'IVA ADUANA' en la descripcion."""
    lineas_aduana = []
    for l in lineas:
        desc = l.get("descripcion", "") or l.get("referencia", "") or ""
        if "iva aduana" in desc.lower():
            lineas_aduana.append(l)
    return lineas_aduana


def corregir_asiento(factura, lineas_aduana, partidas):
    """Reclasifica importe IVA ADUANA de cuenta 600 a cuenta 4709."""
    importe_aduana = sum(
        float(l.get("pvptotal", 0)) for l in lineas_aduana
    )
    idasiento = int(factura.get("idasiento", 0))
    codigo_factura = factura.get("codigo", "?")

    print(f"\n{'='*60}")
    print(f"Factura: {codigo_factura} (idfactura={factura['idfactura']}, "
          f"idasiento={idasiento})")
    print(f"  Importe IVA ADUANA a reclasificar: {importe_aduana:.2f} EUR")

    if importe_aduana == 0:
        print("  SKIP: importe IVA ADUANA = 0")
        return False

    # Buscar partida 6000000000 con DEBE > 0
    p_600 = None
    for p in partidas:
        sub = p.get("codsubcuenta", "")
        if sub == "6000000000" and float(p.get("debe", 0)) > 0:
            p_600 = p
            break

    if not p_600:
        print(f"  ERROR: no se encontro partida 6000000000 con DEBE > 0")
        print(f"  Partidas existentes:")
        for p in partidas:
            print(f"    {p.get('codsubcuenta','')} "
                  f"D={p.get('debe',0)} H={p.get('haber',0)} "
                  f"id={p.get('idpartida','')}")
        return False

    # Verificar que hay suficiente en 600 para restar
    debe_600_actual = float(p_600["debe"])
    debe_600_nuevo = round(debe_600_actual - importe_aduana, 2)

    if debe_600_nuevo < 0:
        print(f"  ERROR: 6000000000 DEBE actual ({debe_600_actual:.2f}) < "
              f"importe aduana ({importe_aduana:.2f})")
        return False

    # Verificar que no existe ya una partida 4709 (evitar duplicados)
    p_4709_existente = None
    for p in partidas:
        if p.get("codsubcuenta", "") == "4709000000":
            p_4709_existente = p
            break

    if p_4709_existente:
        print(f"  SKIP: ya existe partida 4709000000 en asiento {idasiento} "
              f"(D={p_4709_existente.get('debe',0)}, "
              f"id={p_4709_existente.get('idpartida','')})")
        print(f"  Parece que este asiento ya fue corregido.")
        return False

    print(f"\n  Correcciones:")
    print(f"  6000000000 DEBE: {debe_600_actual:.2f} -> {debe_600_nuevo:.2f} "
          f"(reducir {importe_aduana:.2f})")
    print(f"  4709000000 DEBE: NUEVA partida por {importe_aduana:.2f}")

    # 1. PUT 6000000000 (reducir DEBE)
    id_600 = p_600["idpartida"]
    print(f"\n  PUT partidas/{id_600} (6000000000 DEBE={debe_600_nuevo})")
    resp = api_put(f"partidas/{id_600}", {"debe": str(debe_600_nuevo)})
    print(f"    -> OK, debe={resp.get('debe', '?')}")

    # 2. POST nueva partida 4709000000
    concepto = factura.get("observaciones", "") or f"IVA ADUANA - {codigo_factura}"
    nueva_partida = {
        "idasiento": str(idasiento),
        "codsubcuenta": "4709000000",
        "debe": str(importe_aduana),
        "haber": "0",
        "concepto": concepto,
    }
    print(f"  POST partidas (4709000000 DEBE={importe_aduana})")
    resp = api_post("partidas", nueva_partida)
    print(f"    -> OK, idpartida={resp.get('idpartida', '?')}")

    # Verificar cuadre (re-cargar partidas del asiento)
    todas_partidas_post = api_get("partidas")
    partidas_post = [p for p in todas_partidas_post
                     if int(p.get("idasiento", 0)) == idasiento]
    total_debe = sum(float(p.get("debe", 0)) for p in partidas_post)
    total_haber = sum(float(p.get("haber", 0)) for p in partidas_post)
    diff = round(total_debe - total_haber, 2)

    print(f"\n  Verificacion cuadre asiento {idasiento}:")
    for p in partidas_post:
        sub = p.get("codsubcuenta", "")
        d = float(p.get("debe", 0))
        h = float(p.get("haber", 0))
        if d > 0 or h > 0:
            print(f"    {sub} D={d:.2f} H={h:.2f}")
    print(f"    Total DEBE:  {total_debe:.2f}")
    print(f"    Total HABER: {total_haber:.2f}")
    print(f"    Diferencia:  {diff:.2f}")
    if abs(diff) < 0.01:
        print(f"    CUADRA OK")
    else:
        print(f"    ERROR: DESCUADRE de {diff:.2f}")

    return True


def main():
    print("=" * 60)
    print("Fix asientos Cargaexpress - EMPRESA PRUEBA (empresa 3)")
    print("Reclasificacion IVA ADUANA: 6000000000 -> 4709000000")
    print("=" * 60)

    # 1. Obtener facturas Cargaexpress
    facturas = obtener_facturas_cargaexpress()
    if not facturas:
        print("No se encontraron facturas de Cargaexpress.")
        return

    # Pre-cargar lineas y partidas (evitar N+1 queries)
    print("\nCargando lineas de factura...")
    todas_lineas = api_get("lineafacturaproveedores")
    print(f"  Total lineas en sistema: {len(todas_lineas)}")

    print("Cargando partidas...")
    todas_partidas = api_get("partidas")
    print(f"  Total partidas en sistema: {len(todas_partidas)}")

    # 2. Procesar cada factura
    corregidas = 0
    errores = 0
    skips = 0
    resumen = []

    for factura in facturas:
        idfactura = int(factura["idfactura"])
        idasiento = int(factura.get("idasiento", 0))

        # Filtrar lineas de esta factura
        lineas = [l for l in todas_lineas
                  if int(l.get("idfactura", 0)) == idfactura]

        # Identificar lineas IVA ADUANA
        lineas_aduana = identificar_lineas_iva_aduana(lineas)
        if not lineas_aduana:
            print(f"\nFactura {factura.get('codigo','?')} - sin lineas IVA ADUANA, skip")
            skips += 1
            continue

        importe_aduana = sum(float(l.get("pvptotal", 0)) for l in lineas_aduana)

        # Filtrar partidas de este asiento
        partidas = [p for p in todas_partidas
                    if int(p.get("idasiento", 0)) == idasiento]

        try:
            ok = corregir_asiento(factura, lineas_aduana, partidas)
            if ok:
                corregidas += 1
                resumen.append({
                    "codigo": factura.get("codigo", "?"),
                    "importe_aduana": importe_aduana,
                    "estado": "OK"
                })
            else:
                errores += 1
                resumen.append({
                    "codigo": factura.get("codigo", "?"),
                    "importe_aduana": importe_aduana,
                    "estado": "SKIP/ERROR"
                })
        except Exception as e:
            print(f"\n  EXCEPCION: {e}")
            errores += 1
            resumen.append({
                "codigo": factura.get("codigo", "?"),
                "estado": f"EXCEPCION: {e}"
            })

    # 3. Resumen final
    print(f"\n{'='*60}")
    print(f"RESUMEN FINAL")
    print(f"{'='*60}")
    print(f"Facturas Cargaexpress: {len(facturas)}")
    print(f"  Sin IVA ADUANA (skip): {skips}")
    print(f"  Corregidas: {corregidas}")
    print(f"  Errores/ya corregidas: {errores}")

    total_reclasificado = 0
    for r in resumen:
        print(f"  {r['codigo']}: {r['estado']}", end="")
        if r.get("importe_aduana"):
            print(f" (IVA ADUANA reclasificado={r['importe_aduana']:.2f} EUR)", end="")
            if r["estado"] == "OK":
                total_reclasificado += r["importe_aduana"]
        print()

    print(f"\nTotal reclasificado (600 -> 4709): {total_reclasificado:.2f} EUR")


if __name__ == "__main__":
    main()
