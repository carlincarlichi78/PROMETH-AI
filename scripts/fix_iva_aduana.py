"""Correccion de lineas IVA en facturas Cargaexpress (EMPRESA PRUEBA, empresa 3).

Problema: varias lineas que deberian ser IVA0 (suplidos aduaneros) se registraron
con codimpuesto=IVA21, inflando el IVA soportado y los totales.

Referencia: facturas Primatransit en Pastorino (empresa 1) con los mismos datos
ya tienen el IVA correcto. Este script corrige EMPRESA PRUEBA para igualar.

Lineas afectadas (patron): DERECHOS ARANCEL, CAUCION, ADQUISICION CERTIFICADOS,
COSTES NAVIERA MAERSK — todas son suplidos/tasas aduaneras sin IVA.
"""

import sys
import os

sys.path.insert(0, "C:/Users/carli/PROYECTOS/CONTABILIDAD")
os.environ.setdefault("FS_API_TOKEN", "iOXmrA1Bbn8RDWXLv91L")

from scripts.core.fs_api import api_get, api_put, api_get_one

# Patrones de lineas que deben ser IVA0 en facturas de agente aduanero
# Basado en las facturas correctas de Pastorino (Primatransit)
PATRONES_IVA0 = [
    "DERECHOS ARANCEL",
    "IVA ADUANA",
    "CAUCION",
    "ADQUISICION CERTIFICADOS",
    "COSTES NAVIERA MAERSK",
]


def linea_debe_ser_iva0(descripcion: str) -> bool:
    """Determina si una linea debe tener IVA0 basandose en patrones conocidos."""
    desc_upper = descripcion.upper()
    return any(patron in desc_upper for patron in PATRONES_IVA0)


def obtener_facturas_cargaexpress(idempresa: int) -> list:
    """Obtiene facturas de Cargaexpress filtradas por empresa."""
    facturas = api_get("facturaproveedores")
    return [
        f for f in facturas
        if f.get("idempresa") == idempresa
        and "CARGA" in (f.get("nombre", "") or "").upper()
    ]


def obtener_lineas_factura(idfactura: int, todas_lineas: list) -> list:
    """Filtra lineas de una factura especifica."""
    return sorted(
        [l for l in todas_lineas if l.get("idfactura") == idfactura],
        key=lambda x: x["idlinea"]
    )


def obtener_partidas_asiento(idasiento: int, todas_partidas: list) -> list:
    """Filtra partidas de un asiento especifico."""
    return [p for p in todas_partidas if p.get("idasiento") == idasiento]


def corregir_linea(idlinea: int, descripcion: str) -> dict:
    """Cambia codimpuesto a IVA0 en una linea de factura."""
    resultado = api_put(
        f"lineafacturaproveedores/{idlinea}",
        data={"codimpuesto": "IVA0", "iva": 0}
    )
    return resultado


def corregir_partida(idpartida: int, campo: str, nuevo_valor: float) -> dict:
    """Actualiza un campo de una partida de asiento."""
    resultado = api_put(
        f"partidas/{idpartida}",
        data={campo: nuevo_valor}
    )
    return resultado


