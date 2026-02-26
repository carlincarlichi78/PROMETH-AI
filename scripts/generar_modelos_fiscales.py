"""
Generacion de modelos fiscales desde la API de FacturaScripts.

Genera archivos .txt con los modelos fiscales en la carpeta del cliente:
- Modelo 303 (IVA trimestral) x4
- Modelo 349 (operaciones intracomunitarias) x4
- Modelo 347 (operaciones con terceros >3.005,06 EUR) anual
- Modelo 390 (resumen anual IVA)
- Balance de Situacion provisional
- Cuenta de PyG provisional
- Resumen general

Uso:
  export FS_API_TOKEN='tu_token_aqui'
  python scripts/generar_modelos_fiscales.py clientes/pastorino-costa-del-sol
  python scripts/generar_modelos_fiscales.py clientes/pastorino-costa-del-sol --ejercicio 2025 --empresa 1
"""

import requests
import os
import sys
import argparse
from datetime import datetime
from collections import defaultdict
from pathlib import Path


# --- Configuracion ---

API_BASE = os.environ.get(
    "FS_API_URL",
    "https://contabilidad.lemonfresh-tuc.com/api/3",
)

TOKEN_FALLBACK = "iOXmrA1Bbn8RDWXLv91L"

TRIMESTRES = {
    "T1": ("01-01", "03-31"),
    "T2": ("04-01", "06-30"),
    "T3": ("07-01", "09-30"),
    "T4": ("10-01", "12-31"),
}

EMPRESAS = {
    1: {"nombre": "PASTORINO COSTA DEL SOL S.L.", "tipo": "sl", "cif": "B13995519"},
    2: {"nombre": "G. GONZALEZ (Gerardo Gonzalez Callejon)", "tipo": "autonomo", "cif": ""},
}

# Umbral modelo 347
UMBRAL_347 = 3005.06

# Paises UE (codigos FS)
PAISES_UE = {
    "AUT", "BEL", "BGR", "HRV", "CYP", "CZE", "DNK", "EST", "FIN", "FRA",
    "DEU", "GRC", "HUN", "IRL", "ITA", "LVA", "LTU", "LUX", "MLT", "NLD",
    "POL", "PRT", "ROU", "SVK", "SVN", "SWE",
}


# --- Utilidades ---

def parsear_fecha(fecha_str):
    """Convierte DD-MM-YYYY a YYYY-MM-DD para comparaciones."""
    if not fecha_str:
        return ""
    partes = fecha_str.split("-")
    if len(partes) == 3 and len(partes[0]) == 2:
        return f"{partes[2]}-{partes[1]}-{partes[0]}"
    return fecha_str


def eur(valor):
    """Formatea un numero como moneda EUR alineado a la derecha."""
    return f"{valor:>12,.2f} EUR"


def eur_simple(valor):
    """Formatea un numero como moneda EUR sin alineacion."""
    return f"{valor:,.2f} EUR"


# --- API ---

def api_get(token, endpoint, params=None):
    """GET a la API de FacturaScripts con paginacion automatica."""
    url = f"{API_BASE}/{endpoint}"
    todos = []
    params = dict(params or {})
    params.setdefault("limit", 50)
    params.setdefault("offset", 0)

    while True:
        resp = requests.get(url, headers={"Token": token}, params=params, timeout=30)
        resp.raise_for_status()
        lote = resp.json()

        if not lote:
            break

        todos.extend(lote)

        if len(lote) < params["limit"]:
            break

        params["offset"] += params["limit"]

    return todos


def filtrar_por_fecha(registros, campo_fecha, ejercicio, trimestre=None):
    """Filtra registros por rango de fechas (convierte DD-MM-YYYY a YYYY-MM-DD)."""
    if trimestre and trimestre in TRIMESTRES:
        inicio, fin = TRIMESTRES[trimestre]
        fecha_ini = f"{ejercicio}-{inicio}"
        fecha_fin = f"{ejercicio}-{fin}"
    else:
        fecha_ini = f"{ejercicio}-01-01"
        fecha_fin = f"{ejercicio}-12-31"

    return [
        r for r in registros
        if fecha_ini <= parsear_fecha(r.get(campo_fecha, "")) <= fecha_fin
    ]


# --- Obtencion de datos ---

def obtener_facturas_cliente(token, idempresa, ejercicio, trimestre=None):
    """Facturas emitidas (ventas/ingresos)."""
    facturas = api_get(token, "facturaclientes", {
        "idempresa": idempresa,
        "codejercicio": ejercicio,
    })
    # Post-filtro por idempresa (la API FS ignora el filtro en algunos endpoints)
    facturas = [f for f in facturas if str(f.get("idempresa")) == str(idempresa)]
    return filtrar_por_fecha(facturas, "fecha", ejercicio, trimestre)


def obtener_facturas_proveedor(token, idempresa, ejercicio, trimestre=None):
    """Facturas recibidas (compras/gastos)."""
    facturas = api_get(token, "facturaproveedores", {
        "idempresa": idempresa,
        "codejercicio": ejercicio,
    })
    # Post-filtro por idempresa (la API FS ignora el filtro en algunos endpoints)
    facturas = [f for f in facturas if str(f.get("idempresa")) == str(idempresa)]
    return filtrar_por_fecha(facturas, "fecha", ejercicio, trimestre)


def obtener_todas_lineas_factura_cliente(token):
    """Todas las lineas de facturas de cliente."""
    return api_get(token, "lineafacturaclientes")


def obtener_todas_lineas_factura_proveedor(token):
    """Todas las lineas de facturas de proveedor."""
    return api_get(token, "lineafacturaproveedores")


