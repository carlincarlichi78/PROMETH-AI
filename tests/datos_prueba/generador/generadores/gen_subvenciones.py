"""
Generador de documentos de subvenciones para el generador de datos de prueba contable.
Produce resoluciones y recibos bancarios de pago para cada subvencion declarada
en la configuracion de la entidad.
"""

import random
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path
from typing import List

DIR_GENERADOR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DIR_GENERADOR))

from generadores.gen_facturas import DocGenerado
from utils.importes import _redondear
from utils.fechas import generar_fecha_en_mes


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

# Datos ficticios de banco para recibos de ingreso de subvencion
_BANCO_RECEPTOR = "Banco Santander S.A."

# Condiciones genericas que aparecen en toda resolucion de subvencion
_CONDICIONES_GENERICAS = [
    "Destinar el importe a la finalidad para la que fue concedida.",
    "Conservar la documentacion justificativa durante 5 anios.",
    "Facilitar las actuaciones de comprobacion y control de la entidad concedente.",
    "Comunicar cualquier modificacion relevante en las condiciones de la concesion.",
    "No incurrir en las prohibiciones del art. 13 de la Ley General de Subvenciones.",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slug(nombre: str) -> str:
    """Normaliza un nombre para usarlo en nombres de archivo."""
    nfd = unicodedata.normalize("NFD", nombre)
    sin_acentos = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    limpio = re.sub(r"[^a-z0-9]+", "-", sin_acentos.lower())
    return limpio.strip("-")


def _expediente_ficticio(organismo: str, anio: int, rng: random.Random) -> str:
    """Genera un numero de expediente ficticio verosimil."""
    siglas = "".join(p[0].upper() for p in organismo.split()[:3] if p)
    numero = rng.randint(1000, 9999)
    sufijo = rng.randint(100, 999)
    return f"{siglas}/{anio}/{numero}-{sufijo}"


def _firmante_ficticio(organismo: str, rng: random.Random) -> str:
    """Genera un firmante ficticio para la resolucion."""
    nombres = [
        "Directora General de Fondos Europeos",
        "Jefe de Servicio de Ayudas Empresariales",
        "Subdirector General de Innovacion",
        "Delegado Territorial de Agricultura",
        "Director de Programas de Empleo",
        "Secretaria General Tecnica",
    ]
    return rng.choice(nombres)


def _generar_fechas_pagos(
    n_pagos: int,
    fecha_resolucion: date,
    anio: int,
    rng: random.Random,
    subvencion: dict,
) -> List[date]:
    """
    Calcula las fechas de pago segun el numero de pagos y la subvencion.
    Regla especial: PAC se paga en octubre.
    """
    nombre_lower = subvencion.get("nombre", "").lower()

    # PAC: pago unico en octubre
    if "pac" in nombre_lower or "politica agricola" in nombre_lower:
        return [generar_fecha_en_mes(anio, 10, rng)]

    if n_pagos == 1:
        # Pago ~2 meses despues de resolucion
        mes_pago = min(fecha_resolucion.month + 2, 12)
        return [generar_fecha_en_mes(anio, mes_pago, rng)]

    if n_pagos == 2:
        # Primer pago ~2 meses, segundo ~6 meses despues de resolucion
        mes_pago1 = min(fecha_resolucion.month + 2, 12)
        mes_pago2 = min(fecha_resolucion.month + 6, 12)
        return [
            generar_fecha_en_mes(anio, mes_pago1, rng),
            generar_fecha_en_mes(anio, mes_pago2, rng),
        ]

    # Fallback: distribuir pagos uniformemente
    fechas = []
    for i in range(n_pagos):
        mes = min(fecha_resolucion.month + 2 + i * 3, 12)
        fechas.append(generar_fecha_en_mes(anio, mes, rng))
    return fechas


# ---------------------------------------------------------------------------
# Generador de resolucion
# ---------------------------------------------------------------------------

def _generar_resolucion(
    subvencion: dict,
    entidad: dict,
    anio: int,
    fecha_resolucion: date,
    expediente: str,
    firmante: str,
    pagos_detalle: List[dict],
) -> DocGenerado:
    """Genera el DocGenerado de la resolucion de concesion de subvencion."""
    nombre_sub = subvencion.get("nombre", "Subvencion")
    organismo = subvencion.get("organismo", "Organismo concedente")
    importe = float(subvencion.get("importe", 0))
    programa = subvencion.get("programa", nombre_sub)
    slug_nombre = _slug(nombre_sub)

    datos_plantilla = {
        "organismo": organismo,
        "beneficiario": {
            "nombre": entidad.get("nombre", ""),
            "cif": entidad.get("cif", ""),
            "direccion": entidad.get("direccion", ""),
            "email": entidad.get("email", ""),
        },
        "expediente": expediente,
        "programa": programa,
        "importe": _redondear(importe),
        "pagos": pagos_detalle,
        "condiciones": _CONDICIONES_GENERICAS,
        "fecha_resolucion": fecha_resolucion.isoformat(),
        "firmante": firmante,
        "tipo_subvencion": subvencion.get("tipo", "explotacion"),
        "cuenta_contable": subvencion.get("cuenta", "740"),
    }

    metadatos = {
        "tipo": "subvencion",
        "subtipo": "resolucion_subvencion",
        "fecha": fecha_resolucion.isoformat(),
        "importe": _redondear(importe),
        "organismo": organismo,
        "expediente": expediente,
        "receptor": entidad.get("nombre", ""),
        "receptor_cif": entidad.get("cif", ""),
        "tipo_subvencion": subvencion.get("tipo", "explotacion"),
    }

    nombre_archivo = f"{anio}_subvencion_{slug_nombre}.pdf"

    return DocGenerado(
        archivo=nombre_archivo,
        tipo="subvencion",
        subtipo="resolucion_subvencion",
        plantilla="subvencion.html",
        css_variante="administracion",
        datos_plantilla=datos_plantilla,
        metadatos=metadatos,
        error_inyectado=None,
        edge_case=None,
    )


# ---------------------------------------------------------------------------
# Generador de recibo de pago
# ---------------------------------------------------------------------------

def _generar_recibo_pago(
    subvencion: dict,
    entidad: dict,
    anio: int,
    fecha_pago: date,
    importe_pago: float,
    num_pago: int,
    total_pagos: int,
) -> DocGenerado:
    """Genera el DocGenerado del recibo bancario de pago de subvencion."""
    nombre_sub = subvencion.get("nombre", "Subvencion")
    organismo = subvencion.get("organismo", "Organismo concedente")
    slug_nombre = _slug(nombre_sub)

    concepto = (
        f"Ingreso subvencion: {nombre_sub}"
        if total_pagos == 1
        else f"Ingreso subvencion: {nombre_sub} — Pago {num_pago}/{total_pagos}"
    )

    datos_plantilla = {
        "banco": _BANCO_RECEPTOR,
        "titular": {
            "nombre": entidad.get("nombre", ""),
            "cif": entidad.get("cif", ""),
            "iban": entidad.get("banco", ""),
        },
        "tipo_recibo": "ingreso_subvencion",
        "concepto": concepto,
        "fecha": fecha_pago.isoformat(),
        "detalle": [
            {
                "descripcion": f"Pago subvencion {num_pago}/{total_pagos}: {nombre_sub}",
                "organismo": organismo,
                "importe": _redondear(importe_pago),
            }
        ],
        "total": _redondear(importe_pago),
    }

    metadatos = {
        "tipo": "recibo_bancario",
        "subtipo": "subvencion",
        "fecha": fecha_pago.isoformat(),
        "importe_pago": _redondear(importe_pago),
        "organismo": organismo,
        "receptor": entidad.get("nombre", ""),
        "receptor_cif": entidad.get("cif", ""),
        "num_pago": num_pago,
        "total_pagos": total_pagos,
    }

    sufijo_pago = f"_pago{num_pago}" if total_pagos > 1 else ""
    nombre_archivo = f"{fecha_pago.isoformat()}_recibo_subvencion_{slug_nombre}{sufijo_pago}.pdf"

    return DocGenerado(
        archivo=nombre_archivo,
        tipo="recibo_bancario",
        subtipo="subvencion",
        plantilla="recibo_bancario.html",
        css_variante="administracion",
        datos_plantilla=datos_plantilla,
        metadatos=metadatos,
        error_inyectado=None,
        edge_case=None,
    )


# ---------------------------------------------------------------------------
# Funcion principal
# ---------------------------------------------------------------------------

def generar_subvenciones(
    entidad: dict,
    anio: int,
    rng: random.Random,
) -> List[DocGenerado]:
    """
    Genera documentos de subvenciones para una entidad en el ejercicio indicado.

    Por cada subvencion en entidad["subvenciones"] produce:
    - 1 documento de resolucion (tipo: subvencion, subtipo: resolucion_subvencion)
    - N documentos de pago/recibo (tipo: recibo_bancario, subtipo: subvencion)

    Las subvenciones con tarifa plana (reduccion SS) no generan documentos.
    """
    docs: List[DocGenerado] = []
    lista_subvenciones = entidad.get("subvenciones", [])

    for subvencion in lista_subvenciones:
        nombre_sub = subvencion.get("nombre", "")
        importe = float(subvencion.get("importe", 0))
        n_pagos = int(subvencion.get("pagos", 1))
        organismo = subvencion.get("organismo", "Organismo concedente")

        # La tarifa plana es solo reduccion SS, no genera documento
        if "tarifa plana" in nombre_sub.lower():
            continue

        # Fecha de resolucion: entre febrero y abril del anio
        mes_resolucion = rng.randint(2, 4)
        fecha_resolucion = generar_fecha_en_mes(anio, mes_resolucion, rng)

        expediente = _expediente_ficticio(organismo, anio, rng)
        firmante = _firmante_ficticio(organismo, rng)

        # Calcular fechas y distribicion de pagos
        fechas_pago = _generar_fechas_pagos(n_pagos, fecha_resolucion, anio, rng, subvencion)

        # Dividir el importe entre los pagos
        if n_pagos == 1:
            importes_pago = [importe]
        elif n_pagos == 2:
            # Primer pago: 60%, segundo: 40% (patron comun en subvenciones)
            primer_pago = _redondear(importe * 0.60)
            segundo_pago = _redondear(importe - primer_pago)
            importes_pago = [primer_pago, segundo_pago]
        else:
            importe_por_pago = _redondear(importe / n_pagos)
            importes_pago = [importe_por_pago] * (n_pagos - 1)
            importes_pago.append(_redondear(importe - sum(importes_pago[:-1])))

        # Construir detalle de pagos para la resolucion
        pagos_detalle = [
            {
                "num": i + 1,
                "importe": importes_pago[i],
                "fecha_prevista": fechas_pago[i].isoformat() if i < len(fechas_pago) else None,
            }
            for i in range(n_pagos)
        ]

        # Documento de resolucion
        docs.append(_generar_resolucion(
            subvencion=subvencion,
            entidad=entidad,
            anio=anio,
            fecha_resolucion=fecha_resolucion,
            expediente=expediente,
            firmante=firmante,
            pagos_detalle=pagos_detalle,
        ))

        # Documentos de pago (un recibo por cada pago)
        for i, (fecha_pago, importe_pago) in enumerate(
            zip(fechas_pago, importes_pago), start=1
        ):
            docs.append(_generar_recibo_pago(
                subvencion=subvencion,
                entidad=entidad,
                anio=anio,
                fecha_pago=fecha_pago,
                importe_pago=importe_pago,
                num_pago=i,
                total_pagos=n_pagos,
            ))

    return docs
