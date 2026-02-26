"""
Generador principal de facturas de compra y venta para el generador de datos de prueba contable.
Produce DocGenerado listos para renderizar a PDF via Jinja2 + weasyprint.
"""

import random
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import List

DIR_GENERADOR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DIR_GENERADOR))

from utils.fechas import distribuir_fechas, trimestre_de_fecha
from utils.importes import LineaFactura, ResumenFactura, generar_importe_aleatorio


# ---------------------------------------------------------------------------
# Dataclass compartida (usada por todos los generadores)
# ---------------------------------------------------------------------------

@dataclass
class DocGenerado:
    """Documento generado listo para renderizar a PDF."""
    archivo: str          # nombre archivo PDF (ej: "2025-01-15_AWS-Ireland_F2025-0001.pdf")
    tipo: str             # factura_compra, factura_venta, nomina, rlc_ss, recibo_bancario...
    subtipo: str          # estandar, intracomunitaria, simplificada, servicios, nota_credito, restauracion
    plantilla: str        # nombre plantilla HTML (ej: "factura_estandar.html")
    css_variante: str     # estilo CSS (corporativo, autonomo, administracion, extranjero)
    datos_plantilla: dict # variables para renderizar con Jinja2
    metadatos: dict       # para manifiesto.json: fecha, base, iva, total, emisor, receptor, etc.
    error_inyectado: str | None = None   # ID error (E01..E15) o None
    edge_case: str | None = None         # ID edge case (EC01..EC25) o None


# ---------------------------------------------------------------------------
# Constantes de seleccion de plantilla / subtipo
# ---------------------------------------------------------------------------

_CONCEPTOS_RESTAURACION = {
    "carta", "menu", "cubierto", "restaurante", "catering",
    "comida", "cena", "desayuno", "degustacion", "chiringuito",
}

