#!/usr/bin/env python3
"""
Inyeccion de datos de prueba en empresa 4 (CHIRINGUITO SOL Y ARENA S.L.)
para testing del dashboard SFCE.

Genera ~2000 facturas + asientos para ejercicios 2022-2025.

Uso:
    python scripts/inyectar_datos_chiringuito.py --fase todo
    python scripts/inyectar_datos_chiringuito.py --fase fc --anyo 2023
    python scripts/inyectar_datos_chiringuito.py --dry-run
    python scripts/inyectar_datos_chiringuito.py --limpiar-estado
"""
import argparse
import json
import os
import random
import time
from datetime import date, timedelta
from pathlib import Path

import requests

# --- Configuracion ---
API_BASE = "https://contabilidad.lemonfresh-tuc.com/api/3"
TOKEN = os.getenv("FS_API_TOKEN", "iOXmrA1Bbn8RDWXLv91L")
HEADERS = {"Token": TOKEN}
IDEMPRESA = 4
DELAY = 0.25  # segundos entre llamadas API

EJERCICIOS = {
    2022: "C422",
    2023: "C423",
    2024: "C424",
    2025: "0004",
}

ESTADO_PATH = Path(__file__).parent.parent / "tmp" / "estado_inyeccion_chiringuito.json"
ESTADO_PATH.parent.mkdir(exist_ok=True)

# Distribucion % mensual de ventas (actividad estacional)
DIST_MENSUAL = [0.01, 0.01, 0.02, 0.08, 0.10, 0.10, 0.22, 0.25, 0.12, 0.05, 0.02, 0.02]

# Ingresos anuales por ejercicio
INGRESOS_ANUALES = {2022: 360_000, 2023: 440_000, 2024: 510_000, 2025: 475_000}

FC_POR_ANYO = 300
FV_POR_ANYO = 200
CUOTA_AMORT_ANUAL = 8_000  # 80.000 activo x 10% lineal

# Subcuentas estandar PGC
SC = {
    "sueldos":    "6400000000",
    "ss_empresa": "6420000000",
    "irpf_ret":   "4751000000",
    "ss_acred":   "4760000000",
    "rem_pend":   "4651000000",
    "banco":      "5720000000",
    "amort_dot":  "6811000000",
    "amort_acum": "2813000000",
    "iva_rep":    "4770000000",
    "iva_sop":    "4720000000",
    "hp_acr":     "4750000000",
    "resultado":  "1290000000",
    "ventas":     "7000000000",
    "compras":    "6000000000",
}

# Datos maestros
PROVEEDORES = [
    {"cod": "MAKRO",      "cif": "A28054609", "nombre": "MAKRO AUTOSERVICIO S.A.",          "codimpuesto": "IVA21"},
    {"cod": "AYTOMARB",   "cif": "P2906010J", "nombre": "AYUNTAMIENTO DE MARBELLA",          "codimpuesto": "IVA21"},
    {"cod": "RENTMOB",    "cif": "B29022340", "nombre": "RENTING MOBILIARIO TERRAZA S.L.",   "codimpuesto": "IVA21"},
    {"cod": "GCOSTA","cif": "B29055407", "nombre": "GRUPO GASTRO COSTA DEL SOL S.L.",   "codimpuesto": "IVA21"},  # cod se trunca a 10 en API
    {"cod": "ENDESA",     "cif": "A81948077", "nombre": "ENDESA ENERGIA S.A.U.",             "codimpuesto": "IVA21"},
]

CLIENTES = [
    {"cod": "VENTASD", "cif": "00000000T", "nombre": "VENTAS DIARIAS PLAYA",   "codimpuesto": "IVA10"},
    {"cod": "EVENTOS",  "cif": "00000001R", "nombre": "EVENTOS PRIVADOS PLAYA", "codimpuesto": "IVA10"},
]

GASTOS_PROVEEDORES = {
    "MAKRO":       {"pct": 0.32, "concepto": "Suministro alimentacion y bebidas temporada"},
    "AYTOMARB":    {"pct": 0.04, "concepto": "Canon anual licencia ocupacion dominio publico maritimo"},
    "RENTMOB":     {"pct": 0.03, "concepto": "Cuota renting hamacas sombrillas y mobiliario playa"},
    "GCOSTA": {"pct": 0.025,"concepto": "Management fee gestion operaciones hosteleria"},
    "ENDESA":      {"pct": 0.02, "concepto": "Suministro electrico instalaciones chiringuito"},
}

