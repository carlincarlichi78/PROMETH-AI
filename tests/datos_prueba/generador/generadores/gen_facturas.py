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
from utils.etiquetas import etiquetas_para_proveedor, formato_para_proveedor, formatear_fecha, formatear_numero
from utils.variaciones import generar_variaciones_css, css_custom_properties_str
from utils.ruido import perfil_para_proveedor


# ---------------------------------------------------------------------------
# Dataclass compartida (usada por todos los generadores)
# ---------------------------------------------------------------------------

@dataclass
class DocGenerado:
    """Documento generado listo para renderizar a PDF."""
    archivo: str          # nombre archivo PDF (ej: "2025-01-15_AWS-Ireland_F2025-0001.pdf")
    tipo: str             # factura_compra, factura_venta, nomina, rlc_ss, recibo_bancario...
    subtipo: str          # estandar, intracomunitaria, simplificada, servicios, nota_credito, restauracion
    plantilla: str        # nombre plantilla HTML (ej: "facturas/F04_pyme_clasica.html")
    css_variante: str     # estilo CSS (corporativo, autonomo, administracion, extranjero)
    datos_plantilla: dict # variables para renderizar con Jinja2
    metadatos: dict       # para manifiesto.json: fecha, base, iva, total, emisor, receptor, etc.
    error_inyectado: str | None = None   # ID error (E01..E15) o None
    edge_case: str | None = None         # ID edge case (EC01..EC25) o None
    # --- Campos v2 ---
    familia: str | None = None           # familia plantilla (ej: "pyme_clasica", "corp_grande")
    variaciones_css: dict = field(default_factory=dict)  # custom properties CSS
    etiquetas_usadas: dict = field(default_factory=dict)  # etiquetas asignadas al proveedor
    formato_fecha: str = "es_barra"      # formato fecha del proveedor
    formato_numero: str = "es_estandar"  # formato numero del proveedor
    perfil_calidad: str = "digital_bueno"  # perfil degradacion
    degradaciones: list = field(default_factory=list)  # degradaciones aplicadas [str]
    provocaciones: list = field(default_factory=list)   # provocaciones aplicadas [str]


# ---------------------------------------------------------------------------
# Constantes de seleccion de plantilla / subtipo
# ---------------------------------------------------------------------------

_CONCEPTOS_RESTAURACION = {
    "carta", "menu", "cubierto", "restaurante", "catering",
    "comida", "cena", "desayuno", "degustacion", "chiringuito",
}

_CONCEPTOS_SIMPLIFICADA = {"ticket", "simplificada"}

# Mapeo familia -> plantilla v2 (en plantillas/facturas/)
_FAMILIAS_PLANTILLA: dict[str, str] = {
    "corp_grande": "facturas/F01_corp_grande.html",
    "corp_limpia": "facturas/F02_corp_limpia.html",
    "corp_industrial": "facturas/F03_corp_industrial.html",
    "pyme_clasica": "facturas/F04_pyme_clasica.html",
    "pyme_moderna": "facturas/F05_pyme_moderna.html",
    "autonomo_basico": "facturas/F06_autonomo_basico.html",
    "autonomo_pro": "facturas/F07_autonomo_pro.html",
    "ticket_tpv": "facturas/F08_ticket_tpv.html",
    "ticket_simplificado": "facturas/F09_ticket_simplificado.html",
    "tabla_densa": "facturas/F10_tabla_densa.html",
    "multi_pagina": "facturas/F11_multi_pagina.html",
    "extranjera_en": "facturas/F12_extranjera_en.html",
    "extranjera_eu": "facturas/F13_extranjera_eu.html",
    "administracion": "facturas/F14_administracion.html",
    "hosteleria": "facturas/F15_hosteleria.html",
    "sanitario": "facturas/F16_sanitario.html",
    "ecommerce": "facturas/F17_ecommerce.html",
    "rectificativa": "facturas/F18_rectificativa.html",
}

# Familias por defecto segun contexto (cuando no se especifica en empresas.yaml)
_FAMILIAS_DEFECTO_COMPRA = [
    "pyme_clasica", "pyme_moderna", "corp_limpia", "autonomo_pro", "tabla_densa",
]
_FAMILIAS_DEFECTO_VENTA = [
    "pyme_clasica", "pyme_moderna", "corp_limpia",
]


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


def _seleccionar_plantilla_compra(proveedor: dict, seed: int) -> tuple[str, str, str]:
    """
    Selecciona plantilla HTML, variante CSS y familia para factura de compra.
    Retorna (plantilla, css_variante, familia).
    Usa familia_factura del YAML si existe, si no asigna por heuristica.
    """
    familia = proveedor.get("familia_factura")
    regimen = proveedor.get("regimen", "general")
    retencion = proveedor.get("retencion", 0)

    # Asignar familia automatica si no viene del YAML
    if not familia:
        if regimen == "intracomunitario":
            familia = "extranjera_eu"
        elif regimen == "extracomunitario":
            familia = "extranjera_en"
        elif retencion and float(retencion) > 0:
            familia = "autonomo_pro"
        else:
            # Familia determinista por nombre proveedor
            rng_fam = random.Random(hash(proveedor.get("nombre", "")) + seed)
            familia = rng_fam.choice(_FAMILIAS_DEFECTO_COMPRA)

    plantilla = _FAMILIAS_PLANTILLA.get(familia, "facturas/F04_pyme_clasica.html")
    css_variante = "extranjero" if "extranjera" in familia else "corporativo"
    return plantilla, css_variante, familia


