"""
Resumen fiscal on-demand desde la API de FacturaScripts.

Consulta facturas y subcuentas contables para generar:
- Autonomos: Modelo 303 (IVA), Modelo 130 (IRPF), Modelo 111 (Retenciones)
- Sociedades: Modelo 303, Modelo 111, Balance de Situacion, Cuenta de PyG

Uso:
  export FS_API_TOKEN='tu_token_aqui'
  python resumen_fiscal.py --empresa 2 --trimestre T1
  python resumen_fiscal.py --empresa 1 --ejercicio 2025
"""

import requests
import os
import sys
import argparse
from datetime import datetime
from collections import defaultdict


# --- Configuracion ---

API_BASE = os.environ.get(
    "FS_API_URL",
    "https://contabilidad.lemonfresh-tuc.com/api/3",
)

TRIMESTRES = {
    "T1": ("01-01", "03-31"),
    "T2": ("04-01", "06-30"),
    "T3": ("07-01", "09-30"),
    "T4": ("10-01", "12-31"),
}

# Empresas registradas en FacturaScripts
EMPRESAS = {
    1: {"nombre": "PASTORINO COSTA DEL SOL S.L.", "tipo": "sl"},
    2: {"nombre": "G. GONZALEZ (Gerardo Gonzalez Callejon)", "tipo": "autonomo"},
}


# --- API ---

def api_get(token, endpoint, params=None):
    """GET a la API de FacturaScripts con paginacion automatica."""
    url = f"{API_BASE}/{endpoint}"
    todos = []
    params = dict(params or {})
    params.setdefault("limit", 50)
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


def normalizar_fecha(fecha_str):
    """Convierte fecha DD-MM-YYYY de FS a YYYY-MM-DD para comparacion."""
    if not fecha_str:
        return ""
    partes = fecha_str.split("-")
    if len(partes) == 3 and len(partes[0]) == 2:
        return f"{partes[2]}-{partes[1]}-{partes[0]}"
    return fecha_str


def filtrar_por_fecha(registros, campo_fecha, ejercicio, trimestre=None):
    """Filtra registros por rango de fechas."""
    if trimestre and trimestre in TRIMESTRES:
        inicio, fin = TRIMESTRES[trimestre]
        fecha_ini = f"{ejercicio}-{inicio}"
        fecha_fin = f"{ejercicio}-{fin}"
    else:
        fecha_ini = f"{ejercicio}-01-01"
        fecha_fin = f"{ejercicio}-12-31"

    return [
        r for r in registros
        if fecha_ini <= normalizar_fecha(r.get(campo_fecha) or "") <= fecha_fin
    ]


# --- Obtencion de datos ---

def convertir_a_eur(facturas):
    """Convierte campos monetarios de facturas USD (u otra divisa) a EUR."""
    for f in facturas:
        tc = float(f.get("tasaconv", 1) or 1)
        if f.get("coddivisa", "EUR") != "EUR" and tc > 0 and tc != 1:
            f["neto"] = round(float(f.get("neto", 0)) / tc, 2)
            f["totaliva"] = round(float(f.get("totaliva", 0)) / tc, 2)
            f["totalirpf"] = round(float(f.get("totalirpf", 0)) / tc, 2)
            f["total"] = round(float(f.get("total", 0)) / tc, 2)
    return facturas


def obtener_facturas_cliente(token, idempresa, ejercicio, trimestre=None):
    """Facturas emitidas (ventas/ingresos)."""
    facturas = api_get(token, "facturaclientes", {
        "idempresa": idempresa,
        "codejercicio": ejercicio,
    })
    facturas = filtrar_por_fecha(facturas, "fecha", ejercicio, trimestre)
    return convertir_a_eur(facturas)


