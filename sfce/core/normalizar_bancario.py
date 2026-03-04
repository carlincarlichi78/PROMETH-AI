"""
Funciones de normalización para el motor de conciliación bancaria.
"""
import re
import unicodedata
from decimal import Decimal


def normalizar_concepto(texto: str) -> tuple[str, str]:
    """
    Normaliza el concepto bancario en dos niveles.

    Returns:
        (patron_texto, patron_limpio)
        - patron_texto: mayúsculas sin tildes (búsqueda general)
        - patron_limpio: además elimina fechas, IBANs, códigos TPV y frases genéricas
    """
    if not texto:
        return "", ""

    # Paso 1: eliminar tildes
    normalizado = unicodedata.normalize("NFD", texto)
    normalizado = "".join(c for c in normalizado if unicodedata.category(c) != "Mn")
    patron_texto = normalizado.upper().strip()

    # Paso 2: limpieza adicional para patron_limpio
    limpio = patron_texto
    limpio = re.sub(r"\b\d{2}/\d{2}/\d{4}\b", "", limpio)       # DD/MM/YYYY
    limpio = re.sub(r"\b\d{8}\b", "", limpio)                     # DDMMYYYY
    limpio = re.sub(r"\bES\d{20,}\b", "", limpio)                  # IBANs españoles
    limpio = re.sub(r"\b\d{6,}\b", "", limpio)                     # secuencias > 6 dígitos
    limpio = re.sub(r"\bPAGO CON TARJETA EN\b", "", limpio)
    limpio = re.sub(r"\bRECIBO\b", "", limpio)
    limpio = re.sub(r"\bTRANSF(?:ERENCIA)?(?:\s+ORD(?:INARIA)?)?\b", "", limpio)
    limpio = re.sub(r"\bCOMISION\b", "", limpio)
    limpio = " ".join(limpio.split())  # normalizar espacios múltiples

    return patron_texto, limpio


def limpiar_nif(nif: str) -> str:
    """Elimina espacios, guiones y puntos. Devuelve NIF en mayúsculas."""
    return re.sub(r"[\s\-\.]", "", nif).upper()


def rango_importe(importe: Decimal) -> str:
    """Categoriza el importe en rangos para el aprendizaje de patrones."""
    valor = abs(float(importe))
    if valor < 10:
        return "0-10"
    if valor < 100:
        return "10-100"
    if valor < 1000:
        return "100-1000"
    if valor < 10000:
        return "1000-10000"
    return "10000+"