def obtener_subcuentas(token, idempresa, ejercicio):
    """Subcuentas contables con saldos recalculados para la empresa especifica.

    Los saldos de subcuentas en FS acumulan movimientos de TODAS las empresas.
    Recalculamos desde partidas filtradas por empresa para datos correctos.
    """
    from collections import defaultdict

    subcuentas_raw = api_get(token, "subcuentas", {"codejercicio": ejercicio})

    asientos = api_get(token, "asientos", {"codejercicio": ejercicio})
    asientos = [a for a in asientos if str(a.get("idempresa")) == str(idempresa)]
    ids_asientos = {a["idasiento"] for a in asientos}

    partidas = api_get(token, "partidas")
    partidas = [p for p in partidas if p["idasiento"] in ids_asientos]

    saldos = defaultdict(lambda: {"debe": 0.0, "haber": 0.0})
    for p in partidas:
        cod = p.get("codsubcuenta", "")
        saldos[cod]["debe"] += float(p.get("debe", 0))
        saldos[cod]["haber"] += float(p.get("haber", 0))

    mapa_desc = {s["codsubcuenta"]: s.get("descripcion", "") for s in subcuentas_raw}
    resultado = []
    for cod, vals in saldos.items():
        resultado.append({
            "codsubcuenta": cod,
            "descripcion": mapa_desc.get(cod, ""),
            "debe": vals["debe"],
            "haber": vals["haber"],
            "saldo": vals["debe"] - vals["haber"],
        })

    return resultado


def obtener_contactos(token):
    """Todos los contactos (proveedores/clientes)."""
    return api_get(token, "contactos")


# --- Desglose IVA por tipo ---

def desglosar_iva_facturas(facturas, todas_lineas):
    """Desglosa bases e IVA por tipo impositivo usando lineas pre-cargadas.

    Filtra localmente las lineas que pertenecen a las facturas indicadas.
    Retorna dict: {tipo_iva: {'base': float, 'iva': float}}
    """
    desglose = defaultdict(lambda: {"base": 0.0, "iva": 0.0})

    # Set de idfactura para filtrar rapido
    ids_facturas = {f["idfactura"] for f in facturas}

    for linea in todas_lineas:
        if linea.get("idfactura") not in ids_facturas:
            continue

        iva_pct = float(linea.get("iva", 0))
        pvptotal = float(linea.get("pvptotal", 0))
        iva_linea = pvptotal * iva_pct / 100
        clave = f"{iva_pct:.0f}%"
        desglose[clave]["base"] += pvptotal
        desglose[clave]["iva"] += iva_linea

    return dict(desglose)


# --- Modelo 303 ---

def calcular_modelo_303(fact_clientes, fact_proveedores, contactos_map,
                        lineas_cli, lineas_prov):
    """Modelo 303 - IVA trimestral con desglose por tipo y operaciones intracomunitarias."""

    # Totales directos de cabecera de factura
    iva_repercutido = sum(float(f.get("totaliva", 0)) for f in fact_clientes)
    iva_soportado = sum(float(f.get("totaliva", 0)) for f in fact_proveedores)
    base_ventas = sum(float(f.get("neto", 0)) for f in fact_clientes)
    base_compras = sum(float(f.get("neto", 0)) for f in fact_proveedores)

    # Desglose IVA repercutido por tipo (usando lineas pre-cargadas)
    desglose_rep = desglosar_iva_facturas(fact_clientes, lineas_cli)
    desglose_sop = desglosar_iva_facturas(fact_proveedores, lineas_prov)

    # Operaciones intracomunitarias (casillas 10-11 y 36-37)
    # Se identifican por proveedor con pais UE (no ESP)
    base_intracom = 0.0
    iva_intracom = 0.0

    for factura in fact_proveedores:
        codproveedor = str(factura.get("codproveedor", ""))
        contacto = contactos_map.get(codproveedor, {})
        codpais = contacto.get("codpais", "ESP")

        if codpais in PAISES_UE:
            neto = float(factura.get("neto", 0))
            base_intracom += neto
            # IVA autoliquidado al 21%
            iva_intracom += neto * 0.21

    # Resultado: repercutido + intracom devengado - soportado - intracom deducible
    # El intracom se anula (devengado = deducible)
    resultado = iva_repercutido + iva_intracom - iva_soportado - iva_intracom

    return {
        "base_ventas": base_ventas,
        "iva_repercutido": iva_repercutido,
        "desglose_repercutido": desglose_rep,
        "base_compras": base_compras,
        "iva_soportado": iva_soportado,
        "desglose_soportado": desglose_sop,
        "base_intracom": base_intracom,
        "iva_intracom": iva_intracom,
        "resultado": resultado,
        "a_ingresar": max(resultado, 0),
        "a_compensar": abs(min(resultado, 0)),
        "num_fact_emitidas": len(fact_clientes),
        "num_fact_recibidas": len(fact_proveedores),
    }


# --- Modelo 349 ---

def calcular_modelo_349(fact_proveedores, contactos_map):
    """Modelo 349 - Operaciones intracomunitarias del trimestre."""
    operaciones = defaultdict(lambda: {"cifnif": "", "nombre": "", "pais": "", "base": 0.0})

    for factura in fact_proveedores:
        codproveedor = str(factura.get("codproveedor", ""))
        contacto = contactos_map.get(codproveedor, {})
        codpais = contacto.get("codpais", "ESP")

        if codpais in PAISES_UE:
            neto = float(factura.get("neto", 0))
            cifnif = contacto.get("cifnif", "")
            nombre = factura.get("nombre", contacto.get("nombre", ""))
            operaciones[codproveedor]["cifnif"] = cifnif
            operaciones[codproveedor]["nombre"] = nombre
            operaciones[codproveedor]["pais"] = codpais
            operaciones[codproveedor]["base"] += neto

    return dict(operaciones)


# --- Modelo 347 ---

def calcular_modelo_347(fact_clientes, fact_proveedores, contactos_map):
    """Modelo 347 - Operaciones con terceros >3.005,06 EUR (anual)."""
    # Agrupar por CIF
    por_cif = defaultdict(lambda: {"nombre": "", "tipo": "", "total": 0.0})

    # Compras (tipo B)
    for factura in fact_proveedores:
        cifnif = factura.get("cifnif", "")
        nombre = factura.get("nombre", "")
        total = float(factura.get("total", 0))
        if cifnif:
            por_cif[cifnif]["nombre"] = nombre
            por_cif[cifnif]["tipo"] = "B"
            por_cif[cifnif]["total"] += abs(total)

    # Ventas (tipo A)
    for factura in fact_clientes:
        cifnif = factura.get("cifnif", "")
        nombre = (factura.get("nombre") or factura.get("nombrecliente", ""))
        total = float(factura.get("total", 0))
        if cifnif:
            clave = cifnif + "_V"
            por_cif[clave]["nombre"] = nombre
            por_cif[clave]["tipo"] = "A"
            por_cif[clave]["total"] += abs(total)

    # Filtrar por umbral
    resultado = {
        k: v for k, v in por_cif.items()
        if v["total"] > UMBRAL_347
    }

    return resultado


