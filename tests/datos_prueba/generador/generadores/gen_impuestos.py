"""
Generador de recibos de impuestos y tasas municipales/estatales
para el generador de datos de prueba contable.
Produce DocGenerado listos para renderizar a PDF via Jinja2 + weasyprint.

Cubre: IBI, IAE, Tasa basuras, IVTM (vehiculos), Licencia de playa, Multas.
Todos son pagos sin IVA (tributos publicos), mayoria deducibles como gasto.
"""

import random
import sys
from datetime import date
from pathlib import Path
from typing import List

DIR_GENERADOR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DIR_GENERADOR))

from generadores.gen_facturas import DocGenerado, _slug
from utils.fechas import generar_fecha_en_mes
from utils.importes import _redondear


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

# Mes de pago habitual por tipo de impuesto/tasa
_MES_PAGO: dict[str, int] = {
    "ibi": 6,           # IBI: junio (periodo voluntario verano)
    "iae": 1,           # IAE: enero
    "basuras": 3,       # Tasa basuras: marzo (primer semestre)
    "ivtm": 4,          # IVTM: abril (periodo voluntario primavera)
    "licencia_playa": 3, # Licencia de terraza/playa: marzo (antes temporada)
    "multa": 5,         # Multa: mes generico (mayo), se puede personalizar
}

# Organismo emisor por tipo de impuesto
_ORGANISMO: dict[str, str] = {
    "ibi": "Ayuntamiento / Organismo de Gestion Tributaria",
    "iae": "Agencia Tributaria (AEAT) / Ayuntamiento",
    "basuras": "Ayuntamiento / Mancomunidad de Residuos",
    "ivtm": "Ayuntamiento",
    "licencia_playa": "Ayuntamiento / Junta de Andalucia",
    "multa": "Departamento de Recaudacion Municipal",
}

# Concepto descriptivo por tipo
_CONCEPTO: dict[str, str] = {
    "ibi": "Impuesto sobre Bienes Inmuebles (IBI) - Naturaleza Urbana",
    "iae": "Impuesto sobre Actividades Economicas (IAE) - Cuota Municipal",
    "basuras": "Tasa por Prestacion del Servicio de Recogida de Basuras y RSU",
    "ivtm": "Impuesto sobre Vehiculos de Traccion Mecanica (IVTM)",
    "licencia_playa": "Tasa por Ocupacion de Dominio Publico Maritimo-Terrestre",
    "multa": "Sancion por Infraccion en Materia de Circulacion / Ordenanza Municipal",
}

# Deducibilidad fiscal (las multas NO son gasto deducible en IS/IRPF)
_DEDUCIBLE: dict[str, bool] = {
    "ibi": True,
    "iae": True,
    "basuras": True,
    "ivtm": True,
    "licencia_playa": True,
    "multa": False,
}

# Prefijos para referencias catastrales y matriculas ficticias
_MUNICIPIOS_CATASTRO = ["46250", "29601", "41091", "03014", "08019"]
_LETRAS_MATRICULA = ["A", "B", "C", "D", "F", "G", "H", "J", "K", "L", "M"]

# Contador para numeracion de expedientes
_contadores_impuesto: dict[str, int] = {}


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _referencia_catastral(rng: random.Random) -> str:
    """Genera una referencia catastral ficticia con formato valido."""
    municipio = rng.choice(_MUNICIPIOS_CATASTRO)
    poligono = rng.randint(1, 99)
    parcela = rng.randint(1, 999)
    control = "".join(rng.choices("ABCDEFGHJKLMNPQRSTUVWXYZ", k=2))
    return f"{municipio}{poligono:02d}{parcela:03d}UR{control}"


def _matricula_ficticia(rng: random.Random) -> str:
    """Genera una matricula de vehiculo ficticia con formato espanol actual."""
    numeros = rng.randint(1000, 9999)
    letras = "".join(rng.choices(_LETRAS_MATRICULA, k=3))
    return f"{numeros} {letras}"


def _numero_expediente(tipo: str, anio: int) -> str:
    """Genera un numero de expediente/liquidacion para el impuesto."""
    clave = f"{tipo}-{anio}"
    _contadores_impuesto[clave] = _contadores_impuesto.get(clave, 0) + 1
    prefijo = tipo[:3].upper()
    return f"EXP-{prefijo}-{anio}-{_contadores_impuesto[clave]:04d}"


def _tipo_gravamen_texto(tipo: str, importe: float, base: float) -> str:
    """Genera el texto del tipo de gravamen o descripcion de cuota."""
    if base > 0 and importe != base:
        pct = _redondear(importe / base * 100)
        return f"{pct:.2f}%"
    return "Cuota fija"