def main():
    print("=" * 70)
    print("CORRECCION IVA LINEAS CARGAEXPRESS — EMPRESA PRUEBA (empresa 3)")
    print("=" * 70)

    # === FASE 1: Obtener datos ===
    print("\n[1] Obteniendo datos de la API...")
    facturas_cargo = obtener_facturas_cargaexpress(idempresa=3)
    print(f"    Facturas Cargaexpress empresa 3: {len(facturas_cargo)}")

    todas_lineas = api_get("lineafacturaproveedores")
    print(f"    Total lineas factura proveedor: {len(todas_lineas)}")

    todas_partidas = api_get("partidas")
    print(f"    Total partidas: {len(todas_partidas)}")

    # === FASE 2: Identificar lineas a corregir ===
    print("\n[2] Identificando lineas con IVA incorrecto...")

    total_iva_indebido = 0
    correcciones = []  # lista de (factura, linea, iva_indebido)

    for factura in sorted(facturas_cargo, key=lambda f: f["idfactura"]):
        idfactura = factura["idfactura"]
        codigo = factura["codigo"]
        idasiento = factura["idasiento"]
        numproveedor = factura.get("numproveedor", "?")

        lineas = obtener_lineas_factura(idfactura, todas_lineas)
        print(f"\n  Factura {codigo} (id={idfactura}, num={numproveedor}, asiento={idasiento})")
        print(f"    Totales actuales: neto={factura['neto']} totaliva={factura['totaliva']} total={factura['total']}")

        lineas_a_corregir = []
        for linea in lineas:
            if linea_debe_ser_iva0(linea["descripcion"]) and linea["codimpuesto"] != "IVA0":
                iva_indebido = round(linea["pvptotal"] * 0.21, 2)
                lineas_a_corregir.append((linea, iva_indebido))
                total_iva_indebido += iva_indebido
                print(f"    [MAL] idlinea={linea['idlinea']} \"{linea['descripcion']}\" "
                      f"pvptotal={linea['pvptotal']} codimpuesto={linea['codimpuesto']} "
                      f"-> IVA indebido: {iva_indebido}")

        if not lineas_a_corregir:
            print("    [OK] Todas las lineas tienen IVA correcto")
            continue

        iva_indebido_factura = sum(iva for _, iva in lineas_a_corregir)
        base_indebida = sum(l["pvptotal"] for l, _ in lineas_a_corregir)
        correcciones.append({
            "factura": factura,
            "lineas": lineas_a_corregir,
            "iva_indebido_factura": iva_indebido_factura,
            "base_indebida": base_indebida,
        })
        print(f"    Total IVA indebido esta factura: {iva_indebido_factura}")

    print(f"\n  TOTAL IVA INDEBIDO a eliminar: {total_iva_indebido}")

    if not correcciones:
        print("\n[OK] No hay lineas que corregir. Todo esta correcto.")
        return

    # === FASE 3: Aplicar correcciones a lineas ===
    print("\n[3] Corrigiendo lineas de factura (codimpuesto -> IVA0)...")

    for corr in correcciones:
        factura = corr["factura"]
        print(f"\n  Factura {factura['codigo']} (id={factura['idfactura']})")

        for linea, iva_ind in corr["lineas"]:
            print(f"    PUT lineafacturaproveedores/{linea['idlinea']} "
                  f"codimpuesto=IVA0, iva=0 ... ", end="")
            try:
                resultado = corregir_linea(linea["idlinea"], linea["descripcion"])
                print("OK")
            except Exception as e:
                print(f"ERROR: {e}")

    # === FASE 4: Recalcular totales de facturas ===
    # FS no recalcula automaticamente al cambiar lineas — hacerlo via PUT
    print("\n[4] Recalculando totales de facturas...")

    # Recargar lineas frescas
    todas_lineas = api_get("lineafacturaproveedores")

    for corr in correcciones:
        factura = corr["factura"]
        idfactura = factura["idfactura"]

        lineas_factura = obtener_lineas_factura(idfactura, todas_lineas)

        # Calcular totaliva correcto sumando pvptotal * iva/100 por linea
        nuevo_totaliva = round(sum(
            l["pvptotal"] * l["iva"] / 100 for l in lineas_factura
        ), 2)
        nuevo_total = round(factura["neto"] + nuevo_totaliva, 2)

        print(f"\n  Factura {factura['codigo']} (id={idfactura})")
        print(f"    ANTES: neto={factura['neto']} totaliva={factura['totaliva']} total={factura['total']}")
        print(f"    NUEVO: neto={factura['neto']} totaliva={nuevo_totaliva} total={nuevo_total}")

        try:
            api_put(f"facturaproveedores/{idfactura}", data={
                "totaliva": nuevo_totaliva,
                "total": nuevo_total,
                "totaleuros": nuevo_total,
            })
            print(f"    OK")
        except Exception as e:
            print(f"    ERROR: {e}")

        # Verificar
        factura_nueva = api_get_one(f"facturaproveedores/{idfactura}")
        if factura_nueva:
            print(f"    Verificado: totaliva={factura_nueva['totaliva']} total={factura_nueva['total']}")

    # === FASE 5: Corregir partidas del asiento ===
    print("\n[5] Corrigiendo partidas de asientos...")

    # Recargar partidas frescas
    todas_partidas = api_get("partidas")

    for corr in correcciones:
        factura = corr["factura"]
        idasiento = factura["idasiento"]
        iva_indebido = corr["iva_indebido_factura"]
        base_indebida = corr["base_indebida"]

        partidas = obtener_partidas_asiento(idasiento, todas_partidas)

        print(f"\n  Asiento {idasiento} (factura {factura['codigo']})")
        print(f"    IVA indebido a reducir: {iva_indebido}")

        # Identificar partidas
        partida_400 = None  # proveedor (HABER)
        partida_472_21 = None  # IVA soportado 21% (DEBE)
        partida_600 = None  # compras (DEBE)

        for p in partidas:
            cuenta = p["codsubcuenta"]
            if cuenta.startswith("400"):
                partida_400 = p
            elif cuenta.startswith("472") and p.get("iva") == 21:
                partida_472_21 = p
            elif cuenta.startswith("600"):
                partida_600 = p

        print(f"    Partidas encontradas:")
        if partida_400:
            print(f"      400 (proveedor): idpartida={partida_400['idpartida']} debe={partida_400['debe']} haber={partida_400['haber']}")
        if partida_472_21:
            print(f"      472/IVA21: idpartida={partida_472_21['idpartida']} debe={partida_472_21['debe']} haber={partida_472_21['haber']} base={partida_472_21['baseimponible']}")
        if partida_600:
            print(f"      600 (compras): idpartida={partida_600['idpartida']} debe={partida_600['debe']} haber={partida_600['haber']}")

        if not partida_400 or not partida_472_21:
            print(f"    [ERROR] No se encontraron partidas clave. Saltar.")
            continue

        # Corregir partida 472/IVA21: reducir DEBE por IVA indebido, reducir baseimponible
        nuevo_debe_472 = round(partida_472_21["debe"] - iva_indebido, 2)
        nueva_base_472 = round(partida_472_21["baseimponible"] - base_indebida, 2)
        print(f"\n    Corrigiendo 472/IVA21 (idpartida={partida_472_21['idpartida']}):")
        print(f"      debe: {partida_472_21['debe']} -> {nuevo_debe_472}")
        print(f"      baseimponible: {partida_472_21['baseimponible']} -> {nueva_base_472}")

        try:
            api_put(f"partidas/{partida_472_21['idpartida']}", data={
                "debe": nuevo_debe_472,
                "baseimponible": nueva_base_472,
            })
            print(f"      OK")
        except Exception as e:
            print(f"      ERROR: {e}")

        # Corregir partida 400 (proveedor): reducir HABER por IVA indebido
        nuevo_haber_400 = round(partida_400["haber"] - iva_indebido, 2)
        print(f"\n    Corrigiendo 400 (idpartida={partida_400['idpartida']}):")
        print(f"      haber: {partida_400['haber']} -> {nuevo_haber_400}")

        try:
            api_put(f"partidas/{partida_400['idpartida']}", data={
                "haber": nuevo_haber_400,
            })
            print(f"      OK")
        except Exception as e:
            print(f"      ERROR: {e}")

    # === FASE 6: Verificar cuadre final de asientos ===
    print("\n[6] Verificando cuadre final de asientos...")

    # Recargar partidas
    todas_partidas = api_get("partidas")

    for corr in correcciones:
        factura = corr["factura"]
        idasiento = factura["idasiento"]
        partidas = obtener_partidas_asiento(idasiento, todas_partidas)

        total_debe = sum(p["debe"] for p in partidas)
        total_haber = sum(p["haber"] for p in partidas)
        cuadra = abs(total_debe - total_haber) < 0.01

        print(f"\n  Asiento {idasiento} (factura {factura['codigo']}):")
        for p in partidas:
            print(f"    {p['codsubcuenta']} debe={p['debe']} haber={p['haber']} "
                  f"iva={p.get('iva')} base={p.get('baseimponible')}")
        print(f"    TOTAL: debe={total_debe:.2f} haber={total_haber:.2f} "
              f"{'CUADRA' if cuadra else 'NO CUADRA !!!'}")

    # === FASE 7: Verificar Primatransit en Pastorino ===
    print("\n" + "=" * 70)
    print("[7] Verificacion Primatransit en Pastorino (empresa 1)")
    print("=" * 70)

    facturas_all = api_get("facturaproveedores")
    facturas_prima = [
        f for f in facturas_all
        if f.get("idempresa") == 1
        and "PRIMATRANSIT" in (f.get("nombre", "") or "").upper()
    ]

    # Solo las facturas equivalentes (numproveedor = 2390101398, etc.)
    nums_equivalentes = {"2390101398", "2390101399", "2390101400", "2390102446"}
    facturas_prima_equiv = [f for f in facturas_prima if f.get("numproveedor") in nums_equivalentes]

    print(f"  Facturas Primatransit equivalentes: {len(facturas_prima_equiv)}")

    hay_error_pastorino = False
    for factura in sorted(facturas_prima_equiv, key=lambda f: f["idfactura"]):
        lineas = obtener_lineas_factura(factura["idfactura"], todas_lineas)
        print(f"\n  Factura {factura['codigo']} (id={factura['idfactura']}, num={factura.get('numproveedor')})")

        for linea in lineas:
            if linea_debe_ser_iva0(linea["descripcion"]):
                estado = "OK" if linea["codimpuesto"] == "IVA0" else "MAL"
                if estado == "MAL":
                    hay_error_pastorino = True
                print(f"    [{estado}] \"{linea['descripcion']}\" codimpuesto={linea['codimpuesto']}")

    if not hay_error_pastorino:
        print("\n  [OK] Todas las lineas equivalentes en Pastorino ya tienen IVA0 correcto")
    else:
        print("\n  [WARN] Hay lineas con IVA incorrecto en Pastorino — requiere correccion separada")

    # === RESUMEN FINAL ===
    print("\n" + "=" * 70)
    print("RESUMEN FINAL")
    print("=" * 70)

    print(f"\nFacturas corregidas: {len(correcciones)}")
    total_lineas_corregidas = sum(len(c["lineas"]) for c in correcciones)
    print(f"Lineas corregidas: {total_lineas_corregidas}")
    print(f"IVA indebido total eliminado: {total_iva_indebido:.2f} EUR")
    print(f"Asientos con partidas ajustadas: {len(correcciones)}")
    print(f"Pastorino (empresa 1): {'OK' if not hay_error_pastorino else 'REQUIERE CORRECCION'}")


if __name__ == "__main__":
    main()