def obtener_facturas_proveedor(token, idempresa, ejercicio, trimestre=None):
    """Facturas recibidas (compras/gastos)."""
    facturas = api_get(token, "facturaproveedores", {
        "idempresa": idempresa,
        "codejercicio": ejercicio,
    })
    facturas = filtrar_por_fecha(facturas, "fecha", ejercicio, trimestre)
    return convertir_a_eur(facturas)


def obtener_subcuentas(token, idempresa, ejercicio):
    """Subcuentas contables con saldos acumulados."""
    return api_get(token, "subcuentas", {
        "idempresa": idempresa,
        "codejercicio": ejercicio,
    })


# --- Modelos fiscales ---

def calcular_modelo_303(fact_clientes, fact_proveedores):
    """Modelo 303 - IVA trimestral.

    Calcula IVA repercutido (ventas) menos IVA soportado deducible (compras).
    Las facturas exentas (totaliva=0) se reportan como base exenta.
    """
    # Ventas
    base_ventas = sum(float(f.get("neto", 0)) for f in fact_clientes)
    iva_repercutido = sum(float(f.get("totaliva", 0)) for f in fact_clientes)
    base_exenta = sum(
        float(f.get("neto", 0)) for f in fact_clientes
        if float(f.get("totaliva", 0)) == 0
    )
    base_sujeta = base_ventas - base_exenta

    # Compras
    base_compras = sum(float(f.get("neto", 0)) for f in fact_proveedores)
    iva_soportado = sum(float(f.get("totaliva", 0)) for f in fact_proveedores)

    resultado = iva_repercutido - iva_soportado

    return {
        "base_ventas": base_ventas,
        "base_exenta": base_exenta,
        "base_sujeta": base_sujeta,
        "iva_repercutido": iva_repercutido,
        "base_compras": base_compras,
        "iva_soportado": iva_soportado,
        "resultado": resultado,
        "a_ingresar": max(resultado, 0),
        "a_compensar": abs(min(resultado, 0)),
        "num_facturas_emitidas": len(fact_clientes),
        "num_facturas_recibidas": len(fact_proveedores),
    }


def calcular_modelo_130(fact_clientes, fact_proveedores):
    """Modelo 130 - Pago fraccionado IRPF (solo autonomos).

    20% del rendimiento neto (ingresos - gastos) menos retenciones soportadas.
    """
    ingresos = sum(float(f.get("neto", 0)) for f in fact_clientes)
    gastos = sum(float(f.get("neto", 0)) for f in fact_proveedores)
    rendimiento_neto = ingresos - gastos

    # Retenciones que los clientes le han practicado al autonomo
    retenciones_soportadas = sum(
        abs(float(f.get("totalirpf", 0))) for f in fact_clientes
    )

    pago_bruto = rendimiento_neto * 0.20
    pago_neto = max(pago_bruto - retenciones_soportadas, 0)

    return {
        "ingresos": ingresos,
        "gastos": gastos,
        "rendimiento_neto": rendimiento_neto,
        "porcentaje": 20,
        "pago_bruto": pago_bruto,
        "retenciones_soportadas": retenciones_soportadas,
        "a_ingresar": pago_neto,
    }


def calcular_modelo_111(fact_proveedores):
    """Modelo 111 - Retenciones IRPF practicadas.

    Suma las retenciones en facturas de proveedores/profesionales.
    No incluye retenciones de nominas (requiere modulo RRHH).
    """
    facturas_con_irpf = [
        f for f in fact_proveedores
        if float(f.get("totalirpf", 0)) != 0
    ]

    total_retenciones = sum(
        abs(float(f.get("totalirpf", 0))) for f in facturas_con_irpf
    )
    base_retenciones = sum(
        float(f.get("neto", 0)) for f in facturas_con_irpf
    )

    return {
        "base_retenciones": base_retenciones,
        "retenciones": total_retenciones,
        "num_facturas": len(facturas_con_irpf),
        "nota": "No incluye retenciones de nominas (requiere modulo RRHH)",
    }


