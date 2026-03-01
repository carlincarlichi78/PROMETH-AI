"""Motor de Supplier Rules — evolución de aprendizaje.yaml hacia BD."""
import logging
from typing import Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from sfce.db.modelos import SupplierRule

logger = logging.getLogger(__name__)

_UMBRAL_TASA = 0.90
_MINIMO_MUESTRAS = 3


def buscar_regla_aplicable(
    sesion: Session,
    emisor_cif: str,
    emisor_nombre: str = "",
    empresa_id: Optional[int] = None,
) -> Optional[SupplierRule]:
    """Busca la regla más específica aplicable en jerarquía de 3 niveles.

    Jerarquía:
      1. Específica: CIF + empresa  (más precisa)
      2. Global CIF: empresa_id=None + CIF conocido  (cross-empresa)
      3. Global nombre: empresa_id=None + CIF=None + patrón nombre  (fallback)

    Args:
        sesion: Sesión SQLAlchemy.
        emisor_cif: CIF del emisor (puede ser vacío para nivel 3).
        emisor_nombre: Nombre del emisor para fallback por patrón.
        empresa_id: ID de empresa (opcional, None para búsqueda global).
    """
    # Nivel 1 + 2: búsqueda por CIF (empresa específica primero, global segundo)
    if emisor_cif:
        stmt = (
            select(SupplierRule)
            .where(
                or_(
                    SupplierRule.empresa_id == empresa_id,
                    SupplierRule.empresa_id.is_(None),
                ),
                SupplierRule.emisor_cif == emisor_cif,
            )
            .order_by(
                # Más específico primero: empresa > global
                SupplierRule.empresa_id.desc().nulls_last(),
                SupplierRule.tasa_acierto.desc(),
            )
            .limit(1)
        )
        resultado = sesion.execute(stmt).scalar_one_or_none()
        if resultado:
            return resultado

    # Nivel 3: búsqueda por patrón nombre (solo reglas globales sin CIF)
    if emisor_nombre:
        nombre_upper = emisor_nombre.upper()
        candidatas = sesion.execute(
            select(SupplierRule)
            .where(
                SupplierRule.empresa_id.is_(None),
                SupplierRule.emisor_cif.is_(None),
                SupplierRule.emisor_nombre_patron.is_not(None),
            )
            .order_by(SupplierRule.tasa_acierto.desc())
        ).scalars().all()

        for regla in candidatas:
            if regla.emisor_nombre_patron and regla.emisor_nombre_patron.upper() in nombre_upper:
                return regla

    return None


def aplicar_regla(regla: SupplierRule, campos: dict) -> None:
    """Rellena campos con los valores de la regla (pre-fill para OCR)."""
    if regla.subcuenta_gasto:
        campos["subcuenta_gasto"] = regla.subcuenta_gasto
    if regla.codimpuesto:
        campos["codimpuesto"] = regla.codimpuesto
    if regla.regimen:
        campos["regimen"] = regla.regimen
    if regla.tipo_doc_sugerido:
        campos["tipo_doc_sugerido"] = regla.tipo_doc_sugerido


def registrar_confirmacion(
    regla: SupplierRule, correcto: bool, sesion: Session
) -> None:
    """Actualiza contadores tras la validación humana de un documento."""
    regla.aplicaciones += 1
    if correcto:
        regla.confirmaciones += 1
    recalcular_auto_aplicable(regla)
    sesion.commit()


def recalcular_auto_aplicable(regla: SupplierRule) -> None:
    """Recalcula tasa_acierto y auto_aplicable."""
    if regla.aplicaciones > 0:
        regla.tasa_acierto = regla.confirmaciones / regla.aplicaciones
    else:
        regla.tasa_acierto = 0.0
    regla.auto_aplicable = (
        regla.aplicaciones >= _MINIMO_MUESTRAS
        and regla.tasa_acierto >= _UMBRAL_TASA
    )


def upsert_regla_desde_correccion(
    empresa_id: int,
    emisor_cif: str,
    campos_corregidos: dict,
    sesion: Session,
) -> SupplierRule:
    """Crea o actualiza una regla cuando el gestor corrige un campo."""
    regla = sesion.execute(
        select(SupplierRule).where(
            SupplierRule.empresa_id == empresa_id,
            SupplierRule.emisor_cif == emisor_cif,
        )
    ).scalar_one_or_none()

    if not regla:
        regla = SupplierRule(
            empresa_id=empresa_id,
            emisor_cif=emisor_cif,
            nivel="empresa",
            aplicaciones=0,
            confirmaciones=0,
            tasa_acierto=0.0,
            auto_aplicable=False,
        )
        sesion.add(regla)

    if "subcuenta_gasto" in campos_corregidos:
        regla.subcuenta_gasto = campos_corregidos["subcuenta_gasto"]
    if "codimpuesto" in campos_corregidos:
        regla.codimpuesto = campos_corregidos["codimpuesto"]
    if "regimen" in campos_corregidos:
        regla.regimen = campos_corregidos["regimen"]
    if "tipo_doc_sugerido" in campos_corregidos:
        regla.tipo_doc_sugerido = campos_corregidos["tipo_doc_sugerido"]

    registrar_confirmacion(regla, correcto=True, sesion=sesion)
    logger.info("Supplier Rule actualizada: empresa=%s, cif=%s", empresa_id, emisor_cif)
    return regla
