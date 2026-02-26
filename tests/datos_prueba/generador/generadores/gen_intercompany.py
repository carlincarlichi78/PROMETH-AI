"""
Generador de documentos intercompany para el generador de datos de prueba contable.
Produce management fees mensuales, intereses de prestamos, dividendos y prestamos
cruzados estacionales entre sociedades del mismo grupo.
"""

import random
import sys
from datetime import date
from pathlib import Path
from typing import List

DIR_GENERADOR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DIR_GENERADOR))

from generadores.gen_facturas import DocGenerado
from utils.importes import _redondear, LineaFactura, ResumenFactura
from utils.fechas import generar_fecha_en_mes


# ---------------------------------------------------------------------------
# Meses de cierre trimestral (para intereses)
# ---------------------------------------------------------------------------

_MESES_TRIMESTRE = [3, 6, 9, 12]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _nombre_mes(mes: int) -> str:
    """Devuelve el nombre del mes en espanol."""
    nombres = [
        "", "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
    ]
    return nombres[mes]


def _generar_numero_mgmt(anio: int, mes: int, slug_filial: str) -> str:
    """Genera numero de factura de management fee."""
    siglas = slug_filial.upper().replace("-", "")[:6]
    return f"MGT-{siglas}-{anio}-{mes:02d}"


# ---------------------------------------------------------------------------
# Management fees mensuales
# ---------------------------------------------------------------------------

def _generar_management_fees(
    entidad: dict,
    anio: int,
    rng: random.Random,
    intercompany: dict,
) -> List[DocGenerado]:
    """
    Genera 12 facturas de management fee mensuales por cada filial configurada.
    El holding factura a cada filial un importe fijo mensual.
    """
    docs: List[DocGenerado] = []
    clientes = entidad.get("clientes", {})

    # Identificar clientes que son management fees intercompany
    for slug_cli, cliente in clientes.items():
        concepto = cliente.get("concepto", "").lower()
        if "management fee" not in concepto:
            continue

        importe_fee = float(cliente.get("importe_rango", [0, 0])[0])
        if importe_fee <= 0:
            continue

        nombre_filial = cliente.get("nombre", slug_cli)
        cif_filial = cliente.get("cif", "")

        for mes in range(1, 13):
            fecha = generar_fecha_en_mes(anio, mes, rng)
            numero = _generar_numero_mgmt(anio, mes, slug_cli)

            linea = LineaFactura(
                concepto=f"Management fee — {_nombre_mes(mes).capitalize()} {anio}",
                cantidad=1.0,
                precio_unitario=importe_fee,
                iva_tipo=21.0,
                retencion_pct=0.0,
            )
            resumen = ResumenFactura(lineas=[linea])

            datos_plantilla = {
                "numero": numero,
                "fecha": fecha.isoformat(),
                "fecha_vencimiento": date(anio, mes, 28).isoformat(),
                "trimestre": f"T{(mes - 1) // 3 + 1}",
                "emisor": {
                    "nombre": entidad.get("nombre", ""),
                    "cif": entidad.get("cif", ""),
                    "pais": "ESP",
                    "direccion": entidad.get("direccion", ""),
                    "email": entidad.get("email", ""),
                    "banco": entidad.get("banco", ""),
                },
                "receptor": {
                    "nombre": nombre_filial,
                    "cif": cif_filial,
                    "pais": "ESP",
                    "direccion": cliente.get("direccion", ""),
                    "email": cliente.get("email", ""),
                },
                "lineas": [
                    {
                        "concepto": linea.concepto,
                        "cantidad": linea.cantidad,
                        "precio_unitario": linea.precio_unitario,
                        "iva_tipo": linea.iva_tipo,
                        "retencion_pct": linea.retencion_pct,
                        "base": linea.base,
                        "cuota_iva": linea.cuota_iva,
                        "cuota_retencion": linea.cuota_retencion,
                        "total_linea": linea.total_linea,
                    }
                ],
                "resumen": {
                    "base_imponible": resumen.base_imponible,
                    "total_iva": resumen.total_iva,
                    "total_retencion": resumen.total_retencion,
                    "total": resumen.total,
                    "total_eur": resumen.total_eur,
                    "divisa": "EUR",
                    "tasaconv": 1.0,
                    "desglose_iva": resumen.desglose_iva(),
                },
                "codimpuesto": "IVA21",
                "pagado": True,
            }

            metadatos = {
                "tipo": "factura_compra",
                "subtipo": "intercompany",
                "fecha": fecha.isoformat(),
                "trimestre": f"T{(mes - 1) // 3 + 1}",
                "numero": numero,
                "emisor": entidad.get("nombre", ""),
                "emisor_cif": entidad.get("cif", ""),
                "receptor": nombre_filial,
                "receptor_cif": cif_filial,
                "base": resumen.base_imponible,
                "iva": resumen.total_iva,
                "retencion": resumen.total_retencion,
                "total": resumen.total,
                "total_eur": resumen.total_eur,
                "divisa": "EUR",
                "mes": mes,
            }

            nombre_archivo = (
                f"{fecha.isoformat()}_management-fee_{slug_cli}_{numero}.pdf"
            )

            docs.append(DocGenerado(
                archivo=nombre_archivo,
                tipo="factura_compra",
                subtipo="intercompany",
                plantilla="factura_servicios.html",
                css_variante="corporativo",
                datos_plantilla=datos_plantilla,
                metadatos=metadatos,
                error_inyectado=None,
                edge_case=None,
            ))

    return docs


