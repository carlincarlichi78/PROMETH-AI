"""Parser de hints del asunto del email.

Formato: [clave:valor] en cualquier parte del asunto.
Ejemplos:
  '[tipo:FV] [nota:pagada el 15] Factura Mercadona'
  '[tipo:FC][subcuenta:7050] Ventas enero'
"""
import re
from dataclasses import dataclass
from typing import Optional

_PATRON_HINT = re.compile(r'\[(\w+):([^\]]+)\]', re.IGNORECASE)

_TIPOS_VALIDOS = {"FC", "FV", "NC", "NOM", "SUM", "BAN", "RLC", "IMP"}


@dataclass
class HintsEmail:
    tipo_doc: Optional[str] = None
    subcuenta: Optional[str] = None
    nota: Optional[str] = None
    pagada: bool = False
    ejercicio: Optional[str] = None


def extraer_hints_asunto(asunto: str) -> HintsEmail:
    """Extrae hints estructurados del asunto del email.

    Retorna HintsEmail con los campos encontrados. Campos no presentes quedan None/False.
    """
    hints = HintsEmail()
    for match in _PATRON_HINT.finditer(asunto):
        clave = match.group(1).lower()
        valor = match.group(2).strip()
        if clave == "tipo":
            tipo = valor.upper()
            if tipo in _TIPOS_VALIDOS:
                hints.tipo_doc = tipo
        elif clave == "subcuenta":
            hints.subcuenta = valor
        elif clave == "nota":
            hints.nota = valor
        elif clave == "pagada":
            hints.pagada = valor.lower() in ("1", "si", "true", "yes")
        elif clave == "ejercicio":
            hints.ejercicio = valor
    return hints