# --- Estados financieros (S.L.) ---

def clasificar_balance_pgc(codigo):
    """Clasifica una subcuenta del PGC en linea de balance abreviado.

    Retorna (seccion, linea, naturaleza):
    - seccion: 'anc', 'ac', 'pn', 'pnc', 'pc' o None
    - linea: nombre de la partida del balance PGC
    - naturaleza: 'deudora' (activo, usar saldo directo) o
                  'acreedora' (pasivo/PN, negar saldo para mostrar positivo)
    """
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
    if g2 in ("10",):
        return "pn", "I. Capital", "acreedora"
    if g2 in ("11",):
        return "pn", "II. Reservas", "acreedora"
    if g2 in ("12",):
        return "pn", "III. Resultados ejercicios anteriores", "acreedora"
    if g2 in ("13",):
        return "pn", "IV. Subvenciones y donaciones", "acreedora"

    # === PASIVO NO CORRIENTE (grupo 1: 14x-17x) ===
    if g2 in ("14", "15"):
        return "pnc", "I. Provisiones LP", "acreedora"
    if g2 in ("16", "17"):
        return "pnc", "II. Deudas LP", "acreedora"

    # === PASIVO CORRIENTE (parte 4, parte 5) ===
    if g2 in ("40",):
        return "pc", "I. Proveedores", "acreedora"
    if g2 in ("41",):
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


def calcular_balance(subcuentas):
    """Balance de Situacion PGC abreviado.

    Clasifica cada subcuenta en su linea del balance segun el PGC,
    agrupa por seccion (ANC, AC, PN, PNC, PC) y linea, y totaliza.

    Convenciones de saldo en FacturaScripts:
    - saldo = debe - haber
    - Cuentas deudoras (activo): saldo positivo = normal
    - Cuentas acreedoras (pasivo/PN): saldo negativo = normal
    - Para mostrar pasivo/PN como positivo: negar el saldo
    """
    # Diccionario: seccion -> {linea: importe}
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
            # Subcuentas sin clasificacion clara: por signo
            if saldo > 0:
                lineas["ac"]["VII. Otros activos corrientes"] += saldo
            elif saldo < 0:
                lineas["pc"]["VII. Otros pasivos corrientes"] += abs(saldo)
            continue

        if naturaleza == "deudora":
            lineas[seccion][linea] += saldo
        else:  # acreedora
            # Negar saldo para que se muestre positivo
            # (saldo acreedora es negativo en debe-haber)
            lineas[seccion][linea] += -saldo

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
    """Cuenta de Perdidas y Ganancias PGC abreviado.

    Estructura:
    1. Cifra de negocios (70x)
    2. Variacion de existencias (71x)
    3. Aprovisionamientos (60x)
    4. Gastos de personal (64x)
    5. Otros gastos de explotacion (62x, 63x, 65x)
    6. Amortizacion del inmovilizado (68x)
    7. Otros resultados (subvenciones, deterioros, enajenaciones)
    A) RESULTADO DE EXPLOTACION
    8. Ingresos financieros (76x)
    9. Gastos financieros (66x)
    10. Diferencias de cambio (768 - 668)
    B) RESULTADO FINANCIERO
    C) RESULTADO ANTES DE IMPUESTOS
    17. Impuesto sobre beneficios (630, 633)
    D) RESULTADO DEL EJERCICIO
    """
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
            if g2 in ("70",):
                partidas["cifra_negocios"] += importe
            elif g2 in ("71",):
                partidas["variacion_existencias"] += importe
            elif g2 in ("73",):
                partidas["trabajos_activo"] += importe
            elif g2 in ("74", "75"):
                partidas["otros_ingresos_expl"] += importe
            elif g2 in ("76", "77"):
                partidas["ingresos_financieros"] += importe
            elif g2 in ("79",):
                partidas["otros_resultados"] += importe

        elif g1 == "6":
            importe = debe - haber  # Gastos: saldo deudor (positivo = gasto)
            if g2 in ("60", "61"):
                partidas["aprovisionamientos"] += importe
            elif g2 in ("64",):
                partidas["gastos_personal"] += importe
            elif g2 in ("62",):
                partidas["otros_gastos_expl"] += importe
            elif g2 in ("63",):
                # 630/633 = Impuesto beneficios, resto = tributos
                if g3 in ("630", "633"):
                    partidas["impuesto_beneficios"] += importe
                else:
                    partidas["otros_gastos_expl"] += importe
            elif g2 in ("65",):
                partidas["otros_gastos_expl"] += importe
            elif g2 in ("68",):
                partidas["amortizacion"] += importe
            elif g2 in ("66", "67"):
                partidas["gastos_financieros"] += importe
            elif g2 in ("69",):
                partidas["otros_resultados"] += importe

    # Calcular resultado de explotacion
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

    # Resultado financiero
    resultado_financiero = (
        partidas["ingresos_financieros"]
        - partidas["gastos_financieros"]
    )

    resultado_antes_impuestos = resultado_explotacion + resultado_financiero

    # Impuesto: si hay 630/633 registrado, usar ese. Si no, estimar al 25%.
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