# ---------------------------------------------------------------------------
# Intereses de prestamos intercompany (trimestrales)
# ---------------------------------------------------------------------------

def _generar_intereses_prestamo(
    entidad: dict,
    anio: int,
    rng: random.Random,
    intercompany: dict,
) -> List[DocGenerado]:
    """
    Genera 4 recibos trimestrales de intereses por cada prestamo que la entidad
    recibe del holding (prestamo_importe + prestamo_interes en intercompany).
    """
    docs: List[DocGenerado] = []

    saldo = float(intercompany.get("prestamo_importe", 0))
    interes_anual = float(intercompany.get("prestamo_interes", 0))
    prestamista = intercompany.get("prestamo_de", "Holding")

    if saldo <= 0 or interes_anual <= 0:
        return docs

    interes_trimestral = _redondear(saldo * interes_anual / 100 / 4)

    for trimestre, mes in enumerate(_MESES_TRIMESTRE, start=1):
        fecha = generar_fecha_en_mes(anio, mes, rng)

        datos_plantilla = {
            "banco": entidad.get("banco", ""),
            "titular": {
                "nombre": entidad.get("nombre", ""),
                "cif": entidad.get("cif", ""),
                "iban": entidad.get("banco", ""),
            },
            "tipo_recibo": "intereses_prestamo_intercompany",
            "concepto": (
                f"Intereses prestamo intercompany T{trimestre}/{anio} "
                f"— Prestamista: {prestamista}"
            ),
            "fecha": fecha.isoformat(),
            "detalle": [
                {
                    "descripcion": (
                        f"Intereses T{trimestre} sobre prestamo de {prestamista} "
                        f"(saldo {saldo:,.2f} EUR, {interes_anual}% anual)"
                    ),
                    "importe": interes_trimestral,
                }
            ],
            "total": interes_trimestral,
        }

        metadatos = {
            "tipo": "recibo_bancario",
            "subtipo": "intercompany_intereses",
            "fecha": fecha.isoformat(),
            "trimestre": f"T{trimestre}",
            "importe_intereses": interes_trimestral,
            "saldo_prestamo": saldo,
            "interes_anual": interes_anual,
            "prestamista": prestamista,
            "receptor": entidad.get("nombre", ""),
            "receptor_cif": entidad.get("cif", ""),
        }

        nombre_archivo = (
            f"{fecha.isoformat()}_intereses-prestamo-intercompany_T{trimestre}.pdf"
        )

        docs.append(DocGenerado(
            archivo=nombre_archivo,
            tipo="recibo_bancario",
            subtipo="intercompany_intereses",
            plantilla="recibo_bancario.html",
            css_variante="corporativo",
            datos_plantilla=datos_plantilla,
            metadatos=metadatos,
            error_inyectado=None,
            edge_case=None,
        ))

    return docs


# ---------------------------------------------------------------------------
# Dividendos (solo holding, en diciembre)
# ---------------------------------------------------------------------------

