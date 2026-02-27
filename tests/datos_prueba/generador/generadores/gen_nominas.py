"""
Generador de nominas y documentos SS (RLC) para datos de prueba contable espanol.
Produce DocGenerado listos para renderizar con las plantillas nomina.html y rlc_ss.html.
"""

import random
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import List, Optional

DIR_GENERADOR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DIR_GENERADOR))

from utils.etiquetas import etiquetas_para_proveedor, formato_para_proveedor
from utils.fechas import fechas_mensuales, _ultimo_dia_mes
from utils.importes import CuotaSS, calcular_irpf_nomina, _redondear
from utils.ruido import perfil_para_proveedor
from utils.variaciones import css_custom_properties_str, generar_variaciones_css

# ---------------------------------------------------------------------------
# DocGenerado importado desde gen_facturas cuando exista; definido aqui como
# fallback para que el modulo sea autonomo si gen_facturas no existe todavia.
# ---------------------------------------------------------------------------
try:
    from generadores.gen_facturas import DocGenerado
except ImportError:
    @dataclass
    class DocGenerado:
        """Representa un documento generado listo para renderizar a PDF."""
        archivo: str
        tipo: str
        subtipo: str
        plantilla: str
        css_variante: str
        datos_plantilla: dict
        metadatos: dict = field(default_factory=dict)
        error_inyectado: Optional[str] = None
        edge_case: Optional[str] = None


# ---------------------------------------------------------------------------
# Familias de plantillas v2 para nominas
# ---------------------------------------------------------------------------

_FAMILIAS_NOMINA: dict[str, str] = {
    "a3nom": "nominas/N01_a3nom.html",
    "sage": "nominas/N02_sage.html",
    "meta4": "nominas/N03_meta4.html",
    "factorial": "nominas/N04_factorial.html",
    "gestoria_clasica": "nominas/N05_gestoria_clasica.html",
    "gestoria_pro": "nominas/N06_gestoria_pro.html",
    "sector_publico": "nominas/N07_sector_publico.html",
    "construccion": "nominas/N08_construccion.html",
    "hosteleria_nomina": "nominas/N09_hosteleria_nomina.html",
    "comercio": "nominas/N10_comercio.html",
}

# ---------------------------------------------------------------------------
# Constantes normativas 2025
# ---------------------------------------------------------------------------

# Bases minimas y maximas de cotizacion 2025 (grupo 1 titulados superiores)
BASE_COTIZACION_MIN = 1847.40   # euros/mes
BASE_COTIZACION_MAX = 4909.50   # euros/mes

# Grupos de cotizacion por tipo de contrato/puesto
_GRUPO_COTIZACION_DEFECTO = {
    "indefinido": "1",
    "temporal": "5",
    "formacion": "7",
    "fijo_discontinuo": "5",
    "obra_servicio": "5",
    "practicas": "7",
}

# Nombres de mes en castellano
_NOMBRES_MES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
    5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre",
}


# ---------------------------------------------------------------------------
# Helpers privados
# ---------------------------------------------------------------------------

def _slug(texto: str) -> str:
    """Convierte un nombre en slug apto para nombre de archivo."""
    texto = texto.lower().strip()
    texto = re.sub(r"[áàä]", "a", texto)
    texto = re.sub(r"[éèë]", "e", texto)
    texto = re.sub(r"[íìï]", "i", texto)
    texto = re.sub(r"[óòö]", "o", texto)
    texto = re.sub(r"[úùü]", "u", texto)
    texto = re.sub(r"ñ", "n", texto)
    texto = re.sub(r"[^a-z0-9]+", "_", texto)
    return texto.strip("_")


def _generar_num_ss(rng: random.Random) -> str:
    """Genera numero de SS ficticio con formato XX/XXXXXXXX/XX."""
    provincia = rng.randint(1, 52)
    numero = rng.randint(10000000, 99999999)
    control = rng.randint(10, 99)
    return f"{provincia:02d}/{numero:08d}/{control:02d}"


def _generar_ccc_ss(rng: random.Random) -> str:
    """Genera Codigo de Cuenta de Cotizacion ficticio formato XX/XXXXXXX/XX."""
    provincia = rng.randint(1, 52)
    numero = rng.randint(1000000, 9999999)
    control = rng.randint(10, 99)
    return f"{provincia:02d}/{numero:07d}/{control:02d}"


