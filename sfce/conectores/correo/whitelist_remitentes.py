"""Gestión de whitelist de remitentes autorizados por empresa."""
import logging
from sqlalchemy import select
from sqlalchemy.orm import Session
from sfce.db.modelos import RemitenteAutorizado

logger = logging.getLogger(__name__)


def verificar_whitelist(remitente: str, empresa_id: int, sesion: Session) -> bool:
    """True si el remitente está autorizado para la empresa.

    Lógica:
    - Whitelist vacía → permite todo (empresa aún no configurada)
    - Whitelist con entradas → solo remitentes en lista
    - Entrada @dominio.es → autoriza todos los emails de ese dominio
    """
    if es_whitelist_vacia(empresa_id, sesion):
        return True

    remitente_lower = remitente.lower().strip()
    entradas = sesion.execute(
        select(RemitenteAutorizado).where(
            RemitenteAutorizado.empresa_id == empresa_id,
            RemitenteAutorizado.activo == True,  # noqa: E712
        )
    ).scalars().all()

    for entrada in entradas:
        patron = entrada.email.lower().strip()
        if patron.startswith("@"):
            # Wildcard de dominio
            if remitente_lower.endswith(patron):
                return True
        elif patron == remitente_lower:
            return True

    return False


def agregar_remitente(
    email: str, empresa_id: int, sesion: Session, nombre: str | None = None
) -> RemitenteAutorizado:
    """Añade un remitente autorizado. Idempotente por email+empresa_id."""
    existente = sesion.execute(
        select(RemitenteAutorizado).where(
            RemitenteAutorizado.empresa_id == empresa_id,
            RemitenteAutorizado.email == email.lower().strip(),
        )
    ).scalar_one_or_none()
    if existente:
        existente.activo = True
        sesion.flush()
        return existente
    nuevo = RemitenteAutorizado(
        empresa_id=empresa_id,
        email=email.lower().strip(),
        nombre=nombre,
    )
    sesion.add(nuevo)
    sesion.flush()
    return nuevo


def es_whitelist_vacia(empresa_id: int, sesion: Session) -> bool:
    """True si la empresa no tiene ningún registro de remitente (configurada nunca).

    Una empresa con entradas inactivas NO se considera vacía — la whitelist
    está configurada y se aplica estrictamente.
    """
    count = sesion.execute(
        select(RemitenteAutorizado).where(
            RemitenteAutorizado.empresa_id == empresa_id,
        )
    ).scalars().all()
    return len(count) == 0