_CONCEPTOS_SIMPLIFICADA = {"ticket", "simplificada"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slug(nombre: str) -> str:
    """Normaliza un nombre para usarlo en nombres de archivo."""
    # Eliminar acentos
    nfd = unicodedata.normalize("NFD", nombre)
    sin_acentos = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    # Minusculas, reemplazar espacios y caracteres no alfanumericos por guion
    limpio = re.sub(r"[^a-z0-9]+", "-", sin_acentos.lower())
    return limpio.strip("-")


def _codimpuesto_a_tipo(codimpuesto: str) -> float:
    """Convierte el codigo de impuesto a porcentaje numerico."""
    tabla = {
        "IVA21": 21.0,
        "IVA10": 10.0,
        "IVA4": 4.0,
        "IVA0": 0.0,
    }
    return tabla.get(codimpuesto.upper(), 21.0)


def _generar_numero_factura(prefijo: str, anio: int, indice: int) -> str:
    """Genera numero de factura con formato estandar."""
    return f"{prefijo}-{anio}-{indice:04d}"


def _generar_lineas(
    concepto: str,
    importe_rango: list,
    iva_tipo: float,
    retencion_pct: float,
    rng: random.Random,
) -> List[LineaFactura]:
    """Genera entre 1 y 3 lineas de factura realistas."""
    n_lineas = rng.randint(1, 3)
    lineas: List[LineaFactura] = []

    # Conceptos secundarios para lineas adicionales
    conceptos_extra = [
        "Gastos de desplazamiento",
        "Material auxiliar",
        "Portes y envios",
        "Horas adicionales",
        "Suministros",
    ]

    importe_min, importe_max = float(importe_rango[0]), float(importe_rango[1])

    for i in range(n_lineas):
        if i == 0:
            concepto_linea = concepto
            # Importe principal: rango completo dividido entre las lineas para no inflar
            rango_min = importe_min / n_lineas if n_lineas > 1 else importe_min
            rango_max = importe_max / n_lineas if n_lineas > 1 else importe_max
        else:
            concepto_linea = rng.choice(conceptos_extra)
            # Lineas extra: importe pequeno, max 15% del rango original
            rango_min = max(1.0, importe_min * 0.03)
            rango_max = max(rango_min + 1.0, importe_max * 0.15)

        precio = generar_importe_aleatorio(rango_min, rango_max, rng)

        lineas.append(LineaFactura(
            concepto=concepto_linea,
            cantidad=1.0,
            precio_unitario=precio,
            iva_tipo=iva_tipo,
            retencion_pct=retencion_pct,
        ))

    return lineas


def _seleccionar_plantilla_compra(proveedor: dict) -> tuple[str, str]:
    """
    Selecciona plantilla HTML y variante CSS para factura de compra.
    Retorna (plantilla, css_variante).
    """
    regimen = proveedor.get("regimen", "general")
    retencion = proveedor.get("retencion", 0)

    if regimen in ("intracomunitario", "extracomunitario"):
        return "factura_extranjera.html", "extranjero"
    if retencion and float(retencion) > 0:
        return "factura_servicios.html", "corporativo"
    return "factura_estandar.html", "corporativo"


def _seleccionar_plantilla_venta(entidad: dict, cliente: dict) -> tuple[str, str]:
    """
    Selecciona plantilla HTML y variante CSS para factura de venta.
    Retorna (plantilla, css_variante).
    """
    tipo_entidad = entidad.get("tipo", "sl")
    css_base = entidad.get("css_variante", "corporativo")
    concepto = cliente.get("concepto", "").lower()
    pais = cliente.get("pais", "ESP")
    codimpuesto = cliente.get("codimpuesto", "IVA21")

    # Cliente extranjero intracomunitario (IVA0 + pais distinto de ESP)
    if pais != "ESP" and codimpuesto == "IVA0":
        return "factura_extranjera.html", "extranjero"

    # Factura simplificada (ticket)
    if any(palabra in concepto for palabra in _CONCEPTOS_SIMPLIFICADA):
        return "factura_simplificada.html", css_base

    # Restauracion: tipo entidad o concepto
    if tipo_entidad == "restaurante" or any(
        palabra in concepto for palabra in _CONCEPTOS_RESTAURACION
    ):
        return "factura_restauracion.html", css_base

    return "factura_estandar.html", css_base


def _detectar_edge_case_compra(proveedor: dict) -> str | None:
    """Detecta si la factura de compra corresponde a un edge case."""
    regimen = proveedor.get("regimen", "general")
    divisa = proveedor.get("divisa", "EUR")

    if regimen == "intracomunitario":
        return "EC09"
    if divisa not in ("EUR", "", None):
        return "EC01"
    return None


def _detectar_edge_case_venta(entidad: dict, cliente: dict) -> str | None:
    """Detecta si la factura de venta corresponde a un edge case."""
    pais = cliente.get("pais", "ESP")
    divisa = cliente.get("divisa", "EUR")
    concepto = cliente.get("concepto", "").lower()
    codimpuesto = cliente.get("codimpuesto", "IVA21")

    if pais != "ESP" and codimpuesto == "IVA0":
        return "EC09"
    if divisa not in ("EUR", "", None):
        return "EC01"
    if any(palabra in concepto for palabra in _CONCEPTOS_SIMPLIFICADA):
        return "EC05"
    return None


def _n_facturas_por_frecuencia(frecuencia: str, rng: random.Random) -> int:
    """Calcula cuantas facturas generar segun la frecuencia del proveedor/cliente."""
    if frecuencia == "mensual":
        return 12
    if frecuencia == "trimestral":
        return 4
    if frecuencia == "anual":
        return 1
    if frecuencia == "puntual":
        return rng.randint(1, 3)
    # Fallback: tratar como puntual
    return rng.randint(1, 3)


# ---------------------------------------------------------------------------
# Generador principal de facturas de compra
# ---------------------------------------------------------------------------

def generar_facturas_compra(
    entidad: dict,
    anio: int,
    rng: random.Random,
) -> List[DocGenerado]:
    """
    Genera las facturas de compra de una entidad para un ejercicio completo.

    Itera sobre entidad["proveedores"] y produce un DocGenerado por factura,
    con plantilla, datos_plantilla y metadatos completos para el manifiesto.
    """
    docs: List[DocGenerado] = []
    proveedores = entidad.get("proveedores", {})
    meses_activos = entidad.get("meses_activos")

    for slug_prov, proveedor in proveedores.items():
        frecuencia = proveedor.get("frecuencia", "puntual")
        n = _n_facturas_por_frecuencia(frecuencia, rng)

        fechas = distribuir_fechas(anio, n, rng, meses_activos=meses_activos)

        plantilla, css_variante = _seleccionar_plantilla_compra(proveedor)
        codimpuesto = proveedor.get("codimpuesto", "IVA21")
        iva_tipo = _codimpuesto_a_tipo(codimpuesto)
        retencion_pct = float(proveedor.get("retencion", 0))
        concepto = proveedor.get("concepto", "Servicios")
        importe_rango = proveedor.get("importe_rango", [100, 500])
        divisa = proveedor.get("divisa", "EUR")
        pais_prov = proveedor.get("pais", "ESP")

        # Tasa de conversion: si divisa != EUR usar valor ficticio verosimil
        tasaconv = 1.0
        if divisa == "USD":
            tasaconv = round(rng.uniform(1.05, 1.15), 4)
        elif divisa not in ("EUR", "", None):
            tasaconv = round(rng.uniform(0.85, 1.25), 4)

        edge_case = _detectar_edge_case_compra(proveedor)
        prefijo_prov = slug_prov.upper().replace("-", "")[:8]

        for indice, fecha in enumerate(fechas, start=1):
            lineas = _generar_lineas(concepto, importe_rango, iva_tipo, retencion_pct, rng)
            resumen = ResumenFactura(lineas=lineas, divisa=divisa, tasaconv=tasaconv)

            numero = _generar_numero_factura(prefijo_prov, anio, indice)
            slug_archivo = _slug(proveedor.get("nombre", slug_prov))
            nombre_archivo = f"{fecha.isoformat()}_{slug_archivo}_{numero}.pdf"

            # Subtipo segun regimen
            regimen = proveedor.get("regimen", "general")
            if regimen == "intracomunitario":
                subtipo = "intracomunitaria"
            elif regimen == "extracomunitario":
                subtipo = "extracomunitaria"
            elif retencion_pct > 0:
                subtipo = "servicios"
            else:
                subtipo = "estandar"

            datos_plantilla = {
                "numero": numero,
                "fecha": fecha.isoformat(),
                "fecha_vencimiento": date(fecha.year, fecha.month, min(fecha.day + 30, 28)).isoformat(),
                "trimestre": trimestre_de_fecha(fecha),
                "emisor": {
                    "nombre": proveedor.get("nombre", ""),
                    "cif": proveedor.get("cif", ""),
                    "vat": proveedor.get("vat", ""),
                    "pais": pais_prov,
                    "direccion": proveedor.get("direccion", ""),
                    "email": proveedor.get("email", ""),
                    "banco": proveedor.get("banco", ""),
                },
                "receptor": {
                    "nombre": entidad.get("nombre", ""),
                    "cif": entidad.get("cif", ""),
                    "pais": "ESP",
                    "direccion": entidad.get("direccion", ""),
                    "email": entidad.get("email", ""),
                },
                "lineas": [
                    {
                        "concepto": l.concepto,
                        "cantidad": l.cantidad,
                        "precio_unitario": l.precio_unitario,
                        "iva_tipo": l.iva_tipo,
                        "retencion_pct": l.retencion_pct,
                        "base": l.base,
                        "cuota_iva": l.cuota_iva,
                        "cuota_retencion": l.cuota_retencion,
                        "total_linea": l.total_linea,
                    }
                    for l in lineas
                ],
                "resumen": {
                    "base_imponible": resumen.base_imponible,
                    "total_iva": resumen.total_iva,
                    "total_retencion": resumen.total_retencion,
                    "total": resumen.total,
                    "total_eur": resumen.total_eur,
                    "divisa": divisa,
                    "tasaconv": tasaconv,
                    "desglose_iva": resumen.desglose_iva(),
                },
                "codimpuesto": codimpuesto,
                "pagado": True,
            }

            metadatos = {
                "tipo": "factura_compra",
                "subtipo": subtipo,
                "fecha": fecha.isoformat(),
                "trimestre": trimestre_de_fecha(fecha),
                "numero": numero,
                "emisor": proveedor.get("nombre", ""),
                "emisor_cif": proveedor.get("cif", ""),
                "receptor": entidad.get("nombre", ""),
                "receptor_cif": entidad.get("cif", ""),
                "base": resumen.base_imponible,
                "iva": resumen.total_iva,
                "retencion": resumen.total_retencion,
                "total": resumen.total,
                "total_eur": resumen.total_eur,
                "divisa": divisa,
                "codimpuesto": codimpuesto,
                "pais_emisor": pais_prov,
                "plantilla": plantilla,
            }

            docs.append(DocGenerado(
                archivo=nombre_archivo,
                tipo="factura_compra",
                subtipo=subtipo,
                plantilla=plantilla,
                css_variante=css_variante,
                datos_plantilla=datos_plantilla,
                metadatos=metadatos,
                error_inyectado=None,
                edge_case=edge_case,
            ))

    return docs


# ---------------------------------------------------------------------------
# Generador principal de facturas de venta
# ---------------------------------------------------------------------------

def generar_facturas_venta(
    entidad: dict,
    anio: int,
    rng: random.Random,
) -> List[DocGenerado]:
    """
    Genera las facturas de venta de una entidad para un ejercicio completo.

    Itera sobre entidad["clientes"] y produce un DocGenerado por factura,
    con plantilla, datos_plantilla y metadatos completos para el manifiesto.
    """
    docs: List[DocGenerado] = []
    clientes = entidad.get("clientes", {})
    meses_activos = entidad.get("meses_activos")
    serie_entidad = entidad.get("cif", "F")[:1].upper()

    for slug_cli, cliente in clientes.items():
        frecuencia = cliente.get("frecuencia", "puntual")
        n = _n_facturas_por_frecuencia(frecuencia, rng)

        fechas = distribuir_fechas(anio, n, rng, meses_activos=meses_activos)

        plantilla, css_variante = _seleccionar_plantilla_venta(entidad, cliente)
        codimpuesto = cliente.get("codimpuesto", "IVA21")
        iva_tipo = _codimpuesto_a_tipo(codimpuesto)
        retencion_pct = float(cliente.get("retencion", 0))
        concepto = cliente.get("concepto", "Servicios profesionales")
        importe_rango = cliente.get("importe_rango", [500, 3000])
        divisa = cliente.get("divisa", "EUR")
        pais_cli = cliente.get("pais", "ESP")

        # Tasa de conversion para divisas extranjeras
        tasaconv = 1.0
        if divisa == "USD":
            tasaconv = round(rng.uniform(1.05, 1.15), 4)
        elif divisa not in ("EUR", "", None):
            tasaconv = round(rng.uniform(0.85, 1.25), 4)

        edge_case = _detectar_edge_case_venta(entidad, cliente)

        # Subtipo
        concepto_lower = concepto.lower()
        if pais_cli != "ESP" and codimpuesto == "IVA0":
            subtipo = "intracomunitaria"
        elif any(p in concepto_lower for p in _CONCEPTOS_SIMPLIFICADA):
            subtipo = "simplificada"
        elif entidad.get("tipo") == "restaurante" or any(
            p in concepto_lower for p in _CONCEPTOS_RESTAURACION
        ):
            subtipo = "restauracion"
        elif retencion_pct > 0:
            subtipo = "servicios"
        else:
            subtipo = "estandar"

        prefijo_venta = f"{serie_entidad}{slug_cli[:4].upper()}"

        for indice, fecha in enumerate(fechas, start=1):
            lineas = _generar_lineas(concepto, importe_rango, iva_tipo, retencion_pct, rng)
            resumen = ResumenFactura(lineas=lineas, divisa=divisa, tasaconv=tasaconv)

            numero = _generar_numero_factura(prefijo_venta, anio, indice)
            slug_archivo = _slug(cliente.get("nombre", slug_cli))
            nombre_archivo = f"{fecha.isoformat()}_{slug_archivo}_{numero}.pdf"

            datos_plantilla = {
                "numero": numero,
                "fecha": fecha.isoformat(),
                "fecha_vencimiento": date(fecha.year, fecha.month, min(fecha.day + 30, 28)).isoformat(),
                "trimestre": trimestre_de_fecha(fecha),
                "emisor": {
                    "nombre": entidad.get("nombre", ""),
                    "cif": entidad.get("cif", ""),
                    "pais": "ESP",
                    "direccion": entidad.get("direccion", ""),
                    "email": entidad.get("email", ""),
                    "banco": entidad.get("banco", ""),
                    "telefono": entidad.get("telefono", ""),
                },
                "receptor": {
                    "nombre": cliente.get("nombre", ""),
                    "cif": cliente.get("cif", ""),
                    "vat": cliente.get("vat", ""),
                    "pais": pais_cli,
                    "direccion": cliente.get("direccion", ""),
                    "email": cliente.get("email", ""),
                },
                "lineas": [
                    {
                        "concepto": l.concepto,
                        "cantidad": l.cantidad,
                        "precio_unitario": l.precio_unitario,
                        "iva_tipo": l.iva_tipo,
                        "retencion_pct": l.retencion_pct,
                        "base": l.base,
                        "cuota_iva": l.cuota_iva,
                        "cuota_retencion": l.cuota_retencion,
                        "total_linea": l.total_linea,
                    }
                    for l in lineas
                ],
                "resumen": {
                    "base_imponible": resumen.base_imponible,
                    "total_iva": resumen.total_iva,
                    "total_retencion": resumen.total_retencion,
                    "total": resumen.total,
                    "total_eur": resumen.total_eur,
                    "divisa": divisa,
                    "tasaconv": tasaconv,
                    "desglose_iva": resumen.desglose_iva(),
                },
                "codimpuesto": codimpuesto,
                "pagado": True,
            }

            metadatos = {
                "tipo": "factura_venta",
                "subtipo": subtipo,
                "fecha": fecha.isoformat(),
                "trimestre": trimestre_de_fecha(fecha),
                "numero": numero,
                "emisor": entidad.get("nombre", ""),
                "emisor_cif": entidad.get("cif", ""),
                "receptor": cliente.get("nombre", ""),
                "receptor_cif": cliente.get("cif", ""),
                "base": resumen.base_imponible,
                "iva": resumen.total_iva,
                "retencion": resumen.total_retencion,
                "total": resumen.total,
                "total_eur": resumen.total_eur,
                "divisa": divisa,
                "codimpuesto": codimpuesto,
                "pais_receptor": pais_cli,
                "plantilla": plantilla,
            }

            docs.append(DocGenerado(
                archivo=nombre_archivo,
                tipo="factura_venta",
                subtipo=subtipo,
                plantilla=plantilla,
                css_variante=css_variante,
                datos_plantilla=datos_plantilla,
                metadatos=metadatos,
                error_inyectado=None,
                edge_case=edge_case,
            ))

    return docs