def _calcular_base_cotizacion(empleado: dict) -> float:
    """
    Calcula la base de cotizacion mensual del empleado.
    Es el salario mensual bruto ajustado a los limites normativos.
    """
    bruto_anual = empleado.get("bruto_anual", 0.0)
    base_mensual = bruto_anual / 12.0
    base_clamped = max(BASE_COTIZACION_MIN, min(base_mensual, BASE_COTIZACION_MAX))
    return _redondear(base_clamped)


def _empleado_activo(empleado: dict, mes: int, meses_activos_entidad: List[int]) -> bool:
    """
    Determina si el empleado esta activo en el mes indicado.
    Los empleados fijo-discontinuos respetan meses_activos_entidad.
    El resto trabajan todos los meses.
    """
    tipo_contrato = empleado.get("tipo_contrato", "indefinido")
    if tipo_contrato == "fijo_discontinuo":
        return mes in meses_activos_entidad
    return True


def _calcular_nomina_mensual(
    empleado: dict,
    mes: int,
    anio: int,
    paga_extra: bool = False,
    rng: Optional[random.Random] = None,
) -> dict:
    """
    Calcula devengos, deducciones y liquido para la nomina del mes indicado.

    Retorna un dict con:
        devengos, deducciones, total_devengos, total_deducciones, liquido,
        ss_empresa (desglose costes empresa), base_cotizacion
    """
    bruto_anual = float(empleado.get("bruto_anual", 0.0))
    extras = empleado.get("extras", {}) or {}
    tipo_contrato = empleado.get("tipo_contrato", "indefinido")

    # Determinar si las pagas extra estan prorrateadas o separadas
    pagas_prorrateadas = extras.get("pagas_prorrateadas", False)
    divisor = 14 if not pagas_prorrateadas else 12

    salario_base_mensual = _redondear(bruto_anual / divisor)

    # --- Devengos ---
    devengos = []

    if paga_extra:
        # Paga extra: solo salario base de un mes (sin complementos habituales)
        devengos.append({"concepto": "Paga extraordinaria", "importe": salario_base_mensual})
    else:
        devengos.append({"concepto": "Salario base", "importe": salario_base_mensual})

        # Complemento teletrabajo (exento IRPF hasta 11,33 EUR/dia)
        teletrabajo = float(extras.get("teletrabajo_euros_mes", 0))
        if teletrabajo > 0:
            devengos.append({"concepto": "Complemento teletrabajo", "importe": _redondear(teletrabajo)})

        # Plus nocturnidad
        nocturnidad = float(extras.get("nocturnidad_euros_mes", 0))
        if nocturnidad > 0:
            devengos.append({"concepto": "Plus nocturnidad", "importe": _redondear(nocturnidad)})

        # Plus transporte
        transporte = float(extras.get("transporte_euros_mes", 0))
        if transporte > 0:
            devengos.append({"concepto": "Plus transporte", "importe": _redondear(transporte)})

        # Festivos trabajados
        festivos = float(extras.get("festivos_euros_mes", 0))
        if festivos > 0:
            devengos.append({"concepto": "Festivos trabajados", "importe": _redondear(festivos)})

    total_devengos = _redondear(sum(d["importe"] for d in devengos))

    # --- Base de cotizacion ---
    base_cotizacion = _calcular_base_cotizacion(empleado)
    cuota_ss = CuotaSS(base_cotizacion)

    # --- IRPF ---
    irpf_pct = calcular_irpf_nomina(bruto_anual)

    # --- Deducciones ---
    deducciones = []

    # SS trabajador
    cuota_trabajador = cuota_ss.cuota_trabajador
    deducciones.append({
        "concepto": "Seguridad Social (trabajador)",
        "pct": round(
            cuota_ss.cc_trabajador_pct
            + cuota_ss.desempleo_trabajador_pct
            + cuota_ss.fp_trabajador_pct,
            2,
        ),
        "base": base_cotizacion,
        "importe": cuota_trabajador,
    })

    # IRPF sobre total devengado
    irpf_importe = _redondear(total_devengos * irpf_pct / 100)
    deducciones.append({
        "concepto": "I.R.P.F.",
        "pct": irpf_pct,
        "base": total_devengos,
        "importe": irpf_importe,
    })

    # Anticipo (si aplica)
    anticipo = float(extras.get("anticipo_euros_mes", 0))
    if anticipo > 0 and not paga_extra:
        deducciones.append({
            "concepto": "Anticipo a cuenta",
            "pct": None,
            "base": None,
            "importe": _redondear(anticipo),
        })

    total_deducciones = _redondear(sum(d["importe"] for d in deducciones))
    liquido = _redondear(total_devengos - total_deducciones)

    # --- Costes SS empresa (informativo en nomina) ---
    ss_empresa = {
        "contingencias_comunes": _redondear(base_cotizacion * cuota_ss.contingencias_comunes_pct / 100),
        "desempleo": _redondear(base_cotizacion * cuota_ss.desempleo_pct / 100),
        "fogasa": _redondear(base_cotizacion * cuota_ss.fogasa_pct / 100),
        "fp": _redondear(base_cotizacion * cuota_ss.fp_pct / 100),
        "total": cuota_ss.cuota_empresa,
    }

    return {
        "devengos": devengos,
        "deducciones": deducciones,
        "total_devengos": total_devengos,
        "total_deducciones": total_deducciones,
        "liquido": liquido,
        "ss_empresa": ss_empresa,
        "base_cotizacion": base_cotizacion,
        "irpf_pct": irpf_pct,
    }


