"""
Generador de recibos bancarios para datos de prueba contable espanol.

Produce DocGenerado para: prestamos, hipotecas, leasing, renting y
comisiones bancarias. Se llama desde el orquestador principal.
"""

import random
import sys
from datetime import date
from pathlib import Path
from typing import List

DIR_GENERADOR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DIR_GENERADOR))

from utils.fechas import fechas_mensuales
from utils.importes import _redondear

# Importar DocGenerado desde gen_facturas (dataclass compartida del proyecto)
from generadores.gen_facturas import DocGenerado


# ---------------------------------------------------------------------------
# Bancos ficticios
# ---------------------------------------------------------------------------

_BANCOS_FICTICIOS = [
    {"nombre": "Banco Santander S.A.", "bic": "BSCHESMMXXX"},
    {"nombre": "BBVA S.A.", "bic": "BBVAESMMXXX"},
    {"nombre": "CaixaBank S.A.", "bic": "CAIXESBBXXX"},
    {"nombre": "Banco Sabadell S.A.", "bic": "BSABESBBXXX"},
    {"nombre": "Bankinter S.A.", "bic": "BKBKESMMXXX"},
    {"nombre": "Unicaja Banco S.A.", "bic": "UCJAES2MXXX"},
    {"nombre": "Abanca Corporacion Bancaria S.A.", "bic": "CAGLESMMXXX"},
    {"nombre": "Ibercaja Banco S.A.", "bic": "CAZRES2ZXXX"},
]

_OFICINAS = [
    "Oficina 0042 — Malaga Centro",
    "Oficina 1234 — Valencia Gran Via",
    "Oficina 0817 — Madrid Castellana",
    "Oficina 2201 — Marbella Golden Mile",
    "Oficina 0553 — Alicante Puerto",
    "Oficina 3310 — Barcelona Diagonal",
]


def _nombre_banco(rng: random.Random = None) -> dict:
    """Devuelve un banco ficticio con nombre, oficina y BIC."""
    generador = rng or random
    banco = generador.choice(_BANCOS_FICTICIOS)
    oficina = generador.choice(_OFICINAS)
    return {
        "nombre": banco["nombre"],
        "bic": banco["bic"],
        "oficina": oficina,
    }


def _generar_referencia(tipo: str, anio: int, rng: random.Random = None) -> str:
    """Genera un numero de contrato/referencia ficticio."""
    generador = rng or random
    prefijos = {
        "prestamo": "PRE",
        "hipoteca": "HIP",
        "leasing": "LEA",
        "renting": "REN",
        "poliza_credito": "POL",
        "comision": "COM",
    }
    prefijo = prefijos.get(tipo, "BAN")
    numero = generador.randint(10000000, 99999999)
    return f"{prefijo}-{anio}-{numero}"


def _slug_producto(nombre: str) -> str:
    """Convierte el nombre del producto a slug para el nombre de archivo."""
    import unicodedata
    # Normalizar acentos
    nombre_norm = unicodedata.normalize("NFKD", nombre)
    nombre_ascii = nombre_norm.encode("ascii", "ignore").decode("ascii")
    return (
        nombre_ascii.lower()
        .replace(" ", "_")
        .replace("(", "")
        .replace(")", "")
        .replace("-", "_")
        .replace("/", "_")
        [:40]
    )


def _tiene_tpv(entidad: dict) -> bool:
    """
    Determina si la entidad tiene TPV por su actividad economica.
    Restaurantes, hosteleria, comercio minorista y servicios presenciales suelen tenerlo.
    """
    actividad = entidad.get("actividad", "").lower()
    cnae = str(entidad.get("cnae", ""))
    claves_tpv = [
        "restaurante", "hosteleria", "hostelero", "bar ", "cafeteria",
        "comercio", "tienda", "venta al por menor", "minorista",
        "pilates", "gimnasio", "deporte", "spa", "peluquer",
        "catering", "chiringuito",
    ]
    # CNAE hosteleria: 5610-5630; comercio minorista: 47xx
    cnae_tpv = cnae.startswith("56") or cnae.startswith("47")
    actividad_tpv = any(clave in actividad for clave in claves_tpv)
    return cnae_tpv or actividad_tpv