REPARTO_FV = {"MAKRO": 0.60, "RENTMOB": 0.12, "ENDESA": 0.12, "GCOSTA": 0.08, "AYTOMARB": 0.08}


# --- Helpers API ---
def api_get(endpoint, params=None):
    r = requests.get(f"{API_BASE}/{endpoint}", headers=HEADERS,
                     params=params or {}, timeout=30)
    r.raise_for_status()
    return r.json()


def api_post_form(endpoint, data):
    r = requests.post(f"{API_BASE}/{endpoint}", headers=HEADERS,
                      data=data, timeout=30)
    r.raise_for_status()
    return r.json()


def api_put_form(endpoint, data):
    r = requests.put(f"{API_BASE}/{endpoint}", headers=HEADERS,
                     data=data, timeout=30)
    r.raise_for_status()
    return r.json()


# --- Estado ---
def cargar_estado():
    if ESTADO_PATH.exists():
        return json.loads(ESTADO_PATH.read_text(encoding="utf-8"))
    return {"fc": {}, "fv": {}, "asientos": {}, "entidades": {}}


def guardar_estado(estado):
    ESTADO_PATH.write_text(json.dumps(estado, indent=2, ensure_ascii=False), encoding="utf-8")


# --- Utilidades ---
def fecha_aleatoria_mes(anyo, mes):
    inicio = date(anyo, mes, 1)
    fin = date(anyo, mes + 1, 1) - timedelta(days=1) if mes < 12 else date(anyo, 12, 31)
    return inicio + timedelta(days=random.randint(0, (fin - inicio).days))


def distribuir_por_mes(total, dist):
    por_mes = [max(1, round(total * p)) for p in dist]
    diff = total - sum(por_mes)
    por_mes[7] += diff  # agosto absorbe diferencia
    return por_mes


def entidad_existe(tipo, cod):
    ep = "clientes" if tipo == "cliente" else "proveedores"
    try:
        data = api_get(f"{ep}/{cod}")
        return bool(data)
    except Exception:
        return False


# --- Fases ---
def asegurar_entidades(estado, dry_run=False):
    print("\n[ENTIDADES] Verificando clientes y proveedores...")
    for prov in PROVEEDORES:
        cod = prov["cod"]
        if estado["entidades"].get(f"prov_{cod}"):
            print(f"  Proveedor {cod}: ya en estado")
            continue
        if entidad_existe("proveedor", cod):
            estado["entidades"][f"prov_{cod}"] = True
            print(f"  Proveedor {cod}: ya existe en FS")
            continue
        if dry_run:
            print(f"  [DRY] Crearia proveedor {cod}")
            continue
        api_post_form("proveedores", {
            "idempresa": IDEMPRESA, "codproveedor": cod,
            "cifnif": prov["cif"], "nombre": prov["nombre"],
            "codimpuesto": prov["codimpuesto"], "codpais": "ESP", "coddivisa": "EUR",
        })
        estado["entidades"][f"prov_{cod}"] = True
        print(f"  Proveedor {cod}: CREADO")
        time.sleep(DELAY)

    for cli in CLIENTES:
        cod = cli["cod"]
        if estado["entidades"].get(f"cli_{cod}"):
            print(f"  Cliente {cod}: ya en estado")
            continue
        if entidad_existe("cliente", cod):
            estado["entidades"][f"cli_{cod}"] = True
            print(f"  Cliente {cod}: ya existe en FS")
            continue
        if dry_run:
            print(f"  [DRY] Crearia cliente {cod}")
            continue
        api_post_form("clientes", {
            "idempresa": IDEMPRESA, "codcliente": cod,
            "cifnif": cli["cif"], "nombre": cli["nombre"],
            "codimpuesto": cli["codimpuesto"], "codpais": "ESP", "coddivisa": "EUR",
        })
        estado["entidades"][f"cli_{cod}"] = True
        print(f"  Cliente {cod}: CREADO")
        time.sleep(DELAY)