# --- Balance y PyG ---

def clasificar_balance_pgc(codigo):
    """Clasifica una subcuenta del PGC en linea de balance abreviado."""
    if not codigo or len(codigo) < 2:
        return None, None, None

    g1 = codigo[0]
    g2 = codigo[:2]
    g3 = codigo[:3] if len(codigo) >= 3 else g2 + "0"

    # Grupos 6-9 no van al balance
    if g1 not in "12345":
        return None, None, None

    # === ACTIVO NO CORRIENTE (grupo 2) ===
    if g2 == "20":
        return "anc", "I. Inmovilizado intangible", "deudora"
    if g2 in ("21", "23", "27"):
        return "anc", "II. Inmovilizado material", "deudora"
    if g2 == "22":
        return "anc", "III. Inversiones inmobiliarias", "deudora"
    if g2 in ("24", "25", "26"):
        return "anc", "IV. Inversiones financieras LP", "deudora"
    if g2 == "28":
        return "anc", "   (Amortizacion acumulada)", "deudora"
    if g2 == "29":
        return "anc", "   (Deterioro de valor)", "deudora"

    # === ACTIVO CORRIENTE (grupos 3, parte 4, parte 5) ===
    if g1 == "3":
        return "ac", "I. Existencias", "deudora"
    if g2 in ("43", "44"):
        return "ac", "II. Deudores comerciales", "deudora"
    if g3 in ("460", "461", "462", "463", "464"):
        return "ac", "II. Deudores comerciales", "deudora"
    if g3 in ("470", "471", "472"):
        return "ac", "III. HP deudora", "deudora"
    if g3 == "480":
        return "ac", "IV. Periodificaciones CP", "deudora"
    if g2 in ("53", "54"):
        return "ac", "V. Inversiones financieras CP", "deudora"
    if g2 == "57":
        return "ac", "VI. Efectivo", "deudora"

    # === PATRIMONIO NETO (grupo 1: 10x-13x) ===
    if g2 == "10":
        return "pn", "I. Capital", "acreedora"
    if g2 == "11":
        return "pn", "II. Reservas", "acreedora"
    if g2 == "12":
        return "pn", "III. Resultados ejercicios anteriores", "acreedora"
    if g2 == "13":
        return "pn", "IV. Subvenciones y donaciones", "acreedora"

    # === PASIVO NO CORRIENTE (grupo 1: 14x-17x) ===
    if g2 in ("14", "15"):
        return "pnc", "I. Provisiones LP", "acreedora"
    if g2 in ("16", "17"):
        return "pnc", "II. Deudas LP", "acreedora"

    # === PASIVO CORRIENTE (parte 4, parte 5) ===
    if g2 == "40":
        return "pc", "I. Proveedores", "acreedora"
    if g2 == "41":
        return "pc", "II. Acreedores varios", "acreedora"
    if g3 in ("465", "466"):
        return "pc", "III. Remuneraciones pendientes", "acreedora"
    if g3 in ("475", "476", "477"):
        return "pc", "IV. HP acreedora", "acreedora"
    if g3 == "485":
        return "pc", "V. Ingresos anticipados", "acreedora"
    if g2 in ("50", "51", "52"):
        return "pc", "VI. Deudas CP", "acreedora"
    if g2 in ("55", "56"):
        return "pc", "VI. Deudas CP", "acreedora"

    # Fallback para grupo 4/5 no clasificado: por signo del saldo
    if g1 in ("4", "5"):
        return "mixto", "Otros", None

    return None, None, None


def calcular_balance(subcuentas, resultado_ejercicio=0.0):
    """Balance de Situacion PGC abreviado.

    Incluye el resultado del ejercicio (suma grupos 6 y 7 invertida) en Patrimonio Neto.
    """
    lineas = {
        "anc": defaultdict(float),
        "ac": defaultdict(float),
        "pn": defaultdict(float),
        "pnc": defaultdict(float),
        "pc": defaultdict(float),
    }

    for sc in subcuentas:
        codigo = sc.get("codsubcuenta", "")
        saldo = float(sc.get("saldo", 0))
        debe = float(sc.get("debe", 0))
        haber = float(sc.get("haber", 0))

        if debe == 0 and haber == 0:
            continue

        seccion, linea, naturaleza = clasificar_balance_pgc(codigo)

        if seccion is None:
            continue

        if seccion == "mixto":
            if saldo > 0:
                lineas["ac"]["VII. Otros activos corrientes"] += saldo
            elif saldo < 0:
                lineas["pc"]["VII. Otros pasivos corrientes"] += abs(saldo)
            continue

        if naturaleza == "deudora":
            lineas[seccion][linea] += saldo
        else:
            lineas[seccion][linea] += -saldo

    # Anadir resultado del ejercicio a Patrimonio Neto
    if abs(resultado_ejercicio) >= 0.01:
        lineas["pn"]["V. Resultado del ejercicio"] += resultado_ejercicio

    # Totales por seccion
    total_anc = sum(lineas["anc"].values())
    total_ac = sum(lineas["ac"].values())
    total_pn = sum(lineas["pn"].values())
    total_pnc = sum(lineas["pnc"].values())
    total_pc = sum(lineas["pc"].values())

    total_activo = total_anc + total_ac
    total_pasivo = total_pn + total_pnc + total_pc

    return {
        "lineas": dict(lineas),
        "total_anc": total_anc,
        "total_ac": total_ac,
        "total_activo": total_activo,
        "total_pn": total_pn,
        "total_pnc": total_pnc,
        "total_pc": total_pc,
        "total_pasivo": total_pasivo,
        "cuadra": abs(total_activo - total_pasivo) < 0.01,
    }