def _tiene_operaciones_internacionales(entidad: dict) -> bool:
    """Detecta si la entidad tiene proveedores intracomunitarios o extracomunitarios."""
    proveedores = entidad.get("proveedores_detalle", [])
    for prov in proveedores:
        regimen = prov.get("regimen", "")
        if regimen in ("intracomunitario", "extracomunitario", "importacion"):
            return True
    return False


# ---------------------------------------------------------------------------
# Generador de cuotas de prestamo / hipoteca (tabla francesa simplificada)
# ---------------------------------------------------------------------------

def _generar_cuotas_prestamo(
    producto: dict,
    entidad: dict,
    anio: int,
    rng: random.Random = None,
) -> List[DocGenerado]:
    """
    Genera 12 documentos de cuota mensual para un prestamo o hipoteca
    usando amortizacion francesa simplificada.
    """
    generador = rng or random
    tipo = producto.get("tipo", "prestamo")
    nombre = producto.get("nombre", "Prestamo")
    cuota = float(producto.get("cuota", 0))
    interes_anual = float(producto.get("interes", 0))
    saldo_pendiente = float(producto.get("pendiente", 0))
    plazo_meses = int(producto.get("plazo_meses", 12))
    slug = _slug_producto(nombre)
    banco = _nombre_banco(generador)
    referencia = _generar_referencia(tipo, anio, generador)

    nombre_entidad = entidad.get("nombre", entidad.get("nombre_fiscal", "Empresa"))
    nif_entidad = entidad.get("nif", entidad.get("cif", ""))

    tipo_interes_mensual = interes_anual / 100 / 12
    docs: List[DocGenerado] = []
    fechas = fechas_mensuales(anio, dia=5)

    for i, fecha in enumerate(fechas):
        mes_num = i + 1

        # Calculos tabla francesa
        if tipo_interes_mensual > 0 and saldo_pendiente > 0:
            interes_mes = _redondear(saldo_pendiente * tipo_interes_mensual)
        else:
            interes_mes = 0.0

        capital_mes = _redondear(cuota - interes_mes)
        # El capital no puede superar el saldo pendiente
        if capital_mes > saldo_pendiente:
            capital_mes = _redondear(saldo_pendiente)
        capital_mes = max(capital_mes, 0.0)

        saldo_pendiente = _redondear(max(saldo_pendiente - capital_mes, 0.0))

        # Cuotas restantes aproximadas
        cuotas_restantes = max(0, plazo_meses - (12 - (12 - i)))

        detalle = [
            {"concepto": "Amortizacion de capital", "importe": capital_mes},
            {"concepto": "Intereses", "importe": interes_mes},
        ]

        datos = {
            "banco": banco,
            "titular": {"nombre": nombre_entidad, "nif": nif_entidad},
            "tipo_recibo": tipo,
            "subtipo_texto": "Hipoteca" if tipo == "hipoteca" else "Prestamo",
            "referencia": referencia,
            "nombre_producto": nombre,
            "fecha": fecha.isoformat(),
            "fecha_valor": fecha.replace(day=min(fecha.day + 2, 28)).isoformat(),
            "concepto": f"Cuota {mes_num:02d}/{anio} — {nombre}",
            "detalle": detalle,
            "total": cuota,
            "saldo_pendiente": saldo_pendiente,
            "cuotas_restantes": cuotas_restantes,
            "cuenta_cargo": entidad.get("cuenta_banco_principal", "57200000"),
        }

        archivo = f"{anio}-{mes_num:02d}_prestamo_{slug}.pdf"

        docs.append(DocGenerado(
            tipo="recibo_bancario",
            subtipo=tipo,
            plantilla="recibo_bancario.html",
            css_variante=entidad.get("css_variante", "corporativo"),
            archivo=archivo,
            datos_plantilla=datos,
            metadatos={
                "total": cuota,
                "capital": capital_mes,
                "intereses": interes_mes,
                "saldo_pendiente": saldo_pendiente,
                "mes": mes_num,
                "anio": anio,
                "nombre_producto": nombre,
            },
        ))

    return docs