# --- Presentacion ---

def eur(valor):
    """Formatea un numero como moneda EUR."""
    return f"{valor:>12,.2f} EUR"


def separador(titulo=""):
    if titulo:
        print(f"\n{'=' * 64}")
        print(f"  {titulo}")
        print(f"{'=' * 64}")
    else:
        print(f"  {'-' * 50}")


def imprimir_303(datos):
    separador("MODELO 303 -IVA")
    print(f"  Facturas emitidas:         {datos['num_facturas_emitidas']}")
    print(f"  Facturas recibidas:        {datos['num_facturas_recibidas']}")
    separador()
    print(f"  VENTAS")
    print(f"    Base total ventas:       {eur(datos['base_ventas'])}")
    if datos["base_exenta"] > 0:
        print(f"    Base exenta (san.):      {eur(datos['base_exenta'])}")
    print(f"    Base sujeta a IVA:       {eur(datos['base_sujeta'])}")
    print(f"    IVA repercutido:         {eur(datos['iva_repercutido'])}")
    separador()
    print(f"  COMPRAS")
    print(f"    Base compras:            {eur(datos['base_compras'])}")
    print(f"    IVA soportado deducible: {eur(datos['iva_soportado'])}")
    separador()
    print(f"  RESULTADO 303:             {eur(datos['resultado'])}")
    if datos["a_ingresar"] > 0:
        print(f"  >> A ingresar en Hacienda:  {eur(datos['a_ingresar'])}")
    if datos["a_compensar"] > 0:
        print(f"  >> A compensar:             {eur(datos['a_compensar'])}")


def imprimir_130(datos):
    separador("MODELO 130 -PAGO FRACCIONADO IRPF")
    print(f"  Ingresos (neto):           {eur(datos['ingresos'])}")
    print(f"  Gastos (neto):            -{eur(datos['gastos'])}")
    print(f"  Rendimiento neto:          {eur(datos['rendimiento_neto'])}")
    separador()
    print(f"  Pago fraccionado (20%):    {eur(datos['pago_bruto'])}")
    print(f"  Retenciones soportadas:   -{eur(datos['retenciones_soportadas'])}")
    separador()
    print(f"  A INGRESAR:                {eur(datos['a_ingresar'])}")


def imprimir_111(datos):
    separador("MODELO 111 -RETENCIONES IRPF PRACTICADAS")
    print(f"  Facturas con retencion:    {datos['num_facturas']}")
    print(f"  Base retenciones:          {eur(datos['base_retenciones'])}")
    print(f"  Total retenciones:         {eur(datos['retenciones'])}")
    print(f"  ({datos['nota']})")