# ---------------------------------------------------------------------------
# Helper para datos_plantilla de nominas
# ---------------------------------------------------------------------------

def _datos_plantilla_nomina(
    calculo: dict,
    empresa_datos: dict,
    trabajador_datos: dict,
    mes_nombre: str,
    anio: int,
    ultimo_dia: int,
    *,
    paga_extra: bool = False,
    etiquetas: dict = None,
    variaciones: dict = None,
    formato: dict = None,
) -> dict:
    """
    Construye el dict datos_plantilla para una nomina, compatible con TODAS
    las plantillas N01-N10.

    Centraliza aliases (total_devengado/total_deducido, tipo_pct, naf_ss, etc.)
    y campos derivados (bases_cotizacion, irpf_pct) para evitar duplicacion.
    """
    base_cot = calculo["base_cotizacion"]

    # Enriquecer deducciones con alias tipo_pct (N05 usa tipo_pct, otras usan pct)
    deducciones = []
    for d in calculo["deducciones"]:
        d_copia = dict(d)
        d_copia["tipo_pct"] = d.get("pct")
        deducciones.append(d_copia)

    # Alias en trabajador para compatibilidad con distintas plantillas
    trabajador = dict(trabajador_datos)
    trabajador.setdefault("naf_ss", trabajador.get("num_ss", ""))
    trabajador.setdefault("categoria", trabajador.get("puesto", ""))
    trabajador.setdefault("contrato_tipo", trabajador.get("tipo_contrato", ""))

    # Alias en empresa
    empresa = dict(empresa_datos)
    empresa.setdefault("nif", empresa.get("cif", ""))
    empresa.setdefault("cp", "")
    empresa.setdefault("ciudad", "")

    fmt_numero_id = ""
    if formato:
        fmt_numero_id = formato.get("numero", {}).get("id", "")

    return {
        "empresa": empresa,
        "trabajador": trabajador,
        "periodo": {
            "mes": mes_nombre,
            "anio": anio,
            "dias_trabajados": ultimo_dia,
        },
        "devengos": calculo["devengos"],
        "deducciones": deducciones,
        "total_devengos": calculo["total_devengos"],
        "total_devengado": calculo["total_devengos"],
        "total_deducciones": calculo["total_deducciones"],
        "total_deducido": calculo["total_deducciones"],
        "liquido": calculo["liquido"],
        "ss_empresa": calculo["ss_empresa"],
        "paga_extra": paga_extra,
        "especie": 0,
        "irpf_pct": calculo.get("irpf_pct", 0),
        "bases_cotizacion": {
            "contingencias_comunes": base_cot,
            "accidentes_trabajo": base_cot,
            "horas_extra": 0.0,
            "base_irpf": calculo["total_devengos"],
        },
        "etiquetas": etiquetas or {},
        "variaciones_css_str": css_custom_properties_str(variaciones or {}),
        "formato_numero_id": fmt_numero_id,
    }


# ---------------------------------------------------------------------------
# API publica
# ---------------------------------------------------------------------------