def _construir_doc_impuesto(
    tipo: str,
    impuesto: dict,
    entidad: dict,
    anio: int,
    mes: int,
    rng: random.Random,
    referencia_extra: str = "",
) -> DocGenerado:
    """
    Construye un DocGenerado para un impuesto/tasa concreto.

    Centraliza la logica comun a todos los tipos de impuesto.
    """
    importe = float(impuesto.get("importe", 0))
    nombre_entidad = entidad.get("nombre", "")
    cif_entidad = entidad.get("cif", "")
    direccion_entidad = entidad.get("direccion", "")

    organismo = _ORGANISMO.get(tipo, "Administracion Publica")
    concepto = _CONCEPTO.get(tipo, f"Tributo {tipo.upper()}")
    deducible = _DEDUCIBLE.get(tipo, True)
    expediente = _numero_expediente(tipo, anio)

    fecha = generar_fecha_en_mes(anio, mes, rng)
    # Fecha limite de pago: 30 dias desde la fecha de notificacion (simplificado)
    dia_limite = min(fecha.day + 30, 28)
    mes_limite = mes + 1 if mes < 12 else 1
    anio_limite = anio if mes < 12 else anio + 1
    fecha_limite = date(anio_limite, mes_limite, dia_limite).isoformat()

    # Para multas: la base y el tipo gravamen no aplican de igual forma
    base_imponible = importe if tipo == "multa" else importe
    tipo_gravamen = _tipo_gravamen_texto(tipo, importe, base_imponible)

    referencia = referencia_extra or expediente
    nombre_archivo = f"{anio}-{mes:02d}_impuesto_{tipo}.pdf"

    datos_plantilla = {
        "organismo": organismo,
        "obligado": {
            "nombre": nombre_entidad,
            "cif": cif_entidad,
            "direccion": direccion_entidad,
        },
        "concepto": concepto,
        "ejercicio": anio,
        "referencia": referencia,
        "expediente": expediente,
        "periodo": f"Ejercicio {anio}",
        "base_imponible": base_imponible,
        "tipo_gravamen": tipo_gravamen,
        "importe": importe,
        "fecha_limite": fecha_limite,
        "domiciliado": True,
        "deducible": deducible,
        "fecha": fecha.isoformat(),
    }

    metadatos = {
        "tipo": "impuesto_tasa",
        "subtipo": tipo,
        "fecha": fecha.isoformat(),
        "mes": mes,
        "anio": anio,
        "organismo": organismo,
        "concepto": concepto,
        "referencia": referencia,
        "importe": importe,
        "deducible": deducible,
    }

    return DocGenerado(
        archivo=nombre_archivo,
        tipo="impuesto_tasa",
        subtipo=tipo,
        plantilla="impuesto_tasa.html",
        css_variante="administracion",
        datos_plantilla=datos_plantilla,
        metadatos=metadatos,
        error_inyectado=None,
        edge_case=None,
    )


# ---------------------------------------------------------------------------
# Generadores especializados por tipo de impuesto
# ---------------------------------------------------------------------------

def _generar_ibi(impuesto: dict, entidad: dict, anio: int, rng: random.Random) -> List[DocGenerado]:
    """IBI: anual en junio o fraccionado trimestral."""
    docs = []
    frecuencia = impuesto.get("frecuencia", "anual")
    importe_total = float(impuesto.get("importe", 0))
    referencia_catastral = _referencia_catastral(rng)

    if frecuencia == "trimestral":
        meses = [3, 6, 9, 12]
        importe_fraccion = _redondear(importe_total / 4)
        for mes in meses:
            imp_fraccion = dict(impuesto)
            imp_fraccion["importe"] = importe_fraccion
            doc = _construir_doc_impuesto("ibi", imp_fraccion, entidad, anio, mes, rng, referencia_catastral)
            # Personalizar nombre archivo para distinguir cada trimestre
            doc = DocGenerado(
                archivo=f"{anio}-{mes:02d}_impuesto_ibi.pdf",
                tipo=doc.tipo,
                subtipo=doc.subtipo,
                plantilla=doc.plantilla,
                css_variante=doc.css_variante,
                datos_plantilla={**doc.datos_plantilla, "periodo": f"T{meses.index(mes)+1}/{anio}"},
                metadatos={**doc.metadatos, "mes": mes},
                error_inyectado=None,
                edge_case=None,
            )
            docs.append(doc)
    else:
        mes = _MES_PAGO["ibi"]
        doc = _construir_doc_impuesto("ibi", impuesto, entidad, anio, mes, rng, referencia_catastral)
        docs.append(doc)

    return docs