def _imprimir_lineas_seccion(lineas_seccion):
    """Imprime las lineas de detalle de una seccion del balance."""
    # Orden de las lineas PGC (por numero romano)
    for linea, importe in sorted(lineas_seccion.items()):
        if abs(importe) >= 0.01:
            print(f"      {linea:<38} {eur(importe)}")


def imprimir_balance(datos):
    separador("BALANCE DE SITUACION")
    lineas = datos["lineas"]

    # --- ACTIVO ---
    print()
    print(f"  A) ACTIVO NO CORRIENTE               {eur(datos['total_anc'])}")
    _imprimir_lineas_seccion(lineas.get("anc", {}))

    print(f"  B) ACTIVO CORRIENTE                   {eur(datos['total_ac'])}")
    _imprimir_lineas_seccion(lineas.get("ac", {}))

    print(f"    -------------------------------------------------")
    print(f"    TOTAL ACTIVO                        {eur(datos['total_activo'])}")

    # --- PATRIMONIO NETO Y PASIVO ---
    print()
    print(f"  A) PATRIMONIO NETO                    {eur(datos['total_pn'])}")
    _imprimir_lineas_seccion(lineas.get("pn", {}))

    print(f"  B) PASIVO NO CORRIENTE                {eur(datos['total_pnc'])}")
    _imprimir_lineas_seccion(lineas.get("pnc", {}))

    print(f"  C) PASIVO CORRIENTE                   {eur(datos['total_pc'])}")
    _imprimir_lineas_seccion(lineas.get("pc", {}))

    print(f"    -------------------------------------------------")
    print(f"    TOTAL PN + PASIVO                   {eur(datos['total_pasivo'])}")

    separador()
    estado = "CUADRA" if datos["cuadra"] else "NO CUADRA - revisar asientos"
    print(f"  Verificacion: {estado}")


def imprimir_pyg(datos):
    separador("CUENTA DE PERDIDAS Y GANANCIAS")
    p = datos["partidas"]

    print()
    print(f"   1. Cifra de negocios              {eur(p.get('cifra_negocios', 0))}")
    if p.get("variacion_existencias", 0):
        print(f"   2. Variacion de existencias       {eur(p['variacion_existencias'])}")
    if p.get("trabajos_activo", 0):
        print(f"   3. Trabajos para el activo        {eur(p['trabajos_activo'])}")
    print(f"   4. Aprovisionamientos            -{eur(p.get('aprovisionamientos', 0))}")
    if p.get("otros_ingresos_expl", 0):
        print(f"   5. Otros ingresos explotacion     {eur(p['otros_ingresos_expl'])}")
    print(f"   6. Gastos de personal            -{eur(p.get('gastos_personal', 0))}")
    print(f"   7. Otros gastos de explotacion   -{eur(p.get('otros_gastos_expl', 0))}")
    print(f"   8. Amortizacion del inmovilizado -{eur(p.get('amortizacion', 0))}")
    if p.get("otros_resultados", 0):
        print(f"   9. Otros resultados               {eur(p['otros_resultados'])}")

    separador()
    print(f"  A) RESULTADO DE EXPLOTACION        {eur(datos['resultado_explotacion'])}")

    print()
    print(f"  10. Ingresos financieros           {eur(p.get('ingresos_financieros', 0))}")
    print(f"  11. Gastos financieros            -{eur(p.get('gastos_financieros', 0))}")

    separador()
    print(f"  B) RESULTADO FINANCIERO            {eur(datos['resultado_financiero'])}")

    separador()
    print(f"  C) RESULTADO ANTES DE IMPUESTOS    {eur(datos['resultado_antes_impuestos'])}")

    etiqueta_imp = "Imp. Sociedades (est. 25%)" if datos["impuesto_estimado"] else "Impuesto sobre beneficios"
    print(f"  17. {etiqueta_imp:<32}-{eur(datos['impuesto'])}")

    separador()
    print(f"  D) RESULTADO DEL EJERCICIO         {eur(datos['resultado_neto'])}")


