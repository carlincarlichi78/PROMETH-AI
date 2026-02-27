"""SFCE DB — Modelo de usuarios para autenticacion JWT."""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, JSON

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