def generar_fc(anyo, estado, dry_run=False):
    clave = str(anyo)
    if clave not in estado["fc"]:
        estado["fc"][clave] = []
    ya = len(estado["fc"][clave])
    if ya >= FC_POR_ANYO:
        print(f"\n[FC {anyo}] Ya completas ({ya}/{FC_POR_ANYO})")
        return

    codejercicio = EJERCICIOS[anyo]
    ingresos = INGRESOS_ANUALES[anyo]
    por_mes = distribuir_por_mes(FC_POR_ANYO, DIST_MENSUAL)
    ticket_medio = ingresos / FC_POR_ANYO
    print(f"\n[FC {anyo}] Generando {FC_POR_ANYO - ya} facturas (ticket medio {ticket_medio:.0f} EUR)...")

    creadas = 0
    idx = 0
    for mes_idx, num_mes in enumerate(por_mes):
        mes = mes_idx + 1
        for _ in range(num_mes):
            if idx < ya:
                idx += 1
                continue
            es_evento = random.random() < 0.30
            codcliente = "EVENTOS" if es_evento else "VENTASD"
            concepto = ("Servicio catering y organizacion evento privado" if es_evento
                        else "Servicio restauracion y hosteleria en playa")
            factor = random.uniform(1.5, 4.0) if es_evento else random.uniform(0.6, 1.4)
            base = round(ticket_medio * factor * (0.8 if es_evento else 1.0), 2)
            fecha = fecha_aleatoria_mes(anyo, mes)

            if dry_run:
                print(f"  [DRY] FC {anyo}/{mes:02d} {codcliente} {base:.2f}EUR")
                idx += 1
                continue

            lineas = json.dumps([{"descripcion": concepto, "cantidad": 1,
                                  "pvpunitario": base, "codimpuesto": "IVA10"}])
            try:
                resp = api_post_form("crearFacturaCliente", {
                    "idempresa": IDEMPRESA, "codejercicio": codejercicio,
                    "codcliente": codcliente, "fecha": fecha.strftime("%d-%m-%Y"),
                    "coddivisa": "EUR", "lineas": lineas,
                })
                idfactura = (resp.get("doc", {}).get("idfactura")
                             or resp.get("idfactura"))
                estado["fc"][clave].append({"id": idfactura, "fecha": str(fecha), "base": base})
                creadas += 1
                if creadas % 25 == 0:
                    guardar_estado(estado)
                    print(f"  ... {creadas + ya} / {FC_POR_ANYO}")
            except Exception as e:
                print(f"  ERROR FC {fecha}: {e}")
            time.sleep(DELAY)
            idx += 1

    guardar_estado(estado)
    print(f"[FC {anyo}] COMPLETADO: {creadas} nuevas (total {len(estado['fc'][clave])})")


