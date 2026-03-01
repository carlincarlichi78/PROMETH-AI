"""SFCE DB — Modelo de usuarios para autenticacion JWT."""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, JSON, Index
from sqlalchemy.orm import relationship

from sfce.db.base import Base


class Gestoria(Base):
    """Tenant principal del sistema. Cada gestoria tiene sus propios usuarios y clientes."""
    __tablename__ = "gestorias"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(200), nullable=False)
    email_contacto = Column(String(200), nullable=False)
    cif = Column(String(20), nullable=True)
    modulos = Column(JSON, nullable=False, default=list)  # ['contabilidad', 'asesoramiento']
    plan_asesores = Column(Integer, nullable=False, default=1)
    plan_clientes_tramo = Column(String(10), nullable=False, default="1-10")
    activa = Column(Boolean, nullable=False, default=True)
    fecha_alta = Column(DateTime, nullable=False, default=datetime.utcnow)
    fecha_vencimiento = Column(DateTime, nullable=True)

    usuarios = relationship("Usuario", back_populates="gestoria")


class Usuario(Base):
    """Usuario del sistema SFCE con rol y acceso por empresa."""
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True)
    email = Column(String(200), unique=True, nullable=False)
    nombre = Column(String(200), nullable=False)
    hash_password = Column(String(200), nullable=False)
    # rol: 'superadmin' | 'admin_gestoria' | 'asesor' | 'asesor_independiente' | 'cliente'
    # Valores legacy mantenidos: 'admin' | 'gestor' | 'readonly'
    rol = Column(String(30), nullable=False, default="asesor")
    activo = Column(Boolean, default=True)
    empresas_ids = Column(JSON, default=list)  # IDs de empresas que puede ver (gestor) — legacy
    fecha_creacion = Column(DateTime, default=datetime.now)

    # Campos multi-tenant
    gestoria_id = Column(Integer, ForeignKey("gestorias.id"), nullable=True)
    empresas_asignadas = Column(JSON, nullable=False, default=list)

    # Bloqueo de cuenta por intentos fallidos
    failed_attempts = Column(Integer, nullable=False, default=0)
    locked_until = Column(DateTime, nullable=True)

    # 2FA TOTP
    totp_secret = Column(String(64), nullable=True)
    totp_habilitado = Column(Boolean, nullable=False, default=False)

    # Campos de invitación (onboarding)
    invitacion_token = Column(String(128), nullable=True, unique=True, index=True)
    invitacion_expira = Column(DateTime, nullable=True)
    forzar_cambio_password = Column(Boolean, default=False, nullable=False)

    gestoria = relationship("Gestoria", back_populates="usuarios")


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
