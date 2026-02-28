"""SFCE DB — Modelo de usuarios para autenticacion JWT."""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, JSON, Index

from sfce.db.base import Base


class Usuario(Base):
    """Usuario del sistema SFCE con rol y acceso por empresa."""
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True)
    email = Column(String(200), unique=True, nullable=False)
    nombre = Column(String(200), nullable=False)
    hash_password = Column(String(200), nullable=False)
    rol = Column(String(20), nullable=False, default="readonly")  # admin, gestor, readonly
    activo = Column(Boolean, default=True)
    empresas_ids = Column(JSON, default=list)  # IDs de empresas que puede ver (gestor)
    fecha_creacion = Column(DateTime, default=datetime.now)


class AuditLog(Base):
    """Registro de auditoría RGPD. Inmutable — nunca se modifica ni borra."""
    __tablename__ = "audit_log_seguridad"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False)
    # Quién
    usuario_id = Column(Integer, nullable=True)       # null si login fallido
    email_usuario = Column(String(200), nullable=True)
    rol = Column(String(30), nullable=True)
    gestoria_id = Column(Integer, nullable=True)
    # Qué
    accion = Column(String(30), nullable=False)
    # login | login_failed | logout | read | create | update | delete | export | conciliar
    recurso = Column(String(50), nullable=False)
    # auth | empresa | factura | asiento | usuario | movimiento | modelo_fiscal | export
    recurso_id = Column(String(50), nullable=True)
    # Dónde / resultado
    ip_origen = Column(String(45), nullable=True)     # IPv4 o IPv6
    resultado = Column(String(10), nullable=False, default="ok")  # ok | error | denied
    detalles = Column(JSON, nullable=True)            # info adicional

    __table_args__ = (
        Index("ix_audit_log_seg_timestamp", "timestamp"),
        Index("ix_audit_log_seg_gestoria", "gestoria_id", "timestamp"),
        Index("ix_audit_log_seg_usuario", "email_usuario", "timestamp"),
    )