def calcular_pyg(subcuentas):
    """Cuenta de Perdidas y Ganancias PGC abreviado."""
    partidas = defaultdict(float)

    for sc in subcuentas:
        codigo = sc.get("codsubcuenta", "")
        debe = float(sc.get("debe", 0))
        haber = float(sc.get("haber", 0))

        if debe == 0 and haber == 0:
            continue

        g1 = codigo[0] if codigo else ""
        g2 = codigo[:2] if len(codigo) >= 2 else ""
        g3 = codigo[:3] if len(codigo) >= 3 else ""

        if g1 == "7":
            importe = haber - debe  # Ingresos: saldo acreedor
            if g2 == "70":
                partidas["cifra_negocios"] += importe
            elif g2 == "71":
                partidas["variacion_existencias"] += importe
            elif g2 == "73":
                partidas["trabajos_activo"] += importe
            elif g2 in ("74", "75"):
                partidas["otros_ingresos_expl"] += importe
            elif g2 in ("76", "77"):
                partidas["ingresos_financieros"] += importe
            elif g2 == "79":
                partidas["otros_resultados"] += importe

        elif g1 == "6":
            importe = debe - haber  # Gastos: saldo deudor
            if g2 in ("60", "61"):
                partidas["aprovisionamientos"] += importe
            elif g2 == "64":
                partidas["gastos_personal"] += importe
            elif g2 == "62":
                partidas["otros_gastos_expl"] += importe
            elif g2 == "63":
                if g3 in ("630", "633"):
                    partidas["impuesto_beneficios"] += importe
                else:
                    partidas["otros_gastos_expl"] += importe
            elif g2 == "65":
                partidas["otros_gastos_expl"] += importe
            elif g2 == "68":
                partidas["amortizacion"] += importe
            elif g2 in ("66", "67"):
                partidas["gastos_financieros"] += importe
            elif g2 == "69":
                partidas["otros_resultados"] += importe

    resultado_explotacion = (
        partidas["cifra_negocios"]
        + partidas["variacion_existencias"]
        + partidas["trabajos_activo"]
        + partidas["otros_ingresos_expl"]
        - partidas["aprovisionamientos"]
        - partidas["gastos_personal"]
        - partidas["otros_gastos_expl"]
        - partidas["amortizacion"]
        + partidas["otros_resultados"]
    )

    resultado_financiero = (
        partidas["ingresos_financieros"]
        - partidas["gastos_financieros"]
    )

    resultado_antes_impuestos = resultado_explotacion + resultado_financiero

    if partidas["impuesto_beneficios"] > 0:
        impuesto = partidas["impuesto_beneficios"]
        impuesto_estimado = False
    else:
        impuesto = max(resultado_antes_impuestos * 0.25, 0)
        impuesto_estimado = True

    resultado_neto = resultado_antes_impuestos - impuesto

    return {
        "partidas": dict(partidas),
        "resultado_explotacion": resultado_explotacion,
        "resultado_financiero": resultado_financiero,
        "resultado_antes_impuestos": resultado_antes_impuestos,
        "impuesto": impuesto,
        "impuesto_estimado": impuesto_estimado,
        "resultado_neto": resultado_neto,
    }


# --- Generacion de archivos .txt ---

def generar_modelo_303_txt(datos, trimestre, ejercicio, empresa_nombre):
    """Genera texto del modelo 303 para un trimestre."""
    lineas = []
    lineas.append("=" * 64)
    lineas.append(f"  MODELO 303 - IVA TRIMESTRAL ({trimestre} {ejercicio})")
    lineas.append(f"  {empresa_nombre}")
    lineas.append("=" * 64)

    if datos["num_fact_emitidas"] == 0 and datos["num_fact_recibidas"] == 0:
        lineas.append("")
        lineas.append("  *** PROVISIONAL - datos parciales (0 facturas) ***")

    lineas.append("")
    lineas.append(f"  Facturas emitidas:    {datos['num_fact_emitidas']}")
    lineas.append(f"  Facturas recibidas:   {datos['num_fact_recibidas']}")

    # IVA DEVENGADO
    lineas.append("")
    lineas.append("  " + "-" * 50)
    lineas.append("  IVA DEVENGADO")
    lineas.append("  " + "-" * 50)
    lineas.append("")
    lineas.append("  Regimen general:")

    # Desglose repercutido por tipo
    for tipo_iva in sorted(datos["desglose_repercutido"].keys(),
                           key=lambda x: float(x.replace("%", ""))):
        d = datos["desglose_repercutido"][tipo_iva]
        lineas.append(f"    {tipo_iva:>5}  Base: {eur(d['base'])}   IVA: {eur(d['iva'])}")

    lineas.append(f"    {'TOTAL':>5}  Base: {eur(datos['base_ventas'])}   IVA: {eur(datos['iva_repercutido'])}")

    # Intracomunitarias
    if datos["base_intracom"] > 0:
        lineas.append("")
        lineas.append("  Adquisiciones intracomunitarias (casillas 10-11):")
        lineas.append(f"    Base:   {eur(datos['base_intracom'])}")
        lineas.append(f"    IVA 21%:{eur(datos['iva_intracom'])}")

    lineas.append("")
    total_devengado = datos["iva_repercutido"] + datos["iva_intracom"]
    lineas.append(f"  TOTAL IVA DEVENGADO:        {eur(total_devengado)}")

    # IVA DEDUCIBLE
    lineas.append("")
    lineas.append("  " + "-" * 50)
    lineas.append("  IVA DEDUCIBLE")
    lineas.append("  " + "-" * 50)
    lineas.append("")
    lineas.append("  Operaciones interiores:")

    for tipo_iva in sorted(datos["desglose_soportado"].keys(),
                           key=lambda x: float(x.replace("%", ""))):
        d = datos["desglose_soportado"][tipo_iva]
        lineas.append(f"    {tipo_iva:>5}  Base: {eur(d['base'])}   IVA: {eur(d['iva'])}")

    lineas.append(f"    {'TOTAL':>5}  Base: {eur(datos['base_compras'])}   IVA: {eur(datos['iva_soportado'])}")

    if datos["base_intracom"] > 0:
        lineas.append("")
        lineas.append("  Adquisiciones intracomunitarias (casillas 36-37):")
        lineas.append(f"    Base:   {eur(datos['base_intracom'])}")
        lineas.append(f"    IVA 21%:{eur(datos['iva_intracom'])}")

    lineas.append("")
    total_deducible = datos["iva_soportado"] + datos["iva_intracom"]
    lineas.append(f"  TOTAL IVA DEDUCIBLE:        {eur(total_deducible)}")

    # RESULTADO
    lineas.append("")
    lineas.append("  " + "=" * 50)
    lineas.append(f"  RESULTADO (devengado - deducible): {eur(datos['resultado'])}")
    if datos["a_ingresar"] > 0:
        lineas.append(f"  >> A INGRESAR:                     {eur(datos['a_ingresar'])}")
    if datos["a_compensar"] > 0:
        lineas.append(f"  >> A COMPENSAR:                    {eur(datos['a_compensar'])}")
    lineas.append("  " + "=" * 50)

    return "\n".join(lineas)