def _generar_dividendos(
    entidad: dict,
    anio: int,
    rng: random.Random,
    intercompany: dict,
) -> List[DocGenerado]:
    """
    Genera recibos de dividendos recibidos por el holding de sus filiales.
    Solo genera si la entidad tiene intercompany.dividendos_recibidos con bruto > 0.
    Cada dividendo produce un recibo con desglose bruto/retencion/neto (EC14).
    """
    docs: List[DocGenerado] = []
    dividendos_recibidos = intercompany.get("dividendos_recibidos", {})

    for slug_filial, datos_div in dividendos_recibidos.items():
        bruto = float(datos_div.get("bruto", 0))
        if bruto <= 0:
            continue

        retencion = _redondear(bruto * 0.19)
        neto = _redondear(bruto - retencion)

        # Verificar coherencia con los datos del YAML si existen los campos
        if "retencion_19pct" in datos_div:
            retencion = float(datos_div["retencion_19pct"])
            neto = _redondear(bruto - retencion)
        if "neto" in datos_div:
            neto = float(datos_div["neto"])

        fecha = generar_fecha_en_mes(anio, 12, rng)

        nombre_filial_display = slug_filial.replace("-", " ").title()

        datos_plantilla = {
            "banco": entidad.get("banco", ""),
            "titular": {
                "nombre": entidad.get("nombre", ""),
                "cif": entidad.get("cif", ""),
                "iban": entidad.get("banco", ""),
            },
            "tipo_recibo": "dividendo",
            "concepto": (
                f"Dividendo recibido de {nombre_filial_display} — ejercicio {anio}"
            ),
            "fecha": fecha.isoformat(),
            "detalle": [
                {
                    "descripcion": (
                        f"Dividendo bruto distribuido por {nombre_filial_display}"
                    ),
                    "importe": _redondear(bruto),
                },
                {
                    "descripcion": "Retencion IRPF/IS 19% (art. 94 LIRPF / art. 60 LIS)",
                    "importe": -retencion,
                },
            ],
            "total": neto,
        }

        metadatos = {
            "tipo": "recibo_bancario",
            "subtipo": "dividendo",
            "fecha": fecha.isoformat(),
            "dividendo_bruto": _redondear(bruto),
            "retencion_19pct": retencion,
            "dividendo_neto": neto,
            "filial": slug_filial,
            "receptor": entidad.get("nombre", ""),
            "receptor_cif": entidad.get("cif", ""),
        }

        nombre_archivo = (
            f"{fecha.isoformat()}_dividendo_{slug_filial}_{anio}.pdf"
        )

        docs.append(DocGenerado(
            archivo=nombre_archivo,
            tipo="recibo_bancario",
            subtipo="dividendo",
            plantilla="recibo_bancario.html",
            css_variante="corporativo",
            datos_plantilla=datos_plantilla,
            metadatos=metadatos,
            error_inyectado=None,
            edge_case="EC14",
        ))

    return docs


# ---------------------------------------------------------------------------
# Prestamo cruzado estacional EC23 (catering-costa -> chiringuito)
# ---------------------------------------------------------------------------

