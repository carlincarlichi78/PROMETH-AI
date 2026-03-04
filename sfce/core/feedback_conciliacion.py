"""
Feedback loop de conciliación bancaria.

Aprende de confirmaciones manuales (incrementa frecuencia en patrones_conciliacion)
y penaliza rechazos (decrementa, elimina si llega a 0).
"""
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from sfce.core.normalizar_bancario import limpiar_nif, normalizar_concepto, rango_importe
from sfce.db.modelos import PatronConciliacion, SugerenciaMatch


UMBRAL_REDONDEO = Decimal("0.05")
CUENTA_REDONDEO = "6590000000"   # 659 - Otros gastos gestión corriente
CUENTA_COMISION = "6260000000"   # 626 - Servicios bancarios y similares


def feedback_positivo(
    session: Session,
    empresa_id: int,
    concepto_bancario: str,
    importe: Decimal,
    nif_proveedor: Optional[str],
    capa_origen: int,
) -> None:
    """Registra o incrementa un patrón aprendido tras confirmación."""
    patron_texto, patron_limpio = normalizar_concepto(concepto_bancario)
    rango = rango_importe(importe)
    nif_limpio = limpiar_nif(nif_proveedor) if nif_proveedor else None

    patron = (
        session.query(PatronConciliacion)
        .filter_by(empresa_id=empresa_id, patron_texto=patron_texto, rango_importe_aprox=rango)
        .first()
    )
    if patron:
        patron.frecuencia_exito += 1
        patron.ultima_confirmacion = date.today()
        if nif_limpio:
            patron.nif_proveedor = nif_limpio
    else:
        session.add(PatronConciliacion(
            empresa_id=empresa_id,
            patron_texto=patron_texto,
            patron_limpio=patron_limpio,
            nif_proveedor=nif_limpio,
            rango_importe_aprox=rango,
            frecuencia_exito=1,
            ultima_confirmacion=date.today(),
        ))


def feedback_negativo(
    session: Session,
    empresa_id: int,
    concepto_bancario: str,
    importe: Decimal,
    capa_origen: int,
    sugerencia_id: Optional[int] = None,
) -> None:
    """Penaliza el patrón asociado a un rechazo. Si llega a 0, lo elimina."""
    # Desactivar la sugerencia específica si se proporciona
    if sugerencia_id:
        sug = session.get(SugerenciaMatch, sugerencia_id)
        if sug:
            sug.activa = False

    # Solo penalizar patrones si el rechazo vino de capa 4 (patrones aprendidos)
    if capa_origen != 4:
        return

    patron_texto, _ = normalizar_concepto(concepto_bancario)
    rango = rango_importe(importe)
    patron = (
        session.query(PatronConciliacion)
        .filter_by(empresa_id=empresa_id, patron_texto=patron_texto, rango_importe_aprox=rango)
        .first()
    )
    if patron:
        patron.frecuencia_exito -= 1
        if patron.frecuencia_exito <= 0:
            session.delete(patron)


def gestionar_diferencia(importe_mov: Decimal, importe_doc: Decimal) -> dict:
    """
    Determina la acción cuando hay diferencia entre movimiento y documento.

    Returns dict con 'accion', 'cuenta_contable', 'importe_ajuste'.
    - Si diferencia <= 0.05€: auto_redondeo → cuenta 659
    - Si diferencia > 0.05€: crear_asiento_comision → cuenta 626
    """
    diferencia = abs(importe_mov - importe_doc)
    if diferencia <= UMBRAL_REDONDEO:
        return {
            "accion": "auto_redondeo",
            "cuenta_contable": CUENTA_REDONDEO,
            "importe_ajuste": float(diferencia),
        }
    return {
        "accion": "crear_asiento_comision",
        "cuenta_contable": CUENTA_COMISION,
        "importe_ajuste": float(diferencia),
        "requiere_confirmacion": True,
    }