def _generar_iae(impuesto: dict, entidad: dict, anio: int, rng: random.Random) -> List[DocGenerado]:
    """IAE: anual en enero. Solo para entidades con facturacion > 1M EUR."""
    importe = float(impuesto.get("importe", 0))
    # Si importe es 0, la entidad esta exenta (facturacion <= 1M)
    if importe <= 0:
        return []
    mes = _MES_PAGO["iae"]
    doc = _construir_doc_impuesto("iae", impuesto, entidad, anio, mes, rng)
    return [doc]


def _generar_basuras(impuesto: dict, entidad: dict, anio: int, rng: random.Random) -> List[DocGenerado]:
    """Tasa basuras: anual en marzo."""
    mes = _MES_PAGO["basuras"]
    doc = _construir_doc_impuesto("basuras", impuesto, entidad, anio, mes, rng)
    return [doc]


def _generar_ivtm(impuesto: dict, entidad: dict, anio: int, rng: random.Random) -> List[DocGenerado]:
    """IVTM: anual en abril, uno por vehiculo de empresa."""
    mes = _MES_PAGO["ivtm"]
    matricula = impuesto.get("matricula") or _matricula_ficticia(rng)
    doc = _construir_doc_impuesto("ivtm", impuesto, entidad, anio, mes, rng, matricula)
    return [doc]


def _generar_licencia_playa(impuesto: dict, entidad: dict, anio: int, rng: random.Random) -> List[DocGenerado]:
    """Licencia de terraza/playa: anual en marzo. Solo para chiringuitos."""
    mes = _MES_PAGO["licencia_playa"]
    referencia = f"CONC-PLAYA-{anio}-{rng.randint(100, 999)}"
    doc = _construir_doc_impuesto("licencia_playa", impuesto, entidad, anio, mes, rng, referencia)
    return [doc]


def _generar_multa(impuesto: dict, entidad: dict, anio: int, rng: random.Random) -> List[DocGenerado]:
    """
    Multa: puntual, NO deducible fiscalmente.
    Genera edge case EC20 (gasto no deducible) para La Marea segun especificacion.
    """
    mes = impuesto.get("mes", _MES_PAGO["multa"])
    referencia_multa = f"MUL-{anio}-{rng.randint(10000, 99999)}"
    doc = _construir_doc_impuesto("multa", impuesto, entidad, anio, mes, rng, referencia_multa)
    # Las multas son edge case: gasto contabilizado pero no deducible en IS
    doc = DocGenerado(
        archivo=doc.archivo,
        tipo=doc.tipo,
        subtipo=doc.subtipo,
        plantilla=doc.plantilla,
        css_variante=doc.css_variante,
        datos_plantilla=doc.datos_plantilla,
        metadatos=doc.metadatos,
        error_inyectado=None,
        edge_case="EC20",  # Gasto no deducible: multas y sanciones
    )
    return [doc]


# ---------------------------------------------------------------------------
# Despachador por tipo
# ---------------------------------------------------------------------------

_GENERADORES_POR_TIPO = {
    "ibi": _generar_ibi,
    "iae": _generar_iae,
    "basuras": _generar_basuras,
    "ivtm": _generar_ivtm,
    "licencia_playa": _generar_licencia_playa,
    "multa": _generar_multa,
}


# ---------------------------------------------------------------------------
# Generador principal
# ---------------------------------------------------------------------------

def generar_impuestos(
    entidad: dict,
    anio: int,
    rng: random.Random,
) -> List[DocGenerado]:
    """
    Genera recibos de impuestos y tasas segun entidad["gastos_recurrentes"]["impuestos"].

    Tipos soportados: ibi, iae, basuras, ivtm, licencia_playa, multa.
    Todos son tributos publicos (sin IVA), la mayoria deducibles como gasto salvo multas.
    """
    docs: List[DocGenerado] = []
    impuestos = entidad.get("gastos_recurrentes", {}).get("impuestos", [])
    if not impuestos:
        return docs

    for impuesto in impuestos:
        tipo = impuesto.get("tipo", "")
        generador_fn = _GENERADORES_POR_TIPO.get(tipo)

        if generador_fn is None:
            # Tipo desconocido: generar documento generico con mes por defecto
            mes = impuesto.get("mes", 1)
            doc = _construir_doc_impuesto(tipo, impuesto, entidad, anio, mes, rng)
            docs.append(doc)
            continue

        nuevos = generador_fn(impuesto, entidad, anio, rng)
        docs.extend(nuevos)

    return docs