def _generar_prestamo_cruzado(
    entidad: dict,
    anio: int,
    rng: random.Random,
    intercompany: dict,
) -> List[DocGenerado]:
    """
    Genera el desembolso (abril) y devolucion + intereses (octubre) del prestamo
    cruzado estacional que catering-costa otorga a chiringuito-sol-arena (EC23).
    Solo aplica a la entidad que tiene prestamo_cruzado_a configurado.
    """
    docs: List[DocGenerado] = []

    destinatario_slug = intercompany.get("prestamo_cruzado_a")
    if not destinatario_slug:
        return docs

    importe = float(intercompany.get("prestamo_cruzado_importe", 5000))
    interes_anual = float(intercompany.get("prestamo_cruzado_interes", 3.0))

    # Meses activos del prestamo: de abril a octubre (7 meses)
    meses_prestamo = intercompany.get("prestamo_cruzado_meses", [4, 5, 6, 7, 8, 9, 10])
    n_meses = len(meses_prestamo)

    # Intereses totales proporcionales a los meses del prestamo
    intereses = _redondear(importe * interes_anual / 100 * n_meses / 12)
    total_devolucion = _redondear(importe + intereses)

    nombre_destinatario = destinatario_slug.replace("-", " ").title()

    # --- Desembolso en abril (salida de caja) ---
    mes_desembolso = meses_prestamo[0] if meses_prestamo else 4
    fecha_desembolso = generar_fecha_en_mes(anio, mes_desembolso, rng)

    datos_desembolso = {
        "banco": entidad.get("banco", ""),
        "titular": {
            "nombre": entidad.get("nombre", ""),
            "cif": entidad.get("cif", ""),
            "iban": entidad.get("banco", ""),
        },
        "tipo_recibo": "desembolso_prestamo_intercompany",
        "concepto": (
            f"Desembolso prestamo cruzado estacional a {nombre_destinatario}"
        ),
        "fecha": fecha_desembolso.isoformat(),
        "detalle": [
            {
                "descripcion": (
                    f"Prestamo estacional a {nombre_destinatario} "
                    f"(abr-oct {anio}, {interes_anual}% anual)"
                ),
                "importe": -importe,
            }
        ],
        "total": -importe,
    }

    metadatos_desembolso = {
        "tipo": "recibo_bancario",
        "subtipo": "intercompany",
        "fecha": fecha_desembolso.isoformat(),
        "importe": importe,
        "movimiento": "salida",
        "destinatario": destinatario_slug,
        "emisor": entidad.get("nombre", ""),
        "emisor_cif": entidad.get("cif", ""),
    }

    docs.append(DocGenerado(
        archivo=f"{fecha_desembolso.isoformat()}_prestamo-cruzado-desembolso_{destinatario_slug}.pdf",
        tipo="recibo_bancario",
        subtipo="intercompany",
        plantilla="recibo_bancario.html",
        css_variante="corporativo",
        datos_plantilla=datos_desembolso,
        metadatos=metadatos_desembolso,
        error_inyectado=None,
        edge_case="EC23",
    ))

    # --- Devolucion + intereses en octubre (entrada de caja) ---
    mes_devolucion = meses_prestamo[-1] if meses_prestamo else 10
    fecha_devolucion = generar_fecha_en_mes(anio, mes_devolucion, rng)

    datos_devolucion = {
        "banco": entidad.get("banco", ""),
        "titular": {
            "nombre": entidad.get("nombre", ""),
            "cif": entidad.get("cif", ""),
            "iban": entidad.get("banco", ""),
        },
        "tipo_recibo": "devolucion_prestamo_intercompany",
        "concepto": (
            f"Devolucion prestamo cruzado + intereses de {nombre_destinatario}"
        ),
        "fecha": fecha_devolucion.isoformat(),
        "detalle": [
            {
                "descripcion": f"Principal prestamo devuelto por {nombre_destinatario}",
                "importe": importe,
            },
            {
                "descripcion": (
                    f"Intereses {n_meses} meses al {interes_anual}% anual"
                ),
                "importe": intereses,
            },
        ],
        "total": total_devolucion,
    }

    metadatos_devolucion = {
        "tipo": "recibo_bancario",
        "subtipo": "intercompany",
        "fecha": fecha_devolucion.isoformat(),
        "importe": total_devolucion,
        "principal": importe,
        "intereses": intereses,
        "movimiento": "entrada",
        "origen": destinatario_slug,
        "receptor": entidad.get("nombre", ""),
        "receptor_cif": entidad.get("cif", ""),
    }

    docs.append(DocGenerado(
        archivo=f"{fecha_devolucion.isoformat()}_prestamo-cruzado-devolucion_{destinatario_slug}.pdf",
        tipo="recibo_bancario",
        subtipo="intercompany",
        plantilla="recibo_bancario.html",
        css_variante="corporativo",
        datos_plantilla=datos_devolucion,
        metadatos=metadatos_devolucion,
        error_inyectado=None,
        edge_case="EC23",
    ))

    return docs


# ---------------------------------------------------------------------------
# Funcion principal
# ---------------------------------------------------------------------------

def generar_intercompany(
    entidad: dict,
    anio: int,
    rng: random.Random,
) -> List[DocGenerado]:
    """
    Genera todos los documentos intercompany de una entidad para el ejercicio.

    Solo aplica a entidades con la clave intercompany configurada.
    Produce segun el caso:
    - Management fees mensuales (12 facturas por filial)
    - Recibos de intereses trimestrales (4 por prestamo recibido)
    - Recibos de dividendos recibidos (solo holding, diciembre, EC14)
    - Prestamo cruzado estacional: desembolso abril + devolucion octubre (EC23)
    """
    intercompany = entidad.get("intercompany")
    if not intercompany:
        return []

    docs: List[DocGenerado] = []

    # 1. Management fees (holding -> filiales via clientes configurados)
    docs.extend(_generar_management_fees(entidad, anio, rng, intercompany))

    # 2. Intereses de prestamo recibido del holding (filiales que pagan al holding)
    docs.extend(_generar_intereses_prestamo(entidad, anio, rng, intercompany))

    # 3. Dividendos recibidos (solo holding: tiene dividendos_recibidos)
    if "dividendos_recibidos" in intercompany:
        docs.extend(_generar_dividendos(entidad, anio, rng, intercompany))

    # 4. Prestamo cruzado estacional EC23 (catering-costa -> chiringuito)
    if intercompany.get("prestamo_cruzado_a"):
        docs.extend(_generar_prestamo_cruzado(entidad, anio, rng, intercompany))

    return docs