def generar_fv(anyo, estado, dry_run=False):
    clave = str(anyo)
    if clave not in estado["fv"]:
        estado["fv"][clave] = []
    ya = len(estado["fv"][clave])
    if ya >= FV_POR_ANYO:
        print(f"\n[FV {anyo}] Ya completas ({ya}/{FV_POR_ANYO})")
        return

    codejercicio = EJERCICIOS[anyo]
    ingresos = INGRESOS_ANUALES[anyo]
    print(f"\n[FV {anyo}] Generando facturas proveedor...")

    creadas = 0
    idx = 0
    for cod, info in GASTOS_PROVEEDORES.items():
        num = max(1, round(FV_POR_ANYO * REPARTO_FV.get(cod, 0.1)))
        gasto_total = ingresos * info["pct"]
        importe_medio = gasto_total / num

        if cod == "AYTOMARB":
            fechas = [date(anyo, 3, 15)]
        elif cod in ("RENTMOB", "ENDESA"):
            fechas = [date(anyo, mes, random.randint(1, 28)) for mes in range(1, 13)]
        elif cod == "GCOSTA":
            fechas = [date(anyo, mes, random.randint(1, 28)) for mes in [3, 6, 9, 12]]
        else:
            por_mes = distribuir_por_mes(num, DIST_MENSUAL)
            fechas = []
            for mi, n in enumerate(por_mes):
                for _ in range(n):
                    fechas.append(fecha_aleatoria_mes(anyo, mi + 1))

        for i, fecha in enumerate(fechas[:num]):
            if idx < ya:
                idx += 1
                continue
            base = round(importe_medio * random.uniform(0.7, 1.3), 2)
            num_factura = f"{cod[:4]}{anyo}{i+1:03d}"

            if dry_run:
                print(f"  [DRY] FV {anyo} {cod} {base:.2f}EUR {fecha}")
                idx += 1
                continue

            lineas = json.dumps([{"descripcion": info["concepto"], "cantidad": 1,
                                  "pvpunitario": base, "codimpuesto": "IVA21"}])
            try:
                resp = api_post_form("crearFacturaProveedor", {
                    "idempresa": IDEMPRESA, "codejercicio": codejercicio,
                    "codproveedor": cod, "numproveedor": num_factura,
                    "fecha": fecha.strftime("%d-%m-%Y"),
                    "coddivisa": "EUR", "lineas": lineas,
                })
                idfactura = (resp.get("doc", {}).get("idfactura")
                             or resp.get("idfactura"))
                estado["fv"][clave].append({"id": idfactura, "cod": cod,
                                            "fecha": str(fecha), "base": base})
                creadas += 1
                if creadas % 20 == 0:
                    guardar_estado(estado)
                    print(f"  ... {creadas + ya} FV creadas")
            except Exception as e:
                print(f"  ERROR FV {cod} {fecha}: {e}")
            time.sleep(DELAY)
            idx += 1

    guardar_estado(estado)
    print(f"[FV {anyo}] COMPLETADO: {creadas} nuevas (total {len(estado['fv'][clave])})")


def crear_asiento(concepto, fecha, codejercicio, partidas, dry_run=False):
    if dry_run:
        print(f"  [DRY] Asiento '{concepto}' {fecha}: {len(partidas)} partidas")
        return None
    resp = api_post_form("asientos", {
        "idempresa": IDEMPRESA, "codejercicio": codejercicio,
        "fecha": fecha.strftime("%d-%m-%Y"), "concepto": concepto,
    })
    idasiento = resp.get("data", {}).get("idasiento") or resp.get("idasiento")
    if not idasiento:
        print(f"  ERROR: no idasiento en: {resp}")
        return None
    for p in partidas:
        p["idasiento"] = idasiento
        p["idempresa"] = IDEMPRESA
        try:
            api_post_form("partidas", p)
        except Exception as e:
            print(f"  ERROR partida: {e}")
        time.sleep(DELAY * 0.5)
    time.sleep(DELAY)
    return idasiento