def generar_modelo_349_txt(operaciones, trimestre, ejercicio, empresa_nombre):
    """Genera texto del modelo 349 para un trimestre."""
    lineas = []
    lineas.append("=" * 64)
    lineas.append(f"  MODELO 349 - OPERACIONES INTRACOMUNITARIAS ({trimestre} {ejercicio})")
    lineas.append(f"  {empresa_nombre}")
    lineas.append("=" * 64)

    if not operaciones:
        lineas.append("")
        lineas.append("  Sin operaciones intracomunitarias en este trimestre.")
        return "\n".join(lineas)

    lineas.append("")
    lineas.append(f"  {'NIF-IVA':<20} {'Nombre':<25} {'Pais':<5} {'Tipo':<5} {'Base imponible':>15}")
    lineas.append("  " + "-" * 72)

    total = 0.0
    for _, op in sorted(operaciones.items(), key=lambda x: x[1]["nombre"]):
        tipo_op = "A"  # A = adquisicion de servicios/bienes
        lineas.append(
            f"  {op['cifnif']:<20} {op['nombre'][:25]:<25} {op['pais']:<5} {tipo_op:<5} {eur(op['base'])}"
        )
        total += op["base"]

    lineas.append("  " + "-" * 72)
    lineas.append(f"  {'TOTAL':<55} {eur(total)}")

    return "\n".join(lineas)


def generar_modelo_347_txt(operaciones, ejercicio, empresa_nombre):
    """Genera texto del modelo 347 (anual)."""
    lineas = []
    lineas.append("=" * 64)
    lineas.append(f"  MODELO 347 - OPERACIONES CON TERCEROS ({ejercicio})")
    lineas.append(f"  {empresa_nombre}")
    lineas.append(f"  Umbral: {eur_simple(UMBRAL_347)}")
    lineas.append("=" * 64)

    if not operaciones:
        lineas.append("")
        lineas.append("  Sin operaciones que superen el umbral.")
        return "\n".join(lineas)

    lineas.append("")
    lineas.append(f"  {'CIF':<20} {'Nombre':<25} {'Tipo':<5} {'Total':>15}")
    lineas.append("  " + "-" * 67)

    total_compras = 0.0
    total_ventas = 0.0

    for clave, op in sorted(operaciones.items(), key=lambda x: x[1]["total"], reverse=True):
        cif_display = clave.replace("_V", "")
        lineas.append(
            f"  {cif_display:<20} {op['nombre'][:25]:<25} {op['tipo']:<5} {eur(op['total'])}"
        )
        if op["tipo"] == "B":
            total_compras += op["total"]
        else:
            total_ventas += op["total"]

    lineas.append("  " + "-" * 67)
    lineas.append(f"  Total compras (B):{'':>35} {eur(total_compras)}")
    lineas.append(f"  Total ventas (A): {'':>35} {eur(total_ventas)}")

    return "\n".join(lineas)


def generar_modelo_390_txt(datos_303_trimestrales, ejercicio, empresa_nombre):
    """Genera texto del modelo 390 (resumen anual IVA)."""
    lineas = []
    lineas.append("=" * 64)
    lineas.append(f"  MODELO 390 - RESUMEN ANUAL IVA ({ejercicio})")
    lineas.append(f"  {empresa_nombre}")
    lineas.append("=" * 64)

    # Acumular desglose por tipo de IVA
    desglose_rep_total = defaultdict(lambda: {"base": 0.0, "iva": 0.0})
    desglose_sop_total = defaultdict(lambda: {"base": 0.0, "iva": 0.0})
    total_rep = 0.0
    total_sop = 0.0
    total_base_ventas = 0.0
    total_base_compras = 0.0
    base_intracom_total = 0.0
    iva_intracom_total = 0.0

    # Resumen por trimestre
    lineas.append("")
    lineas.append("  DESGLOSE POR TRIMESTRES")
    lineas.append("  " + "-" * 50)
    lineas.append(f"  {'Trim.':<6} {'Repercutido':>14} {'Soportado':>14} {'Resultado':>14}")
    lineas.append("  " + "-" * 50)

    for trim in ["T1", "T2", "T3", "T4"]:
        d = datos_303_trimestrales[trim]
        lineas.append(
            f"  {trim:<6} {eur(d['iva_repercutido'])} {eur(d['iva_soportado'])} {eur(d['resultado'])}"
        )
        total_rep += d["iva_repercutido"]
        total_sop += d["iva_soportado"]
        total_base_ventas += d["base_ventas"]
        total_base_compras += d["base_compras"]
        base_intracom_total += d["base_intracom"]
        iva_intracom_total += d["iva_intracom"]

        for tipo, vals in d["desglose_repercutido"].items():
            desglose_rep_total[tipo]["base"] += vals["base"]
            desglose_rep_total[tipo]["iva"] += vals["iva"]

        for tipo, vals in d["desglose_soportado"].items():
            desglose_sop_total[tipo]["base"] += vals["base"]
            desglose_sop_total[tipo]["iva"] += vals["iva"]

    resultado_anual = total_rep + iva_intracom_total - total_sop - iva_intracom_total
    lineas.append("  " + "-" * 50)
    lineas.append(
        f"  {'TOTAL':<6} {eur(total_rep)} {eur(total_sop)} {eur(resultado_anual)}"
    )

    # Desglose acumulado por tipo IVA
    lineas.append("")
    lineas.append("  " + "=" * 50)
    lineas.append("  DESGLOSE ANUAL POR TIPO DE IVA")
    lineas.append("  " + "-" * 50)

    lineas.append("")
    lineas.append("  IVA REPERCUTIDO:")
    for tipo in sorted(desglose_rep_total.keys(), key=lambda x: float(x.replace("%", ""))):
        d = desglose_rep_total[tipo]
        lineas.append(f"    {tipo:>5}  Base: {eur(d['base'])}   IVA: {eur(d['iva'])}")
    lineas.append(f"    {'TOTAL':>5}  Base: {eur(total_base_ventas)}   IVA: {eur(total_rep)}")

    lineas.append("")
    lineas.append("  IVA SOPORTADO:")
    for tipo in sorted(desglose_sop_total.keys(), key=lambda x: float(x.replace("%", ""))):
        d = desglose_sop_total[tipo]
        lineas.append(f"    {tipo:>5}  Base: {eur(d['base'])}   IVA: {eur(d['iva'])}")
    lineas.append(f"    {'TOTAL':>5}  Base: {eur(total_base_compras)}   IVA: {eur(total_sop)}")

    if base_intracom_total > 0:
        lineas.append("")
        lineas.append("  OPERACIONES INTRACOMUNITARIAS:")
        lineas.append(f"    Base:    {eur(base_intracom_total)}")
        lineas.append(f"    IVA 21%: {eur(iva_intracom_total)}")

    lineas.append("")
    lineas.append("  " + "=" * 50)
    lineas.append(f"  RESULTADO ANUAL:  {eur(resultado_anual)}")
    if resultado_anual > 0:
        lineas.append(f"  >> A INGRESAR:    {eur(resultado_anual)}")
    elif resultado_anual < 0:
        lineas.append(f"  >> A COMPENSAR:   {eur(abs(resultado_anual))}")
    lineas.append("  " + "=" * 50)

    return "\n".join(lineas)


