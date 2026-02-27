"""
Generador de recibos de seguros para el generador de datos de prueba contable.
Produce DocGenerado listos para renderizar a PDF via Jinja2 + weasyprint.

Los seguros en Espana estan exentos de IVA. En su lugar pueden llevar IPS
(Impuesto sobre Primas de Seguros, tipo general 8%) que NO es IVA deducible.
Seguros de vida, salud y algunos ramos especiales estan exentos tambien de IPS.
"""

import random
import sys
from datetime import date
from pathlib import Path
from typing import List

DIR_GENERADOR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DIR_GENERADOR))

from generadores.gen_facturas import DocGenerado, _slug
from utils.etiquetas import etiquetas_para_proveedor, formato_para_proveedor
from utils.variaciones import generar_variaciones_css, css_custom_properties_str
from utils.ruido import perfil_para_proveedor
from utils.fechas import generar_fecha_en_mes
from utils.importes import _redondear


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

# Tipos de seguro que llevan IPS (Impuesto sobre Primas de Seguros, 8%)
# Los seguros de salud/vida/accidentes personales estan exentos de IPS
_IPS_POR_TIPO: dict[str, bool] = {
    "rc": True,           # Responsabilidad civil: lleva IPS
    "multirriesgo": True, # Multirriesgo local: lleva IPS
    "vehiculo": True,     # Vehiculo/coche: lleva IPS
    "credito": True,      # Seguro de credito: lleva IPS
    "transporte": True,   # Mercancias en transito: lleva IPS
    "salud": False,       # Salud: exento de IPS (art. 12.1 Ley IPS)
    "vida": False,        # Vida: exento de IPS
    "accidentes": False,  # Accidentes personales: exento de IPS
}

IPS_TIPO = 8.0  # Tipo impositivo IPS vigente (porcentaje)

# Nombres descriptivos para cada tipo de seguro
_NOMBRE_SEGURO: dict[str, str] = {
    "rc": "Seguro de Responsabilidad Civil Profesional",
    "multirriesgo": "Seguro Multirriesgo Oficina/Local Comercial",
    "vehiculo": "Seguro de Vehiculo de Empresa",
    "credito": "Seguro de Credito Comercial",
    "transporte": "Seguro de Mercancias en Transito",
    "salud": "Seguro Medico-Sanitario Colectivo",
    "vida": "Seguro de Vida Vinculado a Prestamo",
    "accidentes": "Seguro de Accidentes Personales",
}

# Contador para numerar polizas ficticias
_contadores_seguro: dict[str, int] = {}

# Meses de inicio segun frecuencia trimestral
_MESES_TRIMESTRAL = [1, 4, 7, 10]

# Mapeo familia seguro -> plantilla v2
_FAMILIAS_SEGURO: dict[str, str] = {
    "seguro_grande": "seguros/G01_seguro_grande.html",
    "seguro_mutua": "seguros/G02_seguro_mutua.html",
    "seguro_recibo": "seguros/G03_seguro_recibo.html",
}


def _familia_para_seguro(nombre_proveedor: str, seed: int) -> str:
    """Asigna familia de plantilla a un proveedor de seguros (determinista)."""
    rng = random.Random(hash(nombre_proveedor) + seed + 5003)
    return rng.choice(list(_FAMILIAS_SEGURO.keys()))


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _numero_poliza(tipo: str, cif_entidad: str) -> str:
    """Genera un numero de poliza ficticio pero realista."""
    clave = f"{tipo}-{cif_entidad}"
    _contadores_seguro[clave] = _contadores_seguro.get(clave, 0) + 1
    prefijo = tipo[:3].upper()
    return f"POL-{prefijo}-{cif_entidad[-4:]}-{_contadores_seguro[clave]:03d}"


def _numero_referencia_recibo(tipo: str, anio: int, mes: int) -> str:
    """Genera una referencia de recibo bancario para cobro de prima de seguro."""
    return f"RCB-{anio}{mes:02d}-SEG-{tipo[:3].upper()}"