def generar_asientos_directos(anyo, estado, dry_run=False):
    clave = str(anyo)
    if clave not in estado["asientos"]:
        estado["asientos"][clave] = []
    codejercicio = EJERCICIOS[anyo]
    masa = INGRESOS_ANUALES[anyo] * 0.28
    cuota_mens = round(CUOTA_AMORT_ANUAL / 12, 2)
    meses_plenos = list(range(4, 11))
    print(f"\n[ASIENTOS {anyo}] Nominas + amortizaciones...")

    for mes in range(1, 13):
        fecha = date(anyo, mes, 28)

        # Nomina
        clave_nom = f"nom_{anyo}_{mes:02d}"
        if not any(a.get("clave") == clave_nom for a in estado["asientos"][clave]):
            sueldo = round((masa / 7) if mes in meses_plenos else (masa * 0.15 / 5), 2)
            ss_emp = round(sueldo * 0.295, 2)
            irpf = round(sueldo * 0.15, 2)
            ss_trab = round(sueldo * 0.0635, 2)
            neto = round(sueldo - irpf - ss_trab, 2)
            partidas = [
                {"codsubcuenta": SC["sueldos"],    "debe": sueldo, "haber": 0,           "concepto": f"Nomina {mes:02d}/{anyo}"},
                {"codsubcuenta": SC["ss_empresa"], "debe": ss_emp, "haber": 0,            "concepto": f"SS empresa {mes:02d}/{anyo}"},
                {"codsubcuenta": SC["irpf_ret"],   "debe": 0,      "haber": irpf,         "concepto": f"IRPF ret {mes:02d}/{anyo}"},
                {"codsubcuenta": SC["ss_acred"],   "debe": 0,      "haber": ss_emp + ss_trab, "concepto": f"SS acred {mes:02d}/{anyo}"},
                {"codsubcuenta": SC["rem_pend"],   "debe": 0,      "haber": neto,         "concepto": f"Rem pend {mes:02d}/{anyo}"},
            ]
            ida = crear_asiento(f"Nomina {mes:02d}/{anyo}", fecha, codejercicio, partidas, dry_run)
            estado["asientos"][clave].append({"clave": clave_nom, "id": ida})

        # Amortizacion
        clave_am = f"amort_{anyo}_{mes:02d}"
        if not any(a.get("clave") == clave_am for a in estado["asientos"][clave]):
            partidas = [
                {"codsubcuenta": SC["amort_dot"],  "debe": cuota_mens, "haber": 0,          "concepto": f"Amort inmovilizado {mes:02d}/{anyo}"},
                {"codsubcuenta": SC["amort_acum"], "debe": 0,          "haber": cuota_mens,  "concepto": f"Amort acumulada {mes:02d}/{anyo}"},
            ]
            ida = crear_asiento(f"Amortizacion {mes:02d}/{anyo}", fecha, codejercicio, partidas, dry_run)
            estado["asientos"][clave].append({"clave": clave_am, "id": ida})

    guardar_estado(estado)
    print(f"[ASIENTOS {anyo}] Nominas + amortizaciones OK")


def generar_iva_trimestral(anyo, estado, dry_run=False):
    clave = str(anyo)
    if clave not in estado["asientos"]:
        estado["asientos"][clave] = []
    codejercicio = EJERCICIOS[anyo]
    ingresos = INGRESOS_ANUALES[anyo]
    gastos = ingresos * (0.32 + 0.03 + 0.02 + 0.025 + 0.04)
    iva_rep_anual = ingresos * 0.10
    iva_sop_anual = gastos * 0.21
    dist_trim = [0.12, 0.23, 0.55, 0.10]
    fechas_trim = [date(anyo, 4, 20), date(anyo, 7, 20), date(anyo, 10, 20), date(anyo, 12, 30)]
    nombres = ["T1", "T2", "T3", "T4"]
    print(f"\n[IVA {anyo}] Liquidaciones trimestrales...")

    for fecha, nombre, pct in zip(fechas_trim, nombres, dist_trim):
        clave_iva = f"iva_{anyo}_{nombre}"
        if any(a.get("clave") == clave_iva for a in estado["asientos"][clave]):
            continue
        iva_rep = round(iva_rep_anual * pct, 2)
        iva_sop = round(iva_sop_anual * pct, 2)
        resultado = round(iva_rep - iva_sop, 2)
        partidas = [
            {"codsubcuenta": SC["iva_rep"], "debe": iva_rep, "haber": 0,      "concepto": f"IVA repercutido {nombre} {anyo}"},
            {"codsubcuenta": SC["iva_sop"], "debe": 0,       "haber": iva_sop, "concepto": f"IVA soportado {nombre} {anyo}"},
        ]
        if resultado >= 0:
            partidas.append({"codsubcuenta": SC["hp_acr"], "debe": 0, "haber": resultado,
                             "concepto": f"HP acreedora IVA {nombre} {anyo}"})
        else:
            partidas.append({"codsubcuenta": SC["iva_sop"], "debe": abs(resultado), "haber": 0,
                             "concepto": f"HP deudora IVA {nombre} {anyo}"})
        ida = crear_asiento(f"Liquidacion IVA {nombre} {anyo}", fecha, codejercicio, partidas, dry_run)
        estado["asientos"][clave].append({"clave": clave_iva, "id": ida})

    guardar_estado(estado)
    print(f"[IVA {anyo}] Liquidaciones OK")