# ---------------------------------------------------------------------------
# Generador de cuotas de leasing
# ---------------------------------------------------------------------------

def _generar_cuotas_leasing(
    producto: dict,
    entidad: dict,
    anio: int,
    rng: random.Random = None,
) -> List[DocGenerado]:
    """
    Genera 12 cuotas mensuales de leasing financiero con IVA 21%.
    Si es el ultimo ano del contrato incluye la opcion de compra (valor residual ~1%).
    """
    generador = rng or random
    nombre = producto.get("nombre", "Leasing")
    cuota_con_iva = float(producto.get("cuota", 0))
    interes_anual = float(producto.get("interes", 0))
    saldo_pendiente = float(producto.get("pendiente", 0))
    plazo_meses = int(producto.get("plazo_meses", 48))
    importe_total = float(producto.get("importe", 0))
    slug = _slug_producto(nombre)
    banco = _nombre_banco(generador)
    referencia = _generar_referencia("leasing", anio, generador)

    nombre_entidad = entidad.get("nombre", entidad.get("nombre_fiscal", "Empresa"))
    nif_entidad = entidad.get("nif", entidad.get("cif", ""))

    # La cuota del YAML incluye IVA: desglosamos
    IVA_PCT = 21
    cuota_sin_iva = _redondear(cuota_con_iva / (1 + IVA_PCT / 100))
    cuota_iva = _redondear(cuota_con_iva - cuota_sin_iva)

    tipo_interes_mensual = interes_anual / 100 / 12

    # Determinar si este es el ultimo ano del contrato
    # (plazo_meses <= 12 o pendiente <= cuota*12 y el contrato acaba este ano)
    es_ultimo_ano = plazo_meses <= 12 or (saldo_pendiente <= cuota_sin_iva * 12 * 1.1 and saldo_pendiente > 0)
    valor_residual = _redondear(importe_total * 0.01) if importe_total > 0 else _redondear(cuota_sin_iva * 0.5)

    docs: List[DocGenerado] = []
    fechas = fechas_mensuales(anio, dia=5)

    for i, fecha in enumerate(fechas):
        mes_num = i + 1
        cuotas_restantes = max(0, plazo_meses - i)

        # Calculo de la parte de interes (sobre saldo sin IVA)
        if tipo_interes_mensual > 0 and saldo_pendiente > 0:
            interes_mes = _redondear(saldo_pendiente * tipo_interes_mensual)
        else:
            interes_mes = 0.0

        capital_mes = _redondear(cuota_sin_iva - interes_mes)
        if capital_mes > saldo_pendiente:
            capital_mes = _redondear(saldo_pendiente)
        capital_mes = max(capital_mes, 0.0)
        saldo_pendiente = _redondear(max(saldo_pendiente - capital_mes, 0.0))

        # Opcion de compra: solo en la ultima cuota del ultimo ano
        incluye_opcion_compra = es_ultimo_ano and mes_num == 12 and saldo_pendiente == 0
        opcion_base = valor_residual if incluye_opcion_compra else 0.0
        opcion_iva = _redondear(opcion_base * IVA_PCT / 100) if incluye_opcion_compra else 0.0

        base_total = _redondear(cuota_sin_iva + opcion_base)
        iva_total = _redondear(cuota_iva + opcion_iva)
        total_recibo = _redondear(base_total + iva_total)

        detalle = [
            {"concepto": "Cuota de arrendamiento financiero", "importe": cuota_sin_iva},
        ]
        if incluye_opcion_compra:
            detalle.append({"concepto": "Opcion de compra (valor residual)", "importe": opcion_base})

        datos = {
            "banco": banco,
            "titular": {"nombre": nombre_entidad, "nif": nif_entidad},
            "tipo_recibo": "leasing",
            "subtipo_texto": "Arrendamiento financiero (Leasing)",
            "referencia": referencia,
            "nombre_producto": nombre,
            "fecha": fecha.isoformat(),
            "fecha_valor": fecha.replace(day=min(fecha.day + 2, 28)).isoformat(),
            "concepto": f"Cuota leasing {mes_num:02d}/{anio} — {nombre}",
            "detalle": detalle,
            "iva": {
                "base": base_total,
                "tipo": IVA_PCT,
                "cuota": iva_total,
            },
            "total": total_recibo,
            "saldo_pendiente": saldo_pendiente,
            "cuotas_restantes": cuotas_restantes,
            "incluye_opcion_compra": incluye_opcion_compra,
            "valor_residual": valor_residual if incluye_opcion_compra else None,
            "cuenta_cargo": entidad.get("cuenta_banco_principal", "57200000"),
        }

        archivo = f"{anio}-{mes_num:02d}_leasing_{slug}.pdf"

        docs.append(DocGenerado(
            tipo="recibo_bancario",
            subtipo="leasing",
            plantilla="recibo_bancario.html",
            css_variante=entidad.get("css_variante", "corporativo"),
            archivo=archivo,
            datos_plantilla=datos,
            metadatos={
                "total": total_recibo,
                "base": base_total,
                "iva": iva_total,
                "capital": capital_mes,
                "intereses": interes_mes,
                "saldo_pendiente": saldo_pendiente,
                "mes": mes_num,
                "anio": anio,
                "nombre_producto": nombre,
            },
        ))

    return docs


