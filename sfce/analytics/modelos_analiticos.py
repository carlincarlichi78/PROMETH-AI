"""Star schema analítico — 4 tablas fact + event store.

NUNCA consultar partidas/asientos directamente desde el módulo advisor.
Toda la lectura va contra estas tablas.
"""
from datetime import date, datetime, timezone
from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float, ForeignKey,
    Integer, String, Text, JSON, Index,
)
from sqlalchemy.orm import DeclarativeBase


class BaseAnalitica(DeclarativeBase):
    pass


# Alias para compatibilidad con imports externos (tests, etc.)
Base = BaseAnalitica


class EventoAnalitico(BaseAnalitica):
    """Event store append-only. Cada documento procesado genera un evento inmutable."""
    __tablename__ = "eventos_analiticos"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, nullable=False, index=True)
    tipo_evento = Column(String(20), nullable=False)  # TPV | BAN | FV | NOM | ...
    fecha_evento = Column(Date, nullable=False, index=True)
    payload = Column(JSON, nullable=False)  # datos crudos del evento
    procesado = Column(Boolean, default=False)
    creado_en = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_evento_empresa_fecha", "empresa_id", "fecha_evento"),
    )


class FactCaja(BaseAnalitica):
    """Un registro por empresa × fecha × servicio (almuerzo/cena/noche)."""
    __tablename__ = "fact_caja"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, nullable=False, index=True)
    fecha = Column(Date, nullable=False, index=True)
    servicio = Column(String(20), nullable=False, default="general")  # almuerzo|cena|noche|general
    covers = Column(Integer, default=0)
    ventas_totales = Column(Float, default=0.0)
    ticket_medio = Column(Float, default=0.0)
    num_mesas_ocupadas = Column(Integer, default=0)
    metodo_pago_tarjeta = Column(Float, default=0.0)
    metodo_pago_efectivo = Column(Float, default=0.0)
    metodo_pago_otros = Column(Float, default=0.0)
    evento_id = Column(Integer, ForeignKey("eventos_analiticos.id"), nullable=True)

    __table_args__ = (
        Index("ix_fact_caja_empresa_fecha", "empresa_id", "fecha"),
    )


class FactVenta(BaseAnalitica):
    """Un registro por empresa × fecha × servicio × producto."""
    __tablename__ = "fact_venta"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, nullable=False, index=True)
    fecha = Column(Date, nullable=False, index=True)
    servicio = Column(String(20), nullable=False, default="general")
    producto_nombre = Column(String(200), nullable=False)
    familia = Column(String(50), nullable=False, default="otros")  # comida|bebida|postre|vino|otros
    qty = Column(Integer, default=0)
    pvp_unitario = Column(Float, default=0.0)
    total = Column(Float, default=0.0)
    evento_id = Column(Integer, ForeignKey("eventos_analiticos.id"), nullable=True)

    __table_args__ = (
        Index("ix_fact_venta_empresa_fecha", "empresa_id", "fecha"),
    )


class FactCompra(BaseAnalitica):
    """Un registro por empresa × fecha × proveedor × familia de gasto."""
    __tablename__ = "fact_compra"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, nullable=False, index=True)
    fecha = Column(Date, nullable=False, index=True)
    proveedor_nombre = Column(String(200), nullable=False)
    proveedor_cif = Column(String(20), nullable=True)
    familia = Column(String(50), nullable=False, default="otros")  # alimentacion|bebidas|personal|suministros|otros
    importe = Column(Float, default=0.0)
    tipo_movimiento = Column(String(20), default="compra")  # compra|devolucion|pago
    evento_id = Column(Integer, ForeignKey("eventos_analiticos.id"), nullable=True)

    __table_args__ = (
        Index("ix_fact_compra_empresa_fecha", "empresa_id", "fecha"),
        Index("ix_fact_compra_proveedor", "empresa_id", "proveedor_nombre"),
    )


class FactPersonal(BaseAnalitica):
    """Un registro por empresa × período × empleado (o agregado si no hay RRHH detallado)."""
    __tablename__ = "fact_personal"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, nullable=False, index=True)
    periodo = Column(String(7), nullable=False, index=True)  # "2026-06"
    empleado_nombre = Column(String(200), nullable=True)  # null = dato agregado
    coste_bruto = Column(Float, default=0.0)
    coste_ss_empresa = Column(Float, default=0.0)
    coste_total = Column(Float, default=0.0)
    dias_baja = Column(Integer, default=0)
    evento_id = Column(Integer, ForeignKey("eventos_analiticos.id"), nullable=True)

    __table_args__ = (
        Index("ix_fact_personal_empresa_periodo", "empresa_id", "periodo"),
    )


class AlertaAnalitica(BaseAnalitica):
    """Alertas generadas por el motor de reglas sectoriales."""
    __tablename__ = "alertas_analiticas"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, nullable=False, index=True)
    alerta_id = Column(String(50), nullable=False)    # id del YAML (food_cost_spike, etc.)
    severidad = Column(String(10), nullable=False)     # alta|media|baja
    mensaje = Column(Text, nullable=False)
    valor_actual = Column(Float, nullable=True)
    benchmark_referencia = Column(Float, nullable=True)
    activa = Column(Boolean, default=True)
    creada_en = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    resuelta_en = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_alerta_empresa_activa", "empresa_id", "activa"),
    )