def _calcular_desglose_seguro(
    importe_anual: float,
    tiene_ips: bool,
    fraccion: int = 1,
) -> dict[str, float]:
    """
    Calcula el desglose de un recibo de seguro.

    Parametros:
        importe_anual: prima anual total (con IPS incluido si aplica)
        tiene_ips: si el seguro lleva IPS (8%)
        fraccion: divisor de la prima anual (1=anual, 4=trimestral)

    Retorna dict con: prima_neta, ips_cuota, total
    """
    prima_total_fraccion = _redondear(importe_anual / fraccion)

    if tiene_ips:
        # El importe_anual incluye IPS: descomponer
        # prima_neta * (1 + 0.08) = prima_total_fraccion
        prima_neta = _redondear(prima_total_fraccion / (1 + IPS_TIPO / 100))
        ips_cuota = _redondear(prima_total_fraccion - prima_neta)
    else:
        prima_neta = prima_total_fraccion
        ips_cuota = 0.0

    total = _redondear(prima_neta + ips_cuota)
    return {
        "prima_neta": prima_neta,
        "ips_cuota": ips_cuota,
        "total": total,
    }


def _banco_entidad(entidad: dict, nombre_proveedor: str) -> str:
    """
    Determina el banco cobrador del recibo.
    Los seguros se cobran por domiciliacion bancaria desde la cuenta del asegurado.
    """
    # Usar banco de la entidad o uno ficticio generico
    banco = entidad.get("banco", "ES00 0000 0000 0000 0000 0000")
    return banco


# ---------------------------------------------------------------------------
# Generador principal
# ---------------------------------------------------------------------------