# ---------------------------------------------------------------------------
# Generador de recibos de renting
# ---------------------------------------------------------------------------

def _generar_recibos_renting(
    producto: dict,
    entidad: dict,
    anio: int,
) -> List[DocGenerado]:
    """
    Genera facturas mensuales de renting (gasto cuenta 621, IVA 21%).
    Solo genera para los meses activos de la entidad (util para estacionales).
    """
    nombre = producto.get("nombre", "Renting")
    cuota_sin_iva = float(producto.get("cuota", 0))
    slug = _slug_producto(nombre)

    # Meses activos: usar los de la entidad (ej chiringuito: 4-10) o todos
    meses_activos = entidad.get("meses_activos", list(range(1, 13)))

    IVA_PCT = 21
    cuota_iva = _redondear(cuota_sin_iva * IVA_PCT / 100)
    total_recibo = _redondear(cuota_sin_iva + cuota_iva)

    nombre_entidad = entidad.get("nombre", entidad.get("nombre_fiscal", "Empresa"))
    nif_entidad = entidad.get("nif", entidad.get("cif", ""))

    # El proveedor de renting se extrae del nombre del producto si es posible
    nombre_partes = nombre.split(" ")
    proveedor_renting = nombre_partes[-1] if len(nombre_partes) > 1 else "Proveedor Renting"

    docs: List[DocGenerado] = []
    fechas = fechas_mensuales(anio, meses=meses_activos, dia=5)

    for fecha in fechas:
        mes_num = fecha.month

        datos = {
            "emisor": {
                "nombre": f"{proveedor_renting} S.A.",
                "nif": "A00000001",
                "direccion": "Polígono Industrial, s/n",
            },
            "receptor": {"nombre": nombre_entidad, "nif": nif_entidad},
            "tipo_recibo": "renting",
            "subtipo_texto": "Renting (arrendamiento operativo)",
            "nombre_producto": nombre,
            "fecha": fecha.isoformat(),
            "concepto": f"Cuota renting {mes_num:02d}/{anio} — {nombre}",
            "detalle": [
                {"concepto": nombre, "importe": cuota_sin_iva},
            ],
            "iva": {
                "base": cuota_sin_iva,
                "tipo": IVA_PCT,
                "cuota": cuota_iva,
            },
            "total": total_recibo,
            "cuenta_gasto": producto.get("cuenta", "621"),
        }

        archivo = f"{anio}-{mes_num:02d}_renting_{slug}.pdf"

        docs.append(DocGenerado(
            tipo="recibo_bancario",
            subtipo="renting",
            plantilla="recibo_bancario.html",
            css_variante=entidad.get("css_variante", "corporativo"),
            archivo=archivo,
            datos_plantilla=datos,
            metadatos={
                "total": total_recibo,
                "base": cuota_sin_iva,
                "iva": cuota_iva,
                "mes": mes_num,
                "anio": anio,
                "nombre_producto": nombre,
            },
        ))

    return docs


