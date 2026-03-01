"""Parser para Modelo 036/037 — extrae datos de alta censal AEAT."""
import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class DatosAlta036:
    nif: str = ""
    nombre: str = ""
    domicilio_fiscal: str = ""
    fecha_inicio_actividad: str = ""
    regimen_iva: str = ""
    epigrafe_iae: str = ""
    es_sociedad: bool = False
    tipo_cliente: str = ""  # "autonomo" | "sociedad" | "desconocido"
    raw_text: str = ""


_NIF_PERSONA = re.compile(r'\b([0-9]{8}[A-Z])\b')
_NIF_SOCIEDAD = re.compile(r'\b([A-Z][0-9]{8})\b')
_NOMBRE = re.compile(
    r'(?:Apellidos\s+y\s+nombre|Raz[oó]n\s+social|Nombre)[\s:]+([^\n]+)',
    re.IGNORECASE,
)
_DOMICILIO = re.compile(
    r'(?:Domicilio\s+(?:fiscal|social))[\s:]+([^\n]+)',
    re.IGNORECASE,
)
_FECHA_INICIO = re.compile(
    r'(?:Fecha\s+inicio\s+(?:actividad|de\s+actividad)|Fecha\s+inicio)[\s:]+(\d{2}/\d{2}/\d{4})',
    re.IGNORECASE,
)
_REGIMEN_IVA = re.compile(
    r'(?:R[eé]gimen\s+(?:del\s+)?IVA)[\s:]+([^\n]+)',
    re.IGNORECASE,
)
_EPIGRAFE = re.compile(r'(?:Ep[ií]grafe\s+IAE|IAE)[\s:]+(\d+)', re.IGNORECASE)


def parsear_modelo_036(texto: str) -> DatosAlta036:
    """Extrae campos clave de un Modelo 036/037 en texto plano."""
    datos = DatosAlta036(raw_text=texto)

    m_soc = _NIF_SOCIEDAD.search(texto)
    m_fis = _NIF_PERSONA.search(texto)

    if m_soc:
        datos.nif = m_soc.group(1)
        datos.es_sociedad = True
        datos.tipo_cliente = "sociedad"
    elif m_fis:
        datos.nif = m_fis.group(1)
        datos.es_sociedad = False
        datos.tipo_cliente = "autonomo"
    else:
        datos.tipo_cliente = "desconocido"

    if m := _NOMBRE.search(texto):
        datos.nombre = m.group(1).strip()
    if m := _DOMICILIO.search(texto):
        datos.domicilio_fiscal = m.group(1).strip()
    if m := _FECHA_INICIO.search(texto):
        datos.fecha_inicio_actividad = m.group(1).strip()
    if m := _REGIMEN_IVA.search(texto):
        datos.regimen_iva = m.group(1).strip().lower()
    if m := _EPIGRAFE.search(texto):
        datos.epigrafe_iae = m.group(1).strip()

    return datos
