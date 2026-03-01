"""Gate 0: preflight, trust levels, scoring y decision automatica."""
import hashlib
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

from sfce.core.coherencia_fiscal import ResultadoCoherencia

logger = logging.getLogger(__name__)

MAX_BYTES = 25 * 1024 * 1024  # 25 MB


# --- Trust Levels ---

class TrustLevel(str, Enum):
    MAXIMA = "MAXIMA"   # sistema, certigestor
    ALTA = "ALTA"       # gestor, asesor
    MEDIA = "MEDIA"     # email empresa conocida
    BAJA = "BAJA"       # cliente directo, email anonimo


_FUENTES_MAXIMA = {"sistema", "certigestor", "worker_interno"}
_FUENTES_ALTA = {"portal_gestor", "gestor", "asesor"}
_ROLES_ALTA = {"asesor", "admin_gestoria", "superadmin"}


def calcular_trust_level(fuente: str, rol: str = "") -> TrustLevel:
    """Determina el nivel de confianza segun el origen del documento."""
    if fuente in _FUENTES_MAXIMA:
        return TrustLevel.MAXIMA
    if fuente in _FUENTES_ALTA or rol in _ROLES_ALTA:
        return TrustLevel.ALTA
    if fuente == "email_empresa_conocida":
        return TrustLevel.MEDIA
    return TrustLevel.BAJA


# --- Preflight ---

class ErrorPreflight(ValueError):
    pass


@dataclass
class ResultadoPreflight:
    sha256: str
    duplicado: bool
    tamano_bytes: int
    nombre_sanitizado: str


def ejecutar_preflight(
    ruta_archivo: str,
    empresa_id: int,
    sesion,
    nombre_original: str = "",
) -> ResultadoPreflight:
    """Valida el archivo y detecta duplicados por SHA256."""
    from sfce.core.seguridad_archivos import sanitizar_nombre_archivo
    from sfce.core.validador_pdf import validar_pdf, ErrorValidacionPDF
    from sfce.db.modelos import ColaProcesamiento
    from sqlalchemy import select

    ruta = Path(ruta_archivo)
    if not ruta.exists():
        raise ErrorPreflight(f"Archivo no encontrado: {ruta_archivo}")

    contenido = ruta.read_bytes()
    tamano = len(contenido)

    if tamano == 0:
        raise ErrorPreflight("Archivo vacio")
    if tamano > MAX_BYTES:
        raise ErrorPreflight(f"Excede tamano maximo: {tamano / 1024 / 1024:.1f} MB > 25 MB")

    nombre = sanitizar_nombre_archivo(nombre_original or ruta.name)

    if nombre.lower().endswith(".pdf"):
        try:
            validar_pdf(contenido, nombre)
        except ErrorValidacionPDF as e:
            raise ErrorPreflight(str(e)) from e

    sha = hashlib.sha256(contenido).hexdigest()

    # Detectar duplicado
    existe = sesion.execute(
        select(ColaProcesamiento).where(
            ColaProcesamiento.sha256 == sha,
            ColaProcesamiento.empresa_id == empresa_id,
            ColaProcesamiento.estado == "COMPLETADO",
        )
    ).first()

    return ResultadoPreflight(
        sha256=sha,
        duplicado=existe is not None,
        tamano_bytes=tamano,
        nombre_sanitizado=nombre,
    )


# --- Scoring + Decision ---

class Decision(str, Enum):
    AUTO_PUBLICADO = "AUTO_PUBLICADO"
    COLA_REVISION = "COLA_REVISION"
    COLA_ADMIN = "COLA_ADMIN"
    CUARENTENA = "CUARENTENA"


_PESO_OCR        = 0.45  # reducido para dar cabida a coherencia
_PESO_TRUST      = 0.25
_PESO_SUPPLIER   = 0.15
_PESO_COHERENCIA = 0.10  # 5º factor: coherencia fiscal post-OCR
_PESO_CHECKS     = 0.05  # reducido de 0.10

_TRUST_BONUS = {
    TrustLevel.MAXIMA: 25,
    TrustLevel.ALTA: 15,
    TrustLevel.MEDIA: 5,
    TrustLevel.BAJA: 0,
}


def calcular_score(
    confianza_ocr: float,
    trust_level: TrustLevel,
    supplier_rule_aplicada: bool,
    checks_pasados: int,
    checks_totales: int,
    coherencia: Optional[ResultadoCoherencia] = None,
) -> float:
    """Calcula score 0-100 para la decision automatica (5 factores).

    Pesos:
      OCR          45%  (reducido para dar cabida al 5º factor)
      Trust        25%
      Supplier     15%
      Coherencia   10%  (5º factor: validación fiscal post-OCR)
      Checks        5%  (reducido de 10%)
    """
    base_ocr = confianza_ocr * 100 * _PESO_OCR
    bonus_trust = _TRUST_BONUS[trust_level]
    bonus_supplier = 15 if supplier_rule_aplicada else 0
    ratio_checks = (checks_pasados / checks_totales) if checks_totales > 0 else 0
    base_checks = ratio_checks * 100 * _PESO_CHECKS

    base_coherencia = 0.0
    if coherencia is not None:
        base_coherencia = coherencia.score * _PESO_COHERENCIA

    score = base_ocr + bonus_trust + bonus_supplier + base_coherencia + base_checks
    return round(min(score, 100.0), 2)


def decidir_destino(
    score: float,
    trust: TrustLevel,
    coherencia: Optional[ResultadoCoherencia] = None,
) -> Decision:
    """Decide el destino del documento basandose en score, trust y coherencia.

    Bloqueo duro: si coherencia tiene errores graves → CUARENTENA inmediata.
    """
    if coherencia is not None and coherencia.errores_graves:
        return Decision.CUARENTENA

    if score >= 95 and trust in (TrustLevel.MAXIMA, TrustLevel.ALTA):
        return Decision.AUTO_PUBLICADO
    if score >= 85 and trust == TrustLevel.ALTA:
        return Decision.AUTO_PUBLICADO
    if score >= 70:
        return Decision.COLA_REVISION
    if score >= 50:
        return Decision.COLA_ADMIN
    return Decision.CUARENTENA