# ---------------------------------------------------------------------------
# Generador de recibos de poliza de credito
# ---------------------------------------------------------------------------

def _generar_recibos_poliza(
    producto: dict,
    entidad: dict,
    anio: int,
    rng: random.Random,
) -> List[DocGenerado]:
    """
    Genera los cargos anuales y trimestrales de una poliza de credito:
    - 1 comision de apertura/renovacion en enero (0.5% del limite)
    - 4 comisiones de no disposicion trimestrales (0.15% del no dispuesto)
    - 4 liquidaciones de intereses trimestrales (sobre media dispuesta)
    """
    nombre = producto.get("nombre", "Poliza de credito")
    limite = float(producto.get("importe", 0))          # "importe" = limite de la poliza
    saldo_dispuesto = float(producto.get("pendiente", 0))
    interes_anual = float(producto.get("interes", 0))
    slug = _slug_producto(nombre)
    banco = _nombre_banco(rng)
    referencia = _generar_referencia("poliza_credito", anio, rng)

    nombre_entidad = entidad.get("nombre", entidad.get("nombre_fiscal", "Empresa"))
    nif_entidad = entidad.get("nif", entidad.get("cif", ""))

    no_dispuesto = max(0.0, limite - saldo_dispuesto)
    docs: List[DocGenerado] = []

    # --- Comision apertura/renovacion (enero, dia 15) ---
    comision_apertura = _redondear(limite * 0.005)  # 0.5%
    fecha_apertura = date(anio, 1, 15)

    datos_apertura = {
        "banco": banco,
        "titular": {"nombre": nombre_entidad, "nif": nif_entidad},
        "tipo_recibo": "poliza_credito",
        "subtipo_texto": "Poliza de credito — Comision apertura/renovacion",
        "referencia": referencia,
        "nombre_producto": nombre,
        "fecha": fecha_apertura.isoformat(),
        "concepto": f"Comision apertura poliza {anio} — {nombre}",
        "detalle": [
            {"concepto": "Comision de apertura/renovacion (0,50% s/limite)", "importe": comision_apertura},
        ],
        "total": comision_apertura,
        "limite": limite,
        "cuenta_cargo": entidad.get("cuenta_banco_principal", "57200000"),
    }
    docs.append(DocGenerado(
        tipo="recibo_bancario",
        subtipo="poliza_credito",
        plantilla="recibo_bancario.html",
        css_variante=entidad.get("css_variante", "corporativo"),
        archivo=f"{anio}-01_poliza_apertura_{slug}.pdf",
        datos_plantilla=datos_apertura,
        metadatos={
            "total": comision_apertura,
            "concepto_corto": "comision_apertura",
            "anio": anio,
            "nombre_producto": nombre,
        },
    ))

    # --- Recibos trimestrales ---
    trimestres = [
        (1, 3, "T1", date(anio, 3, 31)),
        (4, 6, "T2", date(anio, 6, 30)),
        (7, 9, "T3", date(anio, 9, 30)),
        (10, 12, "T4", date(anio, 12, 31)),
    ]

    # Simular variacion en el saldo dispuesto por trimestre (con algo de ruido)
    saldo_trimestral = saldo_dispuesto
    for mes_ini, mes_fin, codigo_t, fecha_liq in trimestres:
        # Fluctuacion del dispuesto: +/- 10% del limite
        variacion = rng.uniform(-0.10, 0.10) * limite
        saldo_trimestral = _redondear(
            max(0.0, min(limite, saldo_trimestral + variacion))
        )
        no_dispuesto_t = _redondear(max(0.0, limite - saldo_trimestral))

        # Comision no disposicion: 0.15% / 4 trimestres del no dispuesto
        comision_no_disp = _redondear(no_dispuesto_t * 0.0015)

        # Intereses sobre dispuesto (base 90 dias / 360)
        dias_trimestre = 90
        intereses_t = _redondear(saldo_trimestral * (interes_anual / 100) * dias_trimestre / 360)

        total_t = _redondear(comision_no_disp + intereses_t)

        datos_t = {
            "banco": banco,
            "titular": {"nombre": nombre_entidad, "nif": nif_entidad},
            "tipo_recibo": "poliza_credito",
            "subtipo_texto": f"Poliza de credito — Liquidacion {codigo_t}",
            "referencia": referencia,
            "nombre_producto": nombre,
            "fecha": fecha_liq.isoformat(),
            "concepto": f"Liquidacion {codigo_t}/{anio} poliza — {nombre}",
            "detalle": [
                {
                    "concepto": f"Comision no disposicion (0,15% s/{no_dispuesto_t:.2f} EUR no dispuesto)",
                    "importe": comision_no_disp,
                },
                {
                    "concepto": f"Intereses dispuesto ({interes_anual}% TAE, {dias_trimestre} dias s/{saldo_trimestral:.2f} EUR)",
                    "importe": intereses_t,
                },
            ],
            "total": total_t,
            "limite": limite,
            "saldo_dispuesto": saldo_trimestral,
            "no_dispuesto": no_dispuesto_t,
            "cuenta_cargo": entidad.get("cuenta_banco_principal", "57200000"),
        }

        trimestre_mes = trimestres.index((mes_ini, mes_fin, codigo_t, fecha_liq)) + 1
        archivo = f"{anio}-{mes_fin:02d}_poliza_{codigo_t.lower()}_{slug}.pdf"

        docs.append(DocGenerado(
            tipo="recibo_bancario",
            subtipo="poliza_credito",
            plantilla="recibo_bancario.html",
            css_variante=entidad.get("css_variante", "corporativo"),
            archivo=archivo,
            datos_plantilla=datos_t,
            metadatos={
                "total": total_t,
                "comision_no_disp": comision_no_disp,
                "intereses": intereses_t,
                "trimestre": codigo_t,
                "anio": anio,
                "nombre_producto": nombre,
            },
        ))

    return docs