def generar_balance_txt(datos, ejercicio, empresa_nombre):
    """Genera texto del balance de situacion."""
    lineas_out = []
    lineas_out.append("=" * 64)
    lineas_out.append(f"  BALANCE DE SITUACION PROVISIONAL (31/12/{ejercicio})")
    lineas_out.append(f"  {empresa_nombre}")
    lineas_out.append("=" * 64)

    det = datos["lineas"]

    # ACTIVO
    lineas_out.append("")
    lineas_out.append(f"  A) ACTIVO NO CORRIENTE               {eur(datos['total_anc'])}")
    for linea, importe in sorted(det.get("anc", {}).items()):
        if abs(importe) >= 0.01:
            lineas_out.append(f"      {linea:<38} {eur(importe)}")

    lineas_out.append(f"  B) ACTIVO CORRIENTE                   {eur(datos['total_ac'])}")
    for linea, importe in sorted(det.get("ac", {}).items()):
        if abs(importe) >= 0.01:
            lineas_out.append(f"      {linea:<38} {eur(importe)}")

    lineas_out.append("    " + "-" * 50)
    lineas_out.append(f"    TOTAL ACTIVO                        {eur(datos['total_activo'])}")

    # PATRIMONIO NETO Y PASIVO
    lineas_out.append("")
    lineas_out.append(f"  A) PATRIMONIO NETO                    {eur(datos['total_pn'])}")
    for linea, importe in sorted(det.get("pn", {}).items()):
        if abs(importe) >= 0.01:
            lineas_out.append(f"      {linea:<38} {eur(importe)}")

    lineas_out.append(f"  B) PASIVO NO CORRIENTE                {eur(datos['total_pnc'])}")
    for linea, importe in sorted(det.get("pnc", {}).items()):
        if abs(importe) >= 0.01:
            lineas_out.append(f"      {linea:<38} {eur(importe)}")

    lineas_out.append(f"  C) PASIVO CORRIENTE                   {eur(datos['total_pc'])}")
    for linea, importe in sorted(det.get("pc", {}).items()):
        if abs(importe) >= 0.01:
            lineas_out.append(f"      {linea:<38} {eur(importe)}")

    lineas_out.append("    " + "-" * 50)
    lineas_out.append(f"    TOTAL PN + PASIVO                   {eur(datos['total_pasivo'])}")

    lineas_out.append("")
    estado = "CUADRA" if datos["cuadra"] else "NO CUADRA - revisar asientos"
    lineas_out.append(f"  Verificacion: {estado}")
    diff = datos["total_activo"] - datos["total_pasivo"]
    if abs(diff) >= 0.01:
        lineas_out.append(f"  Diferencia: {eur(diff)}")

    return "\n".join(lineas_out)


def generar_pyg_txt(datos, ejercicio, empresa_nombre):
    """Genera texto de la cuenta de PyG."""
    lineas = []
    lineas.append("=" * 64)
    lineas.append(f"  CUENTA DE PERDIDAS Y GANANCIAS PROVISIONAL ({ejercicio})")
    lineas.append(f"  {empresa_nombre}")
    lineas.append("=" * 64)

    p = datos["partidas"]

    lineas.append("")
    lineas.append(f"   1. Cifra de negocios              {eur(p.get('cifra_negocios', 0))}")
    if p.get("variacion_existencias", 0):
        lineas.append(f"   2. Variacion de existencias       {eur(p['variacion_existencias'])}")
    if p.get("trabajos_activo", 0):
        lineas.append(f"   3. Trabajos para el activo        {eur(p['trabajos_activo'])}")
    lineas.append(f"   4. Aprovisionamientos            -{eur(p.get('aprovisionamientos', 0))}")
    if p.get("otros_ingresos_expl", 0):
        lineas.append(f"   5. Otros ingresos explotacion     {eur(p['otros_ingresos_expl'])}")
    lineas.append(f"   6. Gastos de personal            -{eur(p.get('gastos_personal', 0))}")
    lineas.append(f"   7. Otros gastos de explotacion   -{eur(p.get('otros_gastos_expl', 0))}")
    lineas.append(f"   8. Amortizacion del inmovilizado -{eur(p.get('amortizacion', 0))}")
    if p.get("otros_resultados", 0):
        lineas.append(f"   9. Otros resultados               {eur(p['otros_resultados'])}")

    lineas.append("  " + "-" * 50)
    lineas.append(f"  A) RESULTADO DE EXPLOTACION        {eur(datos['resultado_explotacion'])}")

    lineas.append("")
    lineas.append(f"  10. Ingresos financieros           {eur(p.get('ingresos_financieros', 0))}")
    lineas.append(f"  11. Gastos financieros            -{eur(p.get('gastos_financieros', 0))}")

    lineas.append("  " + "-" * 50)
    lineas.append(f"  B) RESULTADO FINANCIERO            {eur(datos['resultado_financiero'])}")

    lineas.append("  " + "-" * 50)
    lineas.append(f"  C) RESULTADO ANTES DE IMPUESTOS    {eur(datos['resultado_antes_impuestos'])}")

    etiqueta = "Imp. Sociedades (est. 25%)" if datos["impuesto_estimado"] else "Impuesto sobre beneficios"
    lineas.append(f"  17. {etiqueta:<32}-{eur(datos['impuesto'])}")

    lineas.append("  " + "=" * 50)
    lineas.append(f"  D) RESULTADO DEL EJERCICIO         {eur(datos['resultado_neto'])}")

    return "\n".join(lineas)


