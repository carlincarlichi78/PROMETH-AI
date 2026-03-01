"""Motor de coherencia fiscal post-OCR.

Validador puro sin dependencias externas. Verifica que los datos extraídos
por OCR sean fiscalmente coherentes antes de pasar al score Gate 0.

Jerarquía de checks:
  - Bloqueos duros: CIF inválido, suma no cuadra → score 0
  - Alertas: penalizan el score final (nunca bloquean)
"""
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

# ---------------------------------------------------------------------------
# Patrones regex para identificadores fiscales
# ---------------------------------------------------------------------------

# CIF personas jurídicas españolas: letra + 7 dígitos + letra o dígito
_RE_CIF_ES = re.compile(r'^[ABCDEFGHJKLMNPQRSUVW]\d{7}[0-9A-J]$', re.IGNORECASE)

# NIF personas físicas: 8 dígitos + letra de control
_RE_NIF_FISICO = re.compile(r'^\d{8}[TRWAGMYFPDXBNJZSQVHLCKE]$', re.IGNORECASE)

# NIE extranjeros residentes: X/Y/Z + 7 dígitos + letra
_RE_NIE = re.compile(r'^[XYZ]\d{7}[TRWAGMYFPDXBNJZSQVHLCKE]$', re.IGNORECASE)

# CIF intracomunitario: 2 letras país + 2-12 alfanuméricos
_RE_INTRA = re.compile(r'^[A-Z]{2}[A-Z0-9]{2,12}$', re.IGNORECASE)

# Prefijos país válidos para IVA intracomunitario (ISO 3166-1 alpha-2 + XI para N.Irlanda)
_PAISES_INTRA = {
    "AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "EL", "ES", "FI", "FR",
    "GB", "GR", "HR", "HU", "IE", "IT", "LT", "LU", "LV", "MT", "NL", "PL",
    "PT", "RO", "SE", "SI", "SK", "XI",
}

# Penalizaciones por alerta (puntos sobre 100)
_PEN_IMPORTE_NO_POSITIVO = 20
_PEN_CONCEPTO_VACIO = 10
_PEN_FECHA_FUERA_RANGO = 15
_PEN_CIF_AUSENTE = 5
_ANOS_RANGO_FECHA = 5

# Tolerancia suma: 1%
_TOL_SUMA = 0.01


# ---------------------------------------------------------------------------
# Resultado
# ---------------------------------------------------------------------------

@dataclass
class ResultadoCoherencia:
    score: float
    errores_graves: list = field(default_factory=list)
    alertas: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# Validación CIF / NIF
# ---------------------------------------------------------------------------

def _cif_valido(cif: str) -> bool:
    """Devuelve True si el identificador fiscal tiene formato válido."""
    if not cif:
        return False
    cif = cif.strip().upper()
    if _RE_CIF_ES.match(cif) or _RE_NIF_FISICO.match(cif) or _RE_NIE.match(cif):
        return True
    # Intracomunitario: requiere prefijo país válido
    if _RE_INTRA.match(cif) and cif[:2].upper() in _PAISES_INTRA:
        return True
    return False


# ---------------------------------------------------------------------------
# Función principal
# ---------------------------------------------------------------------------

def verificar_coherencia_fiscal(datos_ocr: dict) -> ResultadoCoherencia:
    """Verifica coherencia fiscal de los datos extraídos por OCR.

    Args:
        datos_ocr: dict con claves: emisor_cif, base_imponible, iva_importe,
                   total, fecha_factura, concepto.

    Returns:
        ResultadoCoherencia con score [0-100], errores_graves y alertas.
    """
    errores: list[str] = []
    alertas: list[str] = []
    penalizacion = 0.0

    emisor_cif: str = datos_ocr.get("emisor_cif", "") or ""
    base: Optional[float] = datos_ocr.get("base_imponible")
    iva: Optional[float] = datos_ocr.get("iva_importe")
    total: Optional[float] = datos_ocr.get("total")
    fecha_str: str = datos_ocr.get("fecha_factura", "") or ""
    concepto: str = datos_ocr.get("concepto", "") or ""

    # ------------------------------------------------------------------
    # Bloqueos duros
    # ------------------------------------------------------------------

    # 1. CIF inválido (solo si hay CIF — vacío es alerta, no bloqueo)
    if emisor_cif and not _cif_valido(emisor_cif):
        errores.append(f"CIF/NIF inválido: '{emisor_cif}'")

    # 2. Suma no cuadra: base + iva ≠ total (tolerancia 1%)
    if base is not None and iva is not None and total is not None:
        esperado = base + iva
        if abs(esperado) > 0:
            desviacion = abs(total - esperado) / abs(esperado)
            if desviacion > _TOL_SUMA:
                errores.append(
                    f"Suma no cuadra: base({base}) + iva({iva}) = {esperado:.2f} ≠ total({total})"
                )

    # Si hay errores graves, score = 0 y salir
    if errores:
        return ResultadoCoherencia(score=0.0, errores_graves=errores, alertas=alertas)

    # ------------------------------------------------------------------
    # Alertas (penalizan score)
    # ------------------------------------------------------------------

    # 3. Importe no positivo
    if total is not None and total <= 0:
        alertas.append("Importe total no positivo o negativo")
        penalizacion += _PEN_IMPORTE_NO_POSITIVO

    # 4. Concepto vacío
    if not concepto.strip():
        alertas.append("Concepto vacío o ausente")
        penalizacion += _PEN_CONCEPTO_VACIO

    # 5. Fecha fuera de rango (> N años atrás o futura)
    if fecha_str:
        try:
            # Soporta formatos ISO y DD/MM/YYYY
            if "/" in fecha_str:
                partes = fecha_str.split("/")
                if len(partes) == 3:
                    dia, mes, anio = int(partes[0]), int(partes[1]), int(partes[2])
                    fecha = date(anio, mes, dia)
                else:
                    raise ValueError
            else:
                fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()

            hoy = date.today()
            limite_min = date(hoy.year - _ANOS_RANGO_FECHA, hoy.month, hoy.day)
            if fecha < limite_min or fecha > hoy:
                alertas.append(f"Fecha fuera de rango esperado: {fecha_str}")
                penalizacion += _PEN_FECHA_FUERA_RANGO
        except (ValueError, AttributeError):
            alertas.append(f"Formato de fecha no reconocible: '{fecha_str}'")
            penalizacion += _PEN_FECHA_FUERA_RANGO

    # 6. CIF ausente (alerta leve)
    if not emisor_cif.strip():
        alertas.append("CIF/NIF del emisor ausente")
        penalizacion += _PEN_CIF_AUSENTE

    score = max(0.0, 100.0 - penalizacion)
    return ResultadoCoherencia(score=score, errores_graves=errores, alertas=alertas)