# ---------------------------------------------------------------------------
# Generador de comisiones bancarias genericas
# ---------------------------------------------------------------------------

def _generar_comisiones(
    entidad: dict,
    anio: int,
    rng: random.Random,
) -> List[DocGenerado]:
    """
    Genera comisiones bancarias de diverso tipo segun el perfil de la entidad:
    - Mantenimiento de cuenta: trimestral
    - Transferencias: 2-5 por trimestre
    - TPV: mensual si la entidad tiene comercio/hosteleria
    - Transferencia internacional: puntual si hay operaciones intracomunitarias
    """
    banco = _nombre_banco(rng)
    nombre_entidad = entidad.get("nombre", entidad.get("nombre_fiscal", "Empresa"))
    nif_entidad = entidad.get("nif", entidad.get("cif", ""))
    css = entidad.get("css_variante", "corporativo")
    docs: List[DocGenerado] = []

    # --- Mantenimiento de cuenta: 4 recibos trimestrales ---
    fechas_mant = [
        date(anio, 3, 31),
        date(anio, 6, 30),
        date(anio, 9, 30),
        date(anio, 12, 31),
    ]
    trimestres_nombres = ["T1", "T2", "T3", "T4"]

    for idx, (fecha, codigo_t) in enumerate(zip(fechas_mant, trimestres_nombres)):
        comision_mant = _redondear(rng.uniform(15.0, 30.0))
        referencia = _generar_referencia("comision", anio, rng)

        datos = {
            "banco": banco,
            "titular": {"nombre": nombre_entidad, "nif": nif_entidad},
            "tipo_recibo": "comision",
            "subtipo_texto": "Comision mantenimiento cuenta corriente",
            "referencia": referencia,
            "fecha": fecha.isoformat(),
            "concepto": f"Mantenimiento cuenta — {codigo_t} {anio}",
            "detalle": [
                {"concepto": "Comision administracion cuenta corriente", "importe": comision_mant},
            ],
            "total": comision_mant,
            "cuenta_cargo": entidad.get("cuenta_banco_principal", "57200000"),
        }
        docs.append(DocGenerado(
            tipo="recibo_bancario",
            subtipo="comision",
            plantilla="recibo_bancario.html",
            css_variante=css,
            archivo=f"{anio}-{fecha.month:02d}_comision_mantenimiento_{codigo_t.lower()}.pdf",
            datos_plantilla=datos,
            metadatos={
                "total": comision_mant,
                "concepto_corto": "mantenimiento",
                "trimestre": codigo_t,
                "anio": anio,
            },
        ))

    # --- Comisiones por transferencias: 2-5 por trimestre ---
    meses_trimestre = [(1, 3), (4, 6), (7, 9), (10, 12)]
    for (mes_ini, mes_fin), codigo_t in zip(meses_trimestre, trimestres_nombres):
        num_transf = rng.randint(2, 5)
        total_transf = _redondear(sum(rng.uniform(0.50, 3.00) for _ in range(num_transf)))
        fecha_t = date(anio, mes_fin, 28)
        referencia = _generar_referencia("comision", anio, rng)

        datos = {
            "banco": banco,
            "titular": {"nombre": nombre_entidad, "nif": nif_entidad},
            "tipo_recibo": "comision",
            "subtipo_texto": "Comisiones por transferencias emitidas",
            "referencia": referencia,
            "fecha": fecha_t.isoformat(),
            "concepto": f"Comisiones transferencias — {codigo_t} {anio}",
            "detalle": [
                {
                    "concepto": f"Comision por {num_transf} transferencias SEPA emitidas",
                    "importe": total_transf,
                },
            ],
            "total": total_transf,
            "cuenta_cargo": entidad.get("cuenta_banco_principal", "57200000"),
        }
        docs.append(DocGenerado(
            tipo="recibo_bancario",
            subtipo="comision",
            plantilla="recibo_bancario.html",
            css_variante=css,
            archivo=f"{anio}-{mes_fin:02d}_comision_transferencias_{codigo_t.lower()}.pdf",
            datos_plantilla=datos,
            metadatos={
                "total": total_transf,
                "concepto_corto": "transferencias",
                "trimestre": codigo_t,
                "anio": anio,
            },
        ))

    # --- TPV: comision mensual ~1% de ventas estimadas ---
    if _tiene_tpv(entidad):
        # Estimar ventas mensuales desde los ingresos anuales si disponibles
        ingresos_anuales = float(entidad.get("ingresos_estimados", 150000))
        ventas_mes_estimadas = _redondear(ingresos_anuales / 12)
        meses_activos = entidad.get("meses_activos", list(range(1, 13)))
        fechas_tpv = fechas_mensuales(anio, meses=meses_activos, dia=28)

        for fecha in fechas_tpv:
            # Variacion aleatoria sobre la estimacion base
            factor = rng.uniform(0.85, 1.15)
            ventas_mes = _redondear(ventas_mes_estimadas * factor)
            comision_tpv = _redondear(ventas_mes * 0.01)
            referencia = _generar_referencia("comision", anio, rng)

            datos = {
                "banco": banco,
                "titular": {"nombre": nombre_entidad, "nif": nif_entidad},
                "tipo_recibo": "comision",
                "subtipo_texto": "Comision TPV — Terminal Punto de Venta",
                "referencia": referencia,
                "fecha": fecha.isoformat(),
                "concepto": f"Comision TPV {fecha.month:02d}/{anio}",
                "detalle": [
                    {
                        "concepto": f"Comision cobros tarjeta ({ventas_mes:.2f} EUR ventas, 1,00%)",
                        "importe": comision_tpv,
                    },
                ],
                "total": comision_tpv,
                "ventas_periodo": ventas_mes,
                "cuenta_cargo": entidad.get("cuenta_banco_principal", "57200000"),
            }
            docs.append(DocGenerado(
                tipo="recibo_bancario",
                subtipo="comision",
                plantilla="recibo_bancario.html",
                css_variante=css,
                archivo=f"{anio}-{fecha.month:02d}_comision_tpv.pdf",
                datos_plantilla=datos,
                metadatos={
                    "total": comision_tpv,
                    "concepto_corto": "tpv",
                    "mes": fecha.month,
                    "anio": anio,
                },
            ))

    # --- Transferencia internacional: 1 puntual si hay operaciones internacionales ---
    if _tiene_operaciones_internacionales(entidad):
        # Entre los meses activos, escoger uno aleatorio
        meses_activos = entidad.get("meses_activos", list(range(1, 13)))
        mes_int = rng.choice(meses_activos)
        fecha_int = date(anio, mes_int, rng.randint(5, 25))
        comision_int = _redondear(rng.uniform(15.0, 25.0))
        referencia = _generar_referencia("comision", anio, rng)

        datos = {
            "banco": banco,
            "titular": {"nombre": nombre_entidad, "nif": nif_entidad},
            "tipo_recibo": "comision",
            "subtipo_texto": "Comision transferencia internacional SWIFT",
            "referencia": referencia,
            "fecha": fecha_int.isoformat(),
            "concepto": f"Comision transferencia internacional {anio}",
            "detalle": [
                {"concepto": "Comision emision transferencia SWIFT internacional", "importe": comision_int},
            ],
            "total": comision_int,
            "cuenta_cargo": entidad.get("cuenta_banco_principal", "57200000"),
        }
        docs.append(DocGenerado(
            tipo="recibo_bancario",
            subtipo="comision",
            plantilla="recibo_bancario.html",
            css_variante=css,
            archivo=f"{anio}-{mes_int:02d}_comision_swift_internacional.pdf",
            datos_plantilla=datos,
            metadatos={
                "total": comision_int,
                "concepto_corto": "swift_internacional",
                "mes": mes_int,
                "anio": anio,
            },
        ))

    return docs


