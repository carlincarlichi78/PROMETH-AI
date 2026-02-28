"""
Helper de auditoría RGPD.
Usar en endpoints que acceden a datos sensibles.
"""
from datetime import datetime
from enum import StrEnum
from typing import Optional

from sqlalchemy.orm import Session

from sfce.db.modelos_auth import AuditLog


class AuditAccion(StrEnum):
    LOGIN = "login"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    READ = "read"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    EXPORT = "export"
    CONCILIAR = "conciliar"


def auditar(
    session: Session,
    accion: "AuditAccion | str",
    recurso: str,
    *,
    email_usuario: Optional[str] = None,
    usuario_id: Optional[int] = None,
    rol: Optional[str] = None,
    gestoria_id: Optional[int] = None,
    recurso_id: Optional[str] = None,
    ip_origen: Optional[str] = None,
    resultado: str = "ok",
    detalles: Optional[dict] = None,
) -> None:
    """
    Registra una entrada de auditoría en la sesión activa.
    Llamar ANTES de session.commit() para que quede en la misma transacción.
    """
    entrada = AuditLog(
        timestamp=datetime.utcnow(),
        usuario_id=usuario_id,
        email_usuario=email_usuario,
        rol=rol,
        gestoria_id=gestoria_id,
        accion=str(accion),
        recurso=recurso,
        recurso_id=str(recurso_id) if recurso_id is not None else None,
        ip_origen=ip_origen,
        resultado=resultado,
        detalles=detalles,
    )
    session.add(entrada)


def ip_desde_request(request) -> Optional[str]:
    """Extrae IP real del cliente teniendo en cuenta proxies (X-Forwarded-For)."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None
