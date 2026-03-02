from __future__ import annotations
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sfce.db.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class TestingSesion(Base):
    __tablename__ = "testing_sesiones"

    id = Column(String(36), primary_key=True, default=_uuid)
    modo = Column(String(20), nullable=False)        # smoke|regression|vigilancia|manual
    trigger = Column(String(20), nullable=False)     # ci|schedule|api|manual
    estado = Column(String(20), nullable=False)      # en_curso|completado|fallido|abortado
    inicio = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    fin = Column(DateTime(timezone=True), nullable=True)
    total_ok = Column(Integer, default=0)
    total_bugs = Column(Integer, default=0)
    total_arreglados = Column(Integer, default=0)
    total_timeout = Column(Integer, default=0)
    commit_sha = Column(String(40), nullable=True)
    notas = Column(Text, nullable=True)

    ejecuciones = relationship("TestingEjecucion", back_populates="sesion", cascade="all, delete-orphan")
    bugs = relationship("TestingBug", back_populates="sesion", cascade="all, delete-orphan")


class TestingEjecucion(Base):
    __tablename__ = "testing_ejecuciones"

    id = Column(String(36), primary_key=True, default=_uuid)
    sesion_id = Column(String(36), ForeignKey("testing_sesiones.id", ondelete="CASCADE"))
    escenario_id = Column(String(100), nullable=False)
    variante_id = Column(String(100), nullable=False)
    canal = Column(String(20), nullable=False)        # email|portal|bancario|http|playwright
    resultado = Column(String(30), nullable=False)    # ok|bug_pendiente|bug_arreglado|timeout|error_sistema
    estado_doc_final = Column(String(30), nullable=True)
    tipo_doc_detectado = Column(String(10), nullable=True)
    idasiento = Column(Integer, nullable=True)
    asiento_cuadrado = Column(Boolean, nullable=True)
    duracion_ms = Column(Integer, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    sesion = relationship("TestingSesion", back_populates="ejecuciones")


class TestingBug(Base):
    __tablename__ = "testing_bugs"

    id = Column(String(36), primary_key=True, default=_uuid)
    sesion_id = Column(String(36), ForeignKey("testing_sesiones.id", ondelete="CASCADE"))
    escenario_id = Column(String(100), nullable=False)
    variante_id = Column(String(100), nullable=True)
    tipo = Column(String(50), nullable=False)
    descripcion = Column(Text, nullable=False)
    stack_trace = Column(Text, nullable=True)
    fix_intentado = Column(Text, nullable=True)
    fix_exitoso = Column(Boolean, default=False)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    sesion = relationship("TestingSesion", back_populates="bugs")
