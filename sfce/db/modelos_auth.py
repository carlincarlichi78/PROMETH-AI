"""SFCE DB — Modelo de usuarios para autenticacion JWT."""

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, Integer, String, JSON, Index
from sqlalchemy.orm import relationship

from sfce.core.tiers import TIER_BASICO, TIERS_VALIDOS
from sfce.db.base import Base

_TIERS_CHECK = f"plan_tier IN ({', '.join(repr(t) for t in TIERS_VALIDOS)})"


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
    plan_tier         = Column(String(10), nullable=False, default=TIER_BASICO, server_default=TIER_BASICO)
    limite_empresas   = Column(Integer, nullable=True)  # None = ilimitado

    # Credenciales FacturaScripts por gestoría (migración 024)
    # Si son NULL, se usa la instancia global (FS_API_URL / FS_API_TOKEN del sistema)
    fs_url       = Column(String(500), nullable=True)   # URL base API FS (sin barra final)
    fs_token_enc = Column(String(500), nullable=True)   # Token API cifrado con Fernet

    __table_args__ = (
        CheckConstraint(_TIERS_CHECK, name="ck_gestorias_plan_tier"),
    )

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

    # Onboarding: invitacion por email.
    # invitacion_token es NULL cuando el token ya fue consumido (estado post-aceptacion).
    # UNIQUE en NOT-NULL: SQL permite multiples NULL en columna UNIQUE sin violar la restriccion.
    # El constraint garantiza coherencia: si hay expiracion, debe haber token (y viceversa).
    invitacion_token = Column(String(128), nullable=True, unique=True, index=True)
    invitacion_expira = Column(DateTime, nullable=True)
    forzar_cambio_password = Column(Boolean, nullable=False, default=False)

    # Reset de contraseña
    reset_token = Column(String(128), nullable=True, unique=True, index=True)
    reset_token_expira = Column(DateTime, nullable=True)
    plan_tier = Column(String(10), nullable=False, default=TIER_BASICO, server_default=TIER_BASICO)

    gestoria = relationship("Gestoria", back_populates="usuarios")

    __table_args__ = (
        # Coherencia: token e invitacion_expira deben ser ambos NULL o ambos NOT NULL.
        # Evita estados inconsistentes donde hay fecha de expiracion sin token o token sin fecha.
        CheckConstraint(
            "(invitacion_token IS NULL) = (invitacion_expira IS NULL)",
            name="ck_invitacion_token_expira_coherentes",
        ),
        CheckConstraint(_TIERS_CHECK, name="ck_usuarios_plan_tier"),
    )


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