def generar_nominas(entidad: dict, anio: int, rng: random.Random, seed: int = 42) -> List[DocGenerado]:
    """
    Genera nominas mensuales (y pagas extra) para todos los empleados de la entidad.

    Para cada empleado en entidad["empleados_detalle"]:
    - Determina los meses activos segun tipo_contrato y meses_activos de la entidad.
    - Genera una nomina mensual por mes activo.
    - Genera pagas extra en junio y diciembre si no estan prorrateadas.

    Retorna lista de DocGenerado con tipo="nomina".
    """
    empleados = entidad.get("empleados_detalle", [])
    if not empleados:
        return []

    meses_activos_entidad: List[int] = entidad.get("meses_activos", list(range(1, 13)))
    css_variante = entidad.get("css_variante", "corporativo")
    slug_entidad = _slug(entidad.get("nombre", "entidad"))
    nombre_entidad = entidad.get("nombre", "entidad")

    # --- Integracion v2: familia, etiquetas, variaciones, perfil ---
    familia = entidad.get("familia_nomina", "gestoria_clasica")
    plantilla_v2 = _FAMILIAS_NOMINA.get(familia, "nominas/N05_gestoria_clasica.html")
    etiquetas = etiquetas_para_proveedor(nombre_entidad, seed=seed)
    variaciones = generar_variaciones_css(nombre_entidad, familia, seed=seed)
    formato = formato_para_proveedor(nombre_entidad, seed=seed)
    perfil = perfil_para_proveedor(nombre_entidad, seed=seed)

    empresa_datos = {
        "nombre": entidad.get("nombre", ""),
        "cif": entidad.get("cif", ""),
        "direccion": entidad.get("direccion", ""),
        "ccc_ss": _generar_ccc_ss(rng),
    }

    documentos: List[DocGenerado] = []

    for empleado in empleados:
        tipo_contrato = empleado.get("tipo_contrato", "indefinido")
        extras = empleado.get("extras", {}) or {}
        pagas_prorrateadas = extras.get("pagas_prorrateadas", False)
        slug_emp = _slug(empleado.get("nombre", "empleado"))

        # Meses activos para este empleado
        if tipo_contrato == "fijo_discontinuo":
            meses_emp = [m for m in range(1, 13) if m in meses_activos_entidad]
        else:
            meses_emp = list(range(1, 13))

        # Datos fijos del trabajador (num_ss se genera una vez por empleado)
        trabajador_datos = {
            "nombre": empleado.get("nombre", ""),
            "nif": empleado.get("nif", ""),
            "num_ss": _generar_num_ss(rng),
            "puesto": empleado.get("puesto", ""),
            "grupo_cotizacion": _GRUPO_COTIZACION_DEFECTO.get(tipo_contrato, "1"),
            "tipo_contrato": tipo_contrato.replace("_", " ").title(),
            "antiguedad": f"01/01/{anio - rng.randint(0, 8)}",
            "fecha_alta": date(anio - rng.randint(0, 8), 1, 1),
        }

        for mes in meses_emp:
            calculo = _calcular_nomina_mensual(empleado, mes, anio, paga_extra=False, rng=rng)
            ultimo_dia = _ultimo_dia_mes(anio, mes)

            doc = DocGenerado(
                archivo=f"{anio}-{mes:02d}_nomina_{slug_emp}.pdf",
                tipo="nomina",
                subtipo="mensual",
                plantilla=plantilla_v2,
                css_variante=css_variante,
                datos_plantilla=_datos_plantilla_nomina(
                    calculo, empresa_datos, trabajador_datos,
                    _NOMBRES_MES[mes], anio, ultimo_dia,
                    paga_extra=False, etiquetas=etiquetas,
                    variaciones=variaciones, formato=formato,
                ),
                metadatos={
                    "fecha": date(anio, mes, min(28, ultimo_dia)).isoformat(),
                    "entidad_id": slug_entidad,
                    "empleado": empleado.get("nombre", ""),
                    "liquido": calculo["liquido"],
                    "bruto_anual": empleado.get("bruto_anual", 0),
                },
                # campos v2 en DocGenerado
                familia=familia,
                variaciones_css=variaciones,
                etiquetas_usadas=etiquetas,
                formato_fecha=formato["fecha"]["id"],
                formato_numero=formato["numero"]["id"],
                perfil_calidad=perfil,
            )
            documentos.append(doc)

        # Pagas extra en junio y diciembre (si no estan prorrateadas)
        if not pagas_prorrateadas:
            for mes_extra in [6, 12]:
                if mes_extra not in meses_emp:
                    continue
                calculo_extra = _calcular_nomina_mensual(
                    empleado, mes_extra, anio, paga_extra=True, rng=rng
                )
                doc_extra = DocGenerado(
                    archivo=f"{anio}-{mes_extra:02d}_nomina_paga_extra_{slug_emp}.pdf",
                    tipo="nomina",
                    subtipo="paga_extra",
                    plantilla=plantilla_v2,
                    css_variante=css_variante,
                    datos_plantilla=_datos_plantilla_nomina(
                        calculo_extra, empresa_datos, trabajador_datos,
                        _NOMBRES_MES[mes_extra], anio, _ultimo_dia_mes(anio, mes_extra),
                        paga_extra=True, etiquetas=etiquetas,
                        variaciones=variaciones, formato=formato,
                    ),
                    metadatos={
                        "fecha": date(anio, mes_extra, 28).isoformat(),
                        "entidad_id": slug_entidad,
                        "empleado": empleado.get("nombre", ""),
                        "liquido": calculo_extra["liquido"],
                        "bruto_anual": empleado.get("bruto_anual", 0),
                    },
                    # campos v2 en DocGenerado
                    familia=familia,
                    variaciones_css=variaciones,
                    etiquetas_usadas=etiquetas,
                    formato_fecha=formato["fecha"]["id"],
                    formato_numero=formato["numero"]["id"],
                    perfil_calidad=perfil,
                )
                documentos.append(doc_extra)

    return documentos