def generar_seguros(
    entidad: dict,
    anio: int,
    rng: random.Random,
    seed: int = 42,
) -> List[DocGenerado]:
    """
    Genera recibos de seguros segun entidad["gastos_recurrentes"]["seguros"].

    Para cada seguro:
    - frecuencia "anual": 1 recibo en enero (o fecha de renovacion si se indica)
    - frecuencia "trimestral": 4 recibos en enero, abril, julio, octubre

    Los seguros son EXENTOS de IVA. Algunos llevan IPS (8%) que no es deducible.
    """
    docs: List[DocGenerado] = []
    seguros = entidad.get("gastos_recurrentes", {}).get("seguros", [])
    if not seguros:
        return docs

    nombre_entidad = entidad.get("nombre", "")
    cif_entidad = entidad.get("cif", "")
    banco_entidad = _banco_entidad(entidad, "")

    for seguro in seguros:
        tipo = seguro.get("tipo", "rc")
        nombre_proveedor = seguro.get("proveedor", "Aseguradora S.A.")
        importe_anual = float(seguro.get("importe_anual", 0))
        frecuencia = seguro.get("frecuencia", "anual")

        # Saltar seguros con importe 0 (desactivados)
        if importe_anual <= 0:
            continue

        tiene_ips = _IPS_POR_TIPO.get(tipo, True)
        nombre_concepto = _NOMBRE_SEGURO.get(tipo, f"Seguro {tipo.upper()}")
        slug_proveedor = _slug(nombre_proveedor)
        numero_poliza = _numero_poliza(tipo, cif_entidad)

        # v2: familia determinista por nombre proveedor, etiquetas y variaciones
        familia_v2 = _familia_para_seguro(nombre_proveedor, seed)
        plantilla_v2 = _FAMILIAS_SEGURO[familia_v2]
        etiquetas = etiquetas_para_proveedor(nombre_proveedor, seed)
        formato = formato_para_proveedor(nombre_proveedor, seed)
        variaciones = generar_variaciones_css(nombre_proveedor, familia_v2, seed)
        perfil = perfil_para_proveedor(nombre_proveedor, seed)
        fmt_numero_id = formato["numero"]["id"]

        if frecuencia == "trimestral":
            meses_recibo = _MESES_TRIMESTRAL
            fraccion = 4
        else:
            # Anual: enero por defecto, o fecha_renovacion si se especifica
            mes_renovacion = seguro.get("mes_renovacion", 1)
            meses_recibo = [mes_renovacion]
            fraccion = 1

        for mes in meses_recibo:
            fecha = generar_fecha_en_mes(anio, mes, rng)
            desglose = _calcular_desglose_seguro(importe_anual, tiene_ips, fraccion)
            referencia = _numero_referencia_recibo(tipo, anio, mes)
            nombre_archivo = f"{anio}-{mes:02d}_seguro_{tipo}_{slug_proveedor}.pdf"

            # Detalle del recibo para la plantilla
            detalle_recibo = [
                {"concepto": "Prima neta", "importe": desglose["prima_neta"]},
            ]
            if tiene_ips and desglose["ips_cuota"] > 0:
                detalle_recibo.append({
                    "concepto": f"IPS (Impuesto sobre Primas de Seguros {IPS_TIPO:.0f}%)",
                    "importe": desglose["ips_cuota"],
                })
            detalle_recibo.append({
                "concepto": "TOTAL RECIBO",
                "importe": desglose["total"],
            })

            # Recargo Consorcio Compensacion Seguros (~2% sobre prima neta para seguros con IPS)
            recargo_consorcio = _redondear(desglose["prima_neta"] * 0.02) if tiene_ips else 0.0

            # Coberturas desglosadas para plantillas G01/G02
            coberturas = [
                {
                    "concepto": nombre_concepto,
                    "capital": _redondear(desglose["prima_neta"] * rng.uniform(8, 15)),
                    "prima": desglose["prima_neta"],
                },
            ]

            datos_plantilla = {
                "banco": banco_entidad,
                "titular": {
                    "nombre": nombre_entidad,
                    "cif": cif_entidad,
                },
                "aseguradora": {
                    "nombre": nombre_proveedor,
                    "nif": seguro.get("cif", ""),
                    "direccion": seguro.get("direccion", ""),
                },
                "tomador": {
                    "nombre": nombre_entidad,
                    "nif": cif_entidad,
                    "direccion": entidad.get("direccion", ""),
                },
                "poliza": {
                    "numero": numero_poliza,
                    "tipo": nombre_concepto,
                    "vigencia_desde": f"01/01/{anio}",
                    "vigencia_hasta": f"31/12/{anio}",
                },
                "tipo_recibo": "seguro",
                "referencia": numero_poliza,
                "concepto": nombre_concepto,
                "proveedor": nombre_proveedor,
                "fecha": fecha.isoformat(),
                "referencia_recibo": referencia,
                "detalle": detalle_recibo,
                "prima_neta": desglose["prima_neta"],
                "ips_cuota": desglose["ips_cuota"],
                "ips": desglose["ips_cuota"],
                "tiene_ips": tiene_ips,
                "recargo_consorcio": recargo_consorcio,
                "coberturas": coberturas,
                "total": desglose["total"],
                "frecuencia": frecuencia,
                "anio": anio,
                "mes": mes,
                # v2: etiquetas, variaciones CSS y formato numero
                "etiquetas": etiquetas,
                "variaciones_css_str": css_custom_properties_str(variaciones),
                "formato_numero_id": fmt_numero_id,
            }

            metadatos = {
                "tipo": "recibo_bancario",
                "subtipo": "seguro",
                "fecha": fecha.isoformat(),
                "mes": mes,
                "anio": anio,
                "tipo_seguro": tipo,
                "proveedor": nombre_proveedor,
                "poliza": numero_poliza,
                "total": desglose["total"],
                # IVA exento: los seguros no generan IVA deducible
                "iva_deducible": False,
                "ips": desglose["ips_cuota"],
            }

            docs.append(DocGenerado(
                archivo=nombre_archivo,
                tipo="recibo_bancario",
                subtipo="seguro",
                plantilla=plantilla_v2,
                css_variante="corporativo",
                datos_plantilla=datos_plantilla,
                metadatos=metadatos,
                error_inyectado=None,
                edge_case=None,
                familia=familia_v2,
                variaciones_css=variaciones,
                etiquetas_usadas=etiquetas,
                formato_fecha=formato["fecha"]["id"],
                formato_numero=fmt_numero_id,
                perfil_calidad=perfil,
            ))

    return docs