def cerrar_ejercicio(anyo, estado, dry_run=False):
    clave = str(anyo)
    if clave not in estado["asientos"]:
        estado["asientos"][clave] = []
    clave_cierre = f"cierre_{anyo}"
    if any(a.get("clave") == clave_cierre for a in estado["asientos"][clave]):
        print(f"\n[CIERRE {anyo}] Ya realizado")
        return
    codejercicio = EJERCICIOS[anyo]
    ingresos = INGRESOS_ANUALES[anyo]
    gastos_tot = ingresos * 0.88
    resultado = round(ingresos - gastos_tot, 2)
    fecha = date(anyo, 12, 31)
    print(f"\n[CIERRE {anyo}] Resultado neto estimado: {resultado:,.2f} EUR")

    partidas = [
        {"codsubcuenta": SC["ventas"],   "debe": ingresos,                        "haber": 0,           "concepto": f"Regularizacion ingresos {anyo}"},
        {"codsubcuenta": SC["sueldos"],  "debe": 0, "haber": round(ingresos*0.28, 2),                   "concepto": f"Regularizacion gastos personal {anyo}"},
        {"codsubcuenta": SC["compras"],  "debe": 0, "haber": round(ingresos*0.32, 2),                   "concepto": f"Regularizacion compras {anyo}"},
        {"codsubcuenta": SC["amort_dot"],"debe": 0, "haber": CUOTA_AMORT_ANUAL,                         "concepto": f"Regularizacion amortizacion {anyo}"},
        {"codsubcuenta": SC["resultado"],"debe": 0, "haber": resultado,                                 "concepto": f"Resultado ejercicio {anyo}"},
    ]
    ida = crear_asiento(f"Regularizacion cierre {anyo}", fecha, codejercicio, partidas, dry_run)

    if not dry_run:
        try:
            api_put_form(f"ejercicios/{codejercicio}", {"estado": "CERRADO"})
            print(f"  Ejercicio {codejercicio} marcado CERRADO")
        except Exception as e:
            print(f"  AVISO cierre ejercicio: {e}")

    estado["asientos"][clave].append({"clave": clave_cierre, "id": ida})
    guardar_estado(estado)
    print(f"[CIERRE {anyo}] COMPLETADO")


# --- Main ---
def main():
    parser = argparse.ArgumentParser(description="Inyeccion datos CHIRINGUITO SOL Y ARENA empresa 4")
    parser.add_argument("--fase", choices=["entidades", "fc", "fv", "asientos", "cierre", "todo"],
                        default="todo")
    parser.add_argument("--anyo", type=int, choices=[2022, 2023, 2024, 2025], default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limpiar-estado", action="store_true")
    args = parser.parse_args()

    if args.limpiar_estado:
        ESTADO_PATH.unlink(missing_ok=True)
        print("Estado limpiado.")
        return

    estado = cargar_estado()
    anyos = [args.anyo] if args.anyo else list(EJERCICIOS.keys())

    if args.fase in ("entidades", "todo"):
        asegurar_entidades(estado, dry_run=args.dry_run)
        guardar_estado(estado)

    if args.fase in ("fc", "todo"):
        for anyo in anyos:
            generar_fc(anyo, estado, dry_run=args.dry_run)

    if args.fase in ("fv", "todo"):
        for anyo in anyos:
            generar_fv(anyo, estado, dry_run=args.dry_run)

    if args.fase in ("asientos", "todo"):
        for anyo in anyos:
            generar_asientos_directos(anyo, estado, dry_run=args.dry_run)
            generar_iva_trimestral(anyo, estado, dry_run=args.dry_run)

    if args.fase in ("cierre", "todo"):
        for anyo in [2022, 2023, 2024]:
            if args.anyo is None or args.anyo == anyo:
                cerrar_ejercicio(anyo, estado, dry_run=args.dry_run)

    guardar_estado(estado)
    fc_total = sum(len(v) for v in estado["fc"].values())
    fv_total = sum(len(v) for v in estado["fv"].values())
    as_total = sum(len(v) for v in estado["asientos"].values())
    print(f"\n=== RESUMEN ===")
    print(f"FC creadas  : {fc_total}")
    print(f"FV creadas  : {fv_total}")
    print(f"Asientos    : {as_total}")
    print(f"TOTAL docs  : {fc_total + fv_total + as_total}")


if __name__ == "__main__":
    main()
