"""Clasificador de documentos para onboarding masivo."""
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

import pdfplumber


class TipoDocOnboarding(str, Enum):
    CENSO_036_037             = "censo_036_037"
    ESCRITURA_CONSTITUCION    = "escritura_constitucion"
    ESTATUTOS                 = "estatutos"
    IS_ANUAL_200              = "is_anual_200"
    IS_FRACCIONADO_202        = "is_fraccionado_202"
    IVA_TRIMESTRAL_303        = "iva_trimestral_303"
    IVA_ANUAL_390             = "iva_anual_390"
    IRPF_FRACCIONADO_130      = "irpf_fraccionado_130"
    IRPF_MODULOS_131          = "irpf_modulos_131"
    IRPF_ANUAL_100            = "irpf_anual_100"
    RETENCIONES_111           = "retenciones_111"
    RETENCIONES_115           = "retenciones_115"
    RETENCIONES_190           = "retenciones_190"
    ARRENDAMIENTO_180         = "arrendamiento_180"
    OPERACIONES_347           = "operaciones_347"
    ATRIBUCION_RENTAS_184     = "atribucion_rentas_184"
    LIBRO_FACTURAS_EMITIDAS   = "libro_facturas_emitidas"
    LIBRO_FACTURAS_RECIBIDAS  = "libro_facturas_recibidas"
    LIBRO_BIENES_INVERSION    = "libro_bienes_inversion"
    SUMAS_Y_SALDOS            = "sumas_y_saldos"
    PRESUPUESTO_CCPP          = "presupuesto_ccpp"
    DESCONOCIDO               = "desconocido"


@dataclass
class ResultadoClasificacion:
    tipo: TipoDocOnboarding
    confianza: float
    texto_extraido: Optional[str] = None
    error: Optional[str] = None


# Patrones por orden de especificidad (mas especifico primero)
_PATRONES_PDF = [
    (TipoDocOnboarding.CENSO_036_037,          r"MODELO\s+03[67]"),
    (TipoDocOnboarding.IS_ANUAL_200,           r"MODELO\s+200"),
    (TipoDocOnboarding.IS_FRACCIONADO_202,     r"MODELO\s+202"),
    (TipoDocOnboarding.IVA_TRIMESTRAL_303,     r"MODELO\s+303"),
    (TipoDocOnboarding.IVA_ANUAL_390,          r"MODELO\s+390"),
    (TipoDocOnboarding.IRPF_FRACCIONADO_130,   r"MODELO\s+130"),
    (TipoDocOnboarding.IRPF_MODULOS_131,       r"MODELO\s+131"),
    (TipoDocOnboarding.IRPF_ANUAL_100,         r"MODELO\s+100\b"),
    (TipoDocOnboarding.RETENCIONES_111,        r"MODELO\s+111"),
    (TipoDocOnboarding.RETENCIONES_115,        r"MODELO\s+115"),
    (TipoDocOnboarding.RETENCIONES_190,        r"MODELO\s+190"),
    (TipoDocOnboarding.ARRENDAMIENTO_180,      r"MODELO\s+180"),
    (TipoDocOnboarding.OPERACIONES_347,        r"MODELO\s+347"),
    (TipoDocOnboarding.ATRIBUCION_RENTAS_184,  r"MODELO\s+184"),
    (TipoDocOnboarding.ESCRITURA_CONSTITUCION, r"ESCRITURA\s+(DE\s+)?CONSTITU"),
    (TipoDocOnboarding.ESTATUTOS,              r"ESTATUTOS\s+(SOCIALES|DE\s+LA)"),
]

# Columnas clave por tipo de CSV
_COLUMNAS_EMITIDAS = {"nif destinatario", "nombre destinatario", "serie"}
_COLUMNAS_RECIBIDAS = {"nif emisor", "nombre emisor", "numero factura"}
_COLUMNAS_BIENES = {"descripcion del bien", "fecha inicio utilizacion", "porcentaje deduccion"}
_COLUMNAS_SUMAS = {"saldo deudor", "saldo acreedor", "subcuenta"}


def clasificar_documento(ruta: Path) -> ResultadoClasificacion:
    """Clasifica un documento y devuelve su tipo con confianza."""
    sufijo = ruta.suffix.lower()

    if sufijo in (".csv", ".xlsx", ".xls"):
        return _clasificar_tabular(ruta)
    elif sufijo == ".pdf":
        return _clasificar_pdf(ruta)
    else:
        return ResultadoClasificacion(
            tipo=TipoDocOnboarding.DESCONOCIDO, confianza=0.0)


def _clasificar_pdf(ruta: Path) -> ResultadoClasificacion:
    try:
        with pdfplumber.open(str(ruta)) as pdf:
            texto = "\n".join(
                p.extract_text() or "" for p in pdf.pages[:3]
            ).upper()
    except Exception as exc:
        return ResultadoClasificacion(
            tipo=TipoDocOnboarding.DESCONOCIDO,
            confianza=0.0,
            error=str(exc),
        )

    if len(texto.strip()) < 20:
        return ResultadoClasificacion(
            tipo=TipoDocOnboarding.DESCONOCIDO,
            confianza=0.1,
            texto_extraido=texto,
        )

    for tipo, patron in _PATRONES_PDF:
        if re.search(patron, texto, re.IGNORECASE):
            return ResultadoClasificacion(
                tipo=tipo, confianza=0.92, texto_extraido=texto)

    return ResultadoClasificacion(
        tipo=TipoDocOnboarding.DESCONOCIDO,
        confianza=0.2,
        texto_extraido=texto,
    )


def _clasificar_tabular(ruta: Path) -> ResultadoClasificacion:
    try:
        if ruta.suffix.lower() == ".csv":
            import pandas as pd
            df = pd.read_csv(str(ruta), sep=None, engine="python", nrows=2)
        else:
            import pandas as pd
            df = pd.read_excel(str(ruta), nrows=2)
        cols = {c.strip().lower() for c in df.columns}
    except Exception as exc:
        return ResultadoClasificacion(
            tipo=TipoDocOnboarding.DESCONOCIDO,
            confianza=0.0, error=str(exc))

    if _COLUMNAS_EMITIDAS <= cols:
        return ResultadoClasificacion(
            tipo=TipoDocOnboarding.LIBRO_FACTURAS_EMITIDAS, confianza=0.9)
    if _COLUMNAS_RECIBIDAS <= cols:
        return ResultadoClasificacion(
            tipo=TipoDocOnboarding.LIBRO_FACTURAS_RECIBIDAS, confianza=0.9)
    if _COLUMNAS_BIENES & cols:
        return ResultadoClasificacion(
            tipo=TipoDocOnboarding.LIBRO_BIENES_INVERSION, confianza=0.85)
    if _COLUMNAS_SUMAS & cols:
        return ResultadoClasificacion(
            tipo=TipoDocOnboarding.SUMAS_Y_SALDOS, confianza=0.85)

    return ResultadoClasificacion(
        tipo=TipoDocOnboarding.DESCONOCIDO, confianza=0.3)