# --- Main ---

def main():
    parser = argparse.ArgumentParser(
        description="Resumen fiscal on-demand desde FacturaScripts",
    )
    parser.add_argument(
        "--empresa", type=int, required=True,
        help="ID empresa en FacturaScripts (1=Pastorino, 2=Gerardo)",
    )
    parser.add_argument(
        "--ejercicio", type=str, default=str(datetime.now().year),
        help="Ejercicio fiscal (default: ano actual)",
    )
    parser.add_argument(
        "--trimestre", type=str, choices=["T1", "T2", "T3", "T4"],
        help="Trimestre especifico (si no se indica, todo el ejercicio)",
    )
    parser.add_argument(
        "--tipo", type=str, choices=["autonomo", "sl"],
        help="Tipo empresa (override autodeteccion)",
    )
    args = parser.parse_args()

    # Token API
    token = os.environ.get("FS_API_TOKEN")
    if not token:
        print("Error: Variable de entorno FS_API_TOKEN no configurada")
        print("  export FS_API_TOKEN='tu_token_aqui'")
        sys.exit(1)

    # Validar empresa
    empresa = EMPRESAS.get(args.empresa)
    if not empresa:
        print(f"Error: Empresa {args.empresa} no registrada")
        print(f"Empresas disponibles:")
        for eid, edata in EMPRESAS.items():
            print(f"  --empresa {eid}  →  {edata['nombre']} ({edata['tipo']})")
        sys.exit(1)

    tipo = args.tipo or empresa["tipo"]
    periodo = args.trimestre or f"Ejercicio {args.ejercicio} completo"

    # Cabecera
    print(f"\n{'#' * 64}")
    print(f"  RESUMEN FISCAL PROVISIONAL")
    print(f"  {empresa['nombre']}")
    print(f"  Periodo: {periodo}")
    print(f"  Tipo: {tipo.upper()}")
    print(f"  Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print(f"{'#' * 64}")

    # --- Obtener datos ---
    print("\n  Consultando FacturaScripts...")

    fact_clientes = obtener_facturas_cliente(
        token, args.empresa, args.ejercicio, args.trimestre,
    )
    fact_proveedores = obtener_facturas_proveedor(
        token, args.empresa, args.ejercicio, args.trimestre,
    )
    print(f"  - {len(fact_clientes)} facturas emitidas")
    print(f"  - {len(fact_proveedores)} facturas recibidas")

    # --- Modelos fiscales (todos) ---
    m303 = calcular_modelo_303(fact_clientes, fact_proveedores)
    imprimir_303(m303)

    m111 = calcular_modelo_111(fact_proveedores)
    imprimir_111(m111)

    # --- Especificos por tipo ---
    if tipo == "autonomo":
        m130 = calcular_modelo_130(fact_clientes, fact_proveedores)
        imprimir_130(m130)

    elif tipo == "sl":
        print("\n  Consultando subcuentas contables...")
        subcuentas = obtener_subcuentas(token, args.empresa, args.ejercicio)
        con_movimientos = [
            sc for sc in subcuentas
            if float(sc.get("debe", 0)) != 0 or float(sc.get("haber", 0)) != 0
        ]
        print(f"  - {len(con_movimientos)} subcuentas con movimientos")

        balance = calcular_balance(con_movimientos)
        imprimir_balance(balance)

        pyg = calcular_pyg(con_movimientos)
        imprimir_pyg(pyg)

    # --- Pie ---
    print(f"\n{'#' * 64}")
    print(f"  AVISO: Datos provisionales basados en la contabilidad")
    print(f"  registrada hasta la fecha. Para modelos fiscales oficiales")
    print(f"  usar FacturaScripts > Informes.")
    print(f"{'#' * 64}\n")


if __name__ == "__main__":
    main()