def generar_ss(entidad: dict, anio: int, rng: random.Random, seed: int = 42) -> List[DocGenerado]:
    """
    Genera un RLC (Relacion de Liquidacion de Cotizaciones) mensual por cada mes
    en que haya al menos un empleado activo.

    Retorna lista de DocGenerado con tipo="rlc_ss".
    """
    empleados = entidad.get("empleados_detalle", [])
    if not empleados:
        return []

    meses_activos_entidad: List[int] = entidad.get("meses_activos", list(range(1, 13)))
    slug_entidad = _slug(entidad.get("nombre", "entidad"))

    empresa_datos = {
        "nombre": entidad.get("nombre", ""),
        "cif": entidad.get("cif", ""),
        "ccc_ss": _generar_ccc_ss(rng),
    }

    documentos: List[DocGenerado] = []

    for mes in range(1, 13):
        # Recoger empleados activos este mes
        activos = [
            emp for emp in empleados
            if _empleado_activo(emp, mes, meses_activos_entidad)
        ]
        if not activos:
            continue

        trabajadores_rlc = []
        suma_base_cc = 0.0
        suma_cuota_empresa = 0.0
        suma_cuota_trabajador = 0.0

        for emp in activos:
            base_cc = _calcular_base_cotizacion(emp)
            cuota_ss = CuotaSS(base_cc)
            tipo_contrato = emp.get("tipo_contrato", "indefinido")

            trabajadores_rlc.append({
                "nombre": emp.get("nombre", ""),
                "nif": emp.get("nif", ""),
                "grupo": _GRUPO_COTIZACION_DEFECTO.get(tipo_contrato, "1"),
                "dias": _ultimo_dia_mes(anio, mes),
                "base_cc": base_cc,
                "base_cp": base_cc,   # base contingencias profesionales = base CC en regimen general
                "cuota_empresa": cuota_ss.cuota_empresa,
                "cuota_trabajador": cuota_ss.cuota_trabajador,
            })

            suma_base_cc = _redondear(suma_base_cc + base_cc)
            suma_cuota_empresa = _redondear(suma_cuota_empresa + cuota_ss.cuota_empresa)
            suma_cuota_trabajador = _redondear(suma_cuota_trabajador + cuota_ss.cuota_trabajador)

        # Desglose de totales que usa la plantilla rlc_ss.html
        cuota_desempleo_empresa = _redondear(suma_base_cc * 0.055)
        fogasa = _redondear(suma_base_cc * 0.002)
        fp_trabajador = _redondear(suma_base_cc * 0.001)

        totales = {
            "base_cc": suma_base_cc,
            "base_desempleo": suma_base_cc,   # en regimen general CC = desempleo
            "cuota_desempleo": cuota_desempleo_empresa,
            "fogasa": fogasa,
            "fp": fp_trabajador,
            "total_empresa": suma_cuota_empresa,
            "total_trabajador": suma_cuota_trabajador,
            "total_ingresar": _redondear(suma_cuota_empresa + suma_cuota_trabajador),
        }

        doc = DocGenerado(
            archivo=f"{anio}-{mes:02d}_RLC_{slug_entidad}.pdf",
            tipo="rlc_ss",
            subtipo="mensual",
            plantilla="rlc_ss.html",
            css_variante="administracion",
            datos_plantilla={
                "empresa": empresa_datos,
                "periodo": {
                    "mes": mes,
                    "anio": anio,
                },
                "trabajadores": trabajadores_rlc,
                "totales": totales,
            },
            metadatos={
                "fecha": date(anio, mes, min(28, _ultimo_dia_mes(anio, mes))).isoformat(),
                "entidad_id": slug_entidad,
                "num_trabajadores": len(trabajadores_rlc),
                "total_ingresar": totales["total_ingresar"],
            },
        )
        documentos.append(doc)

    return documentos
