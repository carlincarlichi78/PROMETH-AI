"""Parser para escrituras de constitución de sociedades."""
import re
from dataclasses import dataclass, field
from typing import List


@dataclass
class DatosEscritura:
    cif: str = ""
    denominacion: str = ""
    capital_social: str = ""
    objeto_social: str = ""
    administradores: List[str] = field(default_factory=list)
    domicilio_social: str = ""
    raw_text: str = ""


_CIF = re.compile(r'(?:C\.?I\.?F\.?|NIF/CIF|NIF)[\s:]+([A-Z][0-9]{8})', re.IGNORECASE)
_CIF_BARE = re.compile(r'\b([A-Z][0-9]{8})\b')
_DENOMINACION = re.compile(
    r'(?:DENOMINACI[OÓ]N\s+SOCIAL|RAZ[OÓ]N\s+SOCIAL|Denominacion)[\s:]+([^\n]+)',
    re.IGNORECASE,
)
_CAPITAL = re.compile(r'CAPITAL\s+SOCIAL[\s:]+([^\n]+)', re.IGNORECASE)
_OBJETO = re.compile(r'OBJETO\s+SOCIAL[\s:]+([^\n]+)', re.IGNORECASE)
_ADMIN = re.compile(
    r'ADMINISTRADOR[^\n:]*:\s*([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑa-záéíóúñ\s]+?),\s*DNI',
    re.IGNORECASE,
)
_DOMICILIO = re.compile(r'DOMICILIO\s+SOCIAL[\s:]+([^\n]+)', re.IGNORECASE)


def parsear_escritura(texto: str) -> DatosEscritura:
    """Extrae campos clave de una escritura de constitución en texto plano."""
    datos = DatosEscritura(raw_text=texto)

    # CIF: primero buscar con prefijo, luego bare
    if m := _CIF.search(texto):
        datos.cif = m.group(1).upper()
    elif m := _CIF_BARE.search(texto):
        datos.cif = m.group(1).upper()

    if m := _DENOMINACION.search(texto):
        datos.denominacion = m.group(1).strip()
    if m := _CAPITAL.search(texto):
        datos.capital_social = m.group(1).strip()
    if m := _OBJETO.search(texto):
        datos.objeto_social = m.group(1).strip()
    if m := _DOMICILIO.search(texto):
        datos.domicilio_social = m.group(1).strip()

    datos.administradores = [m.group(1).strip() for m in _ADMIN.finditer(texto)]

    return datos