def _seleccionar_plantilla_venta(entidad: dict, cliente: dict, seed: int) -> tuple[str, str, str]:
    """
    Selecciona plantilla HTML, variante CSS y familia para factura de venta.
    Retorna (plantilla, css_variante, familia).
    Usa familia_factura_venta de la entidad o heuristica.
    """
    familia = entidad.get("familia_factura_venta")
    tipo_entidad = entidad.get("tipo", "sl")
    css_base = entidad.get("css_variante", "corporativo")
    concepto = cliente.get("concepto", "").lower()
    pais = cliente.get("pais", "ESP")
    codimpuesto = cliente.get("codimpuesto", "IVA21")

    # Asignar familia automatica si no viene del YAML
    if not familia:
        if pais != "ESP" and codimpuesto == "IVA0":
            familia = "extranjera_eu"
        elif any(palabra in concepto for palabra in _CONCEPTOS_SIMPLIFICADA):
            familia = "ticket_simplificado"
        elif tipo_entidad == "restaurante" or any(
            palabra in concepto for palabra in _CONCEPTOS_RESTAURACION
        ):
            familia = "hosteleria"
        elif tipo_entidad == "autonomo":
            familia = "autonomo_pro"
        else:
            rng_fam = random.Random(hash(entidad.get("nombre", "")) + seed)
            familia = rng_fam.choice(_FAMILIAS_DEFECTO_VENTA)

    plantilla = _FAMILIAS_PLANTILLA.get(familia, "facturas/F04_pyme_clasica.html")
    css_variante = "extranjero" if "extranjera" in familia else css_base
    return plantilla, css_variante, familia


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
    seed: int = 42,
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

        plantilla, css_variante, familia = _seleccionar_plantilla_compra(proveedor, seed)

        # v2: etiquetas, formatos, variaciones CSS y perfil calidad por proveedor
        nombre_prov = proveedor.get("nombre", slug_prov)
        etiquetas = etiquetas_para_proveedor(nombre_prov, seed)
        formato = formato_para_proveedor(nombre_prov, seed)
        variaciones = generar_variaciones_css(nombre_prov, familia, seed)
        perfil = perfil_para_proveedor(nombre_prov, seed)
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

            # v2: formatear fecha y numero segun proveedor
            fecha_fmt = formatear_fecha(fecha, formato["fecha"]["id"])
            fmt_numero_id = formato["numero"]["id"]

            datos_plantilla = {
                "numero": numero,
                "fecha": fecha.isoformat(),
                "fecha_formateada": fecha_fmt,
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
                        "descuento_pct": l.descuento_pct,
                        "iva_tipo": l.iva_tipo,
                        "retencion_pct": l.retencion_pct,
                        "recargo_eq_pct": l.recargo_eq_pct,
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
                # v2: etiquetas y variaciones para las plantillas
                "etiquetas": etiquetas,
                "variaciones_css_str": css_custom_properties_str(variaciones),
                "formato_numero_id": fmt_numero_id,
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
                "familia": familia,
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
                familia=familia,
                variaciones_css=variaciones,
                etiquetas_usadas=etiquetas,
                formato_fecha=formato["fecha"]["id"],
                formato_numero=fmt_numero_id,
                perfil_calidad=perfil,
            ))

    return docs


# ---------------------------------------------------------------------------
# Generador principal de facturas de venta
# ---------------------------------------------------------------------------

def generar_facturas_venta(
    entidad: dict,
    anio: int,
    rng: random.Random,
    seed: int = 42,
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

    # v2: etiquetas y variaciones de la ENTIDAD (emisor en ventas)
    nombre_entidad = entidad.get("nombre", "")
    etiquetas_ent = etiquetas_para_proveedor(nombre_entidad, seed)
    formato_ent = formato_para_proveedor(nombre_entidad, seed)

    for slug_cli, cliente in clientes.items():
        frecuencia = cliente.get("frecuencia", "puntual")
        n = _n_facturas_por_frecuencia(frecuencia, rng)

        fechas = distribuir_fechas(anio, n, rng, meses_activos=meses_activos)

        plantilla, css_variante, familia = _seleccionar_plantilla_venta(entidad, cliente, seed)
        variaciones = generar_variaciones_css(nombre_entidad, familia, seed)
        perfil = perfil_para_proveedor(nombre_entidad, seed)
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

            fecha_fmt = formatear_fecha(fecha, formato_ent["fecha"]["id"])
            fmt_numero_id = formato_ent["numero"]["id"]

            datos_plantilla = {
                "numero": numero,
                "fecha": fecha.isoformat(),
                "fecha_formateada": fecha_fmt,
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
                        "descuento_pct": l.descuento_pct,
                        "iva_tipo": l.iva_tipo,
                        "retencion_pct": l.retencion_pct,
                        "recargo_eq_pct": l.recargo_eq_pct,
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
                "etiquetas": etiquetas_ent,
                "variaciones_css_str": css_custom_properties_str(variaciones),
                "formato_numero_id": fmt_numero_id,
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
                "familia": familia,
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
                familia=familia,
                variaciones_css=variaciones,
                etiquetas_usadas=etiquetas_ent,
                formato_fecha=formato_ent["fecha"]["id"],
                formato_numero=fmt_numero_id,
                perfil_calidad=perfil,
            ))

    return docs