def generar_resumen_txt(datos_303, datos_349, datos_347, datos_390,
                        datos_balance, datos_pyg, ejercicio, empresa_nombre):
    """Genera resumen general de todos los modelos."""
    lineas = []
    lineas.append("#" * 64)
    lineas.append(f"  RESUMEN GENERAL DE MODELOS FISCALES ({ejercicio})")
    lineas.append(f"  {empresa_nombre}")
    lineas.append(f"  Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    lineas.append("#" * 64)

    # Modelo 303 por trimestre
    lineas.append("")
    lineas.append("=" * 64)
    lineas.append("  MODELO 303 - IVA (resumen trimestral)")
    lineas.append("=" * 64)
    lineas.append(f"  {'Trim.':<6} {'Repercut.':>14} {'Soportado':>14} {'Resultado':>14}")
    lineas.append("  " + "-" * 50)

    total_resultado_303 = 0.0
    for trim in ["T1", "T2", "T3", "T4"]:
        d = datos_303[trim]
        nota = " *" if d["num_fact_emitidas"] == 0 and d["num_fact_recibidas"] == 0 else ""
        lineas.append(
            f"  {trim + nota:<6} {eur(d['iva_repercutido'])} {eur(d['iva_soportado'])} {eur(d['resultado'])}"
        )
        total_resultado_303 += d["resultado"]

    lineas.append("  " + "-" * 50)
    lineas.append(f"  {'ANUAL':<6} {'':>14} {'':>14} {eur(total_resultado_303)}")
    lineas.append("  (* = sin facturas, datos parciales)")

    # Modelo 349
    lineas.append("")
    lineas.append("=" * 64)
    lineas.append("  MODELO 349 - OPERACIONES INTRACOMUNITARIAS (resumen)")
    lineas.append("=" * 64)
    for trim in ["T1", "T2", "T3", "T4"]:
        ops = datos_349[trim]
        if ops:
            total_trim = sum(op["base"] for op in ops.values())
            lineas.append(f"  {trim}: {len(ops)} proveedor(es), base total: {eur(total_trim)}")
        else:
            lineas.append(f"  {trim}: Sin operaciones")

    # Modelo 347
    lineas.append("")
    lineas.append("=" * 64)
    lineas.append("  MODELO 347 - OPERACIONES CON TERCEROS (resumen)")
    lineas.append("=" * 64)
    lineas.append(f"  Terceros que superan {eur_simple(UMBRAL_347)}: {len(datos_347)}")
    for clave, op in sorted(datos_347.items(), key=lambda x: x[1]["total"], reverse=True):
        cif_display = clave.replace("_V", "")
        lineas.append(f"    {cif_display:<20} {op['nombre'][:30]:<30} {op['tipo']} {eur(op['total'])}")

    # Balance y PyG
    if datos_balance:
        lineas.append("")
        lineas.append("=" * 64)
        lineas.append("  BALANCE Y PyG (resumen)")
        lineas.append("=" * 64)
        lineas.append(f"  Total Activo:           {eur(datos_balance['total_activo'])}")
        lineas.append(f"  Total PN + Pasivo:      {eur(datos_balance['total_pasivo'])}")
        estado = "SI" if datos_balance["cuadra"] else "NO"
        lineas.append(f"  Cuadra: {estado}")

    if datos_pyg:
        lineas.append(f"  Resultado explotacion:  {eur(datos_pyg['resultado_explotacion'])}")
        lineas.append(f"  Resultado neto:         {eur(datos_pyg['resultado_neto'])}")
        if datos_pyg["impuesto_estimado"]:
            lineas.append(f"  (Imp. Sociedades estimado al 25%)")

    lineas.append("")
    lineas.append("#" * 64)
    lineas.append("  AVISO: Datos PROVISIONALES basados en la contabilidad")
    lineas.append("  registrada hasta la fecha. Para modelos fiscales oficiales")
    lineas.append("  usar FacturaScripts > Informes > Modelo correspondiente.")
    lineas.append("#" * 64)

    return "\n".join(lineas)


# --- Construccion del mapa de contactos ---

def construir_mapa_contactos(contactos):
    """Construye un diccionario codproveedor -> datos del contacto."""
    mapa = {}
    for c in contactos:
        codproveedor = str(c.get("codproveedor", ""))
        if codproveedor:
            mapa[codproveedor] = c
    return mapa


# --- Main ---

def main():
    parser = argparse.ArgumentParser(
        description="Genera modelos fiscales desde FacturaScripts",
    )
    parser.add_argument(
        "carpeta_cliente", type=str,
        help="Ruta relativa a la carpeta del cliente (ej: clientes/pastorino-costa-del-sol)",
    )
    parser.add_argument(
        "--ejercicio", type=str, default="2025",
        help="Ejercicio fiscal (default: 2025)",
    )
    parser.add_argument(
        "--empresa", type=int, default=1,
        help="ID empresa en FacturaScripts (default: 1)",
    )
    args = parser.parse_args()

    # Token API
    token = os.environ.get("FS_API_TOKEN", TOKEN_FALLBACK)

    # Validar empresa
    empresa = EMPRESAS.get(args.empresa)
    if not empresa:
        print(f"Error: Empresa {args.empresa} no registrada")
        sys.exit(1)

    ejercicio = args.ejercicio
    empresa_nombre = empresa["nombre"]

    # Determinar carpeta de salida
    # El script se ejecuta desde la raiz del proyecto CONTABILIDAD
    script_dir = Path(__file__).resolve().parent
    proyecto_dir = script_dir.parent
    carpeta_cliente = proyecto_dir / args.carpeta_cliente
    carpeta_salida = carpeta_cliente / ejercicio / "modelos_fiscales"

    if not carpeta_cliente.exists():
        print(f"Error: Carpeta del cliente no existe: {carpeta_cliente}")
        sys.exit(1)

    carpeta_salida.mkdir(parents=True, exist_ok=True)

    print(f"  Generando modelos fiscales para {empresa_nombre}")
    print(f"  Ejercicio: {ejercicio}")
    print(f"  Salida: {carpeta_salida}")
    print()

    # --- Obtener datos de la API ---
    print("  Consultando API de FacturaScripts...")

    # Facturas del ejercicio completo (filtraremos por trimestre despues)
    todas_fact_clientes = obtener_facturas_cliente(token, args.empresa, ejercicio)
    todas_fact_proveedores = obtener_facturas_proveedor(token, args.empresa, ejercicio)
    contactos = obtener_contactos(token)
    contactos_map = construir_mapa_contactos(contactos)

    # Cargar TODAS las lineas de factura de una sola vez (la API ignora filtros por idfactura)
    todas_lineas_cli = obtener_todas_lineas_factura_cliente(token)
    todas_lineas_prov = obtener_todas_lineas_factura_proveedor(token)

    print(f"  - {len(todas_fact_clientes)} facturas emitidas")
    print(f"  - {len(todas_fact_proveedores)} facturas recibidas")
    print(f"  - {len(contactos)} contactos")
    print(f"  - {len(todas_lineas_cli)} lineas factura cliente")
    print(f"  - {len(todas_lineas_prov)} lineas factura proveedor")

    # --- Calcular modelos por trimestre ---
    datos_303 = {}
    datos_349 = {}

    for trim in ["T1", "T2", "T3", "T4"]:
        print(f"  Procesando {trim}...")

        # Filtrar facturas del trimestre
        fact_cli_trim = filtrar_por_fecha(todas_fact_clientes, "fecha", ejercicio, trim)
        fact_prov_trim = filtrar_por_fecha(todas_fact_proveedores, "fecha", ejercicio, trim)

        # Modelo 303
        datos_303[trim] = calcular_modelo_303(
            fact_cli_trim, fact_prov_trim, contactos_map,
            todas_lineas_cli, todas_lineas_prov,
        )

        # Modelo 349
        datos_349[trim] = calcular_modelo_349(fact_prov_trim, contactos_map)

    # Modelo 347 (anual)
    datos_347 = calcular_modelo_347(
        todas_fact_clientes, todas_fact_proveedores, contactos_map
    )

    # Balance y PyG (solo S.L.)
    datos_balance = None
    datos_pyg = None

    if empresa["tipo"] == "sl":
        print("  Consultando subcuentas contables...")
        subcuentas = obtener_subcuentas(token, args.empresa, ejercicio)
        con_movimientos = [
            sc for sc in subcuentas
            if float(sc.get("debe", 0)) != 0 or float(sc.get("haber", 0)) != 0
        ]
        print(f"  - {len(con_movimientos)} subcuentas con movimientos")

        # Calcular PyG primero para obtener resultado del ejercicio
        datos_pyg = calcular_pyg(con_movimientos)

        # Calcular balance incluyendo resultado del ejercicio en PN
        datos_balance = calcular_balance(con_movimientos, datos_pyg["resultado_neto"])

    # --- Escribir archivos ---
    print()
    print("  Escribiendo archivos...")

    archivos_generados = []

    # Modelo 303 por trimestre
    for trim in ["T1", "T2", "T3", "T4"]:
        ruta = carpeta_salida / f"modelo_303_{trim}.txt"
        contenido = generar_modelo_303_txt(datos_303[trim], trim, ejercicio, empresa_nombre)
        ruta.write_text(contenido, encoding="utf-8")
        archivos_generados.append(ruta.name)

    # Modelo 349 por trimestre
    for trim in ["T1", "T2", "T3", "T4"]:
        ruta = carpeta_salida / f"modelo_349_{trim}.txt"
        contenido = generar_modelo_349_txt(datos_349[trim], trim, ejercicio, empresa_nombre)
        ruta.write_text(contenido, encoding="utf-8")
        archivos_generados.append(ruta.name)

    # Modelo 347 anual
    ruta = carpeta_salida / "modelo_347_anual.txt"
    contenido = generar_modelo_347_txt(datos_347, ejercicio, empresa_nombre)
    ruta.write_text(contenido, encoding="utf-8")
    archivos_generados.append(ruta.name)

    # Modelo 390 anual
    ruta = carpeta_salida / "modelo_390_anual.txt"
    contenido = generar_modelo_390_txt(datos_303, ejercicio, empresa_nombre)
    ruta.write_text(contenido, encoding="utf-8")
    archivos_generados.append(ruta.name)

    # Balance de Situacion
    if datos_balance:
        ruta = carpeta_salida / "balance_situacion.txt"
        contenido = generar_balance_txt(datos_balance, ejercicio, empresa_nombre)
        ruta.write_text(contenido, encoding="utf-8")
        archivos_generados.append(ruta.name)

    # Cuenta de PyG
    if datos_pyg:
        ruta = carpeta_salida / "cuenta_pyg.txt"
        contenido = generar_pyg_txt(datos_pyg, ejercicio, empresa_nombre)
        ruta.write_text(contenido, encoding="utf-8")
        archivos_generados.append(ruta.name)

    # Resumen general
    ruta = carpeta_salida / "resumen_general.txt"
    contenido = generar_resumen_txt(
        datos_303, datos_349, datos_347, None,
        datos_balance, datos_pyg, ejercicio, empresa_nombre,
    )
    ruta.write_text(contenido, encoding="utf-8")
    archivos_generados.append(ruta.name)

    # --- Resultado ---
    print()
    print(f"  {len(archivos_generados)} archivos generados en {carpeta_salida}:")
    for nombre in archivos_generados:
        print(f"    - {nombre}")

    print()
    print("  AVISO: Datos PROVISIONALES. Para modelos oficiales usar FacturaScripts.")


if __name__ == "__main__":
    main()