# ---------------------------------------------------------------------------
# Funcion principal orquestadora
# ---------------------------------------------------------------------------

def generar_bancarios(
    entidad: dict,
    anio: int,
    rng: random.Random,
) -> List[DocGenerado]:
    """
    Genera todos los recibos bancarios de la entidad para el ano indicado.

    Itera sobre `entidad["productos_financieros"]` y despacha cada tipo
    al generador correspondiente. Ademas genera comisiones bancarias genericas.

    Tipos soportados:
        - prestamo / hipoteca: tabla francesa, 12 cuotas
        - leasing: 12 cuotas con IVA 21%, opcion de compra en ultimo ano
        - renting: facturas mensuales con IVA 21%, respeta meses activos
        - poliza_credito: apertura anual + 4 liquidaciones trimestrales

    Tipos ignorados (sin logica bancaria propia en este modulo):
        - linea_descuento, confirming, factoring (se pueden anadir si se necesitan)

    Parametros:
        entidad: dict con los datos de la entidad del YAML
        anio: ejercicio a generar
        rng: instancia de Random para reproducibilidad

    Retorna lista de DocGenerado (tipo="recibo_bancario").
    """
    productos = entidad.get("productos_financieros", [])
    docs: List[DocGenerado] = []

    for producto in productos:
        tipo = producto.get("tipo", "")

        if tipo in ("prestamo", "hipoteca"):
            docs.extend(_generar_cuotas_prestamo(producto, entidad, anio, rng))

        elif tipo == "leasing":
            docs.extend(_generar_cuotas_leasing(producto, entidad, anio, rng))

        elif tipo == "renting":
            docs.extend(_generar_recibos_renting(producto, entidad, anio))

        elif tipo == "poliza_credito":
            docs.extend(_generar_recibos_poliza(producto, entidad, anio, rng))

        # tipos ignorados: linea_descuento, confirming, factoring, etc.

    # Comisiones bancarias genericas (siempre se generan)
    docs.extend(_generar_comisiones(entidad, anio, rng))

    return docs
