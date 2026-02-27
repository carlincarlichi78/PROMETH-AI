"""SFCE DB — Modelos SQLAlchemy (16 tablas)."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean, Column, Date, DateTime, ForeignKey, Integer,
    Numeric, String, Text, JSON, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship

from sfce.db.base import Base


class DirectorioEntidad(Base):
    """Directorio maestro global de entidades (proveedores/clientes)."""
    __tablename__ = "directorio_entidades"

    id = Column(Integer, primary_key=True)
    cif = Column(String(20), unique=True, nullable=True)  # nullable para clientes sin CIF
    nombre = Column(String(200), nullable=False)
    nombre_comercial = Column(String(200))
    aliases = Column(JSON, default=list)
    pais = Column(String(3), default="ESP")
    tipo_persona = Column(String(10))  # fisica | juridica
    forma_juridica = Column(String(20))
    cnae = Column(String(4))
    sector = Column(String(50))
    validado_aeat = Column(Boolean, default=False)
    validado_vies = Column(Boolean, default=False)
    fecha_alta = Column(DateTime, default=datetime.now)
    fecha_actualizacion = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    datos_enriquecidos = Column(JSON, default=dict)

    overlays = relationship("ProveedorCliente", back_populates="directorio")

    __table_args__ = (
        Index("ix_directorio_nombre", "nombre"),
    )


class Empresa(Base):
    """Empresa/autonomo gestionado."""
    __tablename__ = "empresas"

    id = Column(Integer, primary_key=True)
    cif = Column(String(20), unique=True, nullable=False)
    nombre = Column(String(200), nullable=False)
    forma_juridica = Column(String(50), nullable=False)  # autonomo, sl, sa, cb, sc, coop, asociacion, comunidad, fundacion, slp, slu
    territorio = Column(String(20), nullable=False, default="peninsula")
    regimen_iva = Column(String(30), nullable=False, default="general")
    idempresa_fs = Column(Integer)  # ID en FacturaScripts (nullable si solo BD local)
    codejercicio_fs = Column(String(10))
    activa = Column(Boolean, default=True)
    fecha_alta = Column(Date, nullable=False, default=date.today)
    config_extra = Column(JSON, default=dict)  # datos adicionales del config.yaml

    # Relaciones
    proveedores_clientes = relationship("ProveedorCliente", back_populates="empresa")
    trabajadores = relationship("Trabajador", back_populates="empresa")
    documentos = relationship("Documento", back_populates="empresa")
    asientos = relationship("Asiento", back_populates="empresa")
    activos = relationship("ActivoFijo", back_populates="empresa")


class ProveedorCliente(Base):
    """Proveedor o cliente de una empresa."""
    __tablename__ = "proveedores_clientes"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    cif = Column(String(20), nullable=False)
    nombre = Column(String(200), nullable=False)
    tipo = Column(String(10), nullable=False)  # proveedor | cliente
    subcuenta_gasto = Column(String(10))  # 6000000000
    subcuenta_contrapartida = Column(String(10))  # 4000000xxx
    codimpuesto = Column(String(10), default="IVA21")
    regimen = Column(String(30), default="general")
    retencion_pct = Column(Numeric(5, 2))
    recargo_equiv = Column(Numeric(5, 2))
    pais = Column(String(3))  # ISO 3166-1 alpha-3
    persona_fisica = Column(Boolean, default=False)
    aliases = Column(JSON, default=list)  # nombres alternativos
    activo = Column(Boolean, default=True)
    directorio_id = Column(Integer, ForeignKey("directorio_entidades.id"), nullable=True)

    empresa = relationship("Empresa", back_populates="proveedores_clientes")
    directorio = relationship("DirectorioEntidad", back_populates="overlays")

    __table_args__ = (
        UniqueConstraint("empresa_id", "cif", "tipo", name="uq_empresa_cif_tipo"),
        Index("ix_provcli_cif", "cif"),
        Index("ix_provcli_directorio", "directorio_id"),
    )


class Trabajador(Base):
    """Trabajador de una empresa (para nominas)."""
    __tablename__ = "trabajadores"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    dni = Column(String(20), nullable=False)
    nombre = Column(String(200), nullable=False)
    categoria = Column(String(100))
    bruto_mensual = Column(Numeric(10, 2))
    pagas = Column(Integer, default=14)
    fecha_alta = Column(Date)
    fecha_baja = Column(Date)
    ss_empresa_pct = Column(Numeric(5, 2), default=Decimal("30.0"))
    irpf_pct = Column(Numeric(5, 2))
    activo = Column(Boolean, default=True)

    empresa = relationship("Empresa", back_populates="trabajadores")

    __table_args__ = (
        UniqueConstraint("empresa_id", "dni", name="uq_empresa_dni"),
    )


class Documento(Base):
    """Documento procesado (factura, nomina, suministro, etc.)."""
    __tablename__ = "documentos"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    tipo_doc = Column(String(10), nullable=False)  # FC, FV, NC, NOM, SUM, BAN, RLC, IMP, ANT, REC
    ruta_pdf = Column(String(500))
    hash_pdf = Column(String(64))  # SHA256
    datos_ocr = Column(JSON)  # resultado OCR completo
    ocr_tier = Column(Integer)  # 0, 1, 2
    confianza = Column(Integer)
    estado = Column(String(20), nullable=False, default="pendiente")  # pendiente, registrado, cuarentena, error
    motivo_cuarentena = Column(Text)
    decision_log = Column(JSON)  # log_razonamiento del MotorReglas
    asiento_id = Column(Integer, ForeignKey("asientos.id"))
    factura_id_fs = Column(Integer)  # idfactura en FacturaScripts
    fecha_proceso = Column(DateTime, default=datetime.now)
    ejercicio = Column(String(4))

    empresa = relationship("Empresa", back_populates="documentos")
    asiento = relationship("Asiento", back_populates="documento")

    __table_args__ = (
        Index("ix_doc_empresa_tipo", "empresa_id", "tipo_doc"),
        Index("ix_doc_hash", "hash_pdf"),
        Index("ix_doc_estado", "estado"),
    )


class Asiento(Base):
    """Asiento contable."""
    __tablename__ = "asientos"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    numero = Column(Integer)  # numero secuencial dentro del ejercicio
    fecha = Column(Date, nullable=False)
    concepto = Column(String(500))
    idasiento_fs = Column(Integer)  # ID en FacturaScripts
    ejercicio = Column(String(4))
    origen = Column(String(30))  # pipeline, manual, cierre, amortizacion, regularizacion
    sincronizado_fs = Column(Boolean, default=False)

    empresa = relationship("Empresa", back_populates="asientos")
    partidas = relationship("Partida", back_populates="asiento", cascade="all, delete-orphan")
    documento = relationship("Documento", back_populates="asiento", uselist=False)

    __table_args__ = (
        Index("ix_asiento_empresa_fecha", "empresa_id", "fecha"),
    )


class Partida(Base):
    """Linea de un asiento contable."""
    __tablename__ = "partidas"

    id = Column(Integer, primary_key=True)
    asiento_id = Column(Integer, ForeignKey("asientos.id"), nullable=False)
    subcuenta = Column(String(10), nullable=False)
    debe = Column(Numeric(12, 2), default=Decimal("0"))
    haber = Column(Numeric(12, 2), default=Decimal("0"))
    concepto = Column(String(500))
    codimpuesto = Column(String(10))
    documento_id = Column(Integer)  # referencia al documento origen
    idpartida_fs = Column(Integer)  # ID en FacturaScripts

    asiento = relationship("Asiento", back_populates="partidas")

    __table_args__ = (
        Index("ix_partida_subcuenta", "subcuenta"),
    )


class Factura(Base):
    """Factura emitida o recibida (datos fiscales)."""
    __tablename__ = "facturas"

    id = Column(Integer, primary_key=True)
    documento_id = Column(Integer, ForeignKey("documentos.id"), nullable=False)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    tipo = Column(String(10), nullable=False)  # emitida | recibida
    numero_factura = Column(String(50))
    fecha_factura = Column(Date)
    fecha_operacion = Column(Date)
    cif_emisor = Column(String(20))
    nombre_emisor = Column(String(200))
    cif_receptor = Column(String(20))
    nombre_receptor = Column(String(200))
    base_imponible = Column(Numeric(12, 2))
    iva_importe = Column(Numeric(12, 2))
    irpf_importe = Column(Numeric(12, 2))
    recargo_importe = Column(Numeric(12, 2))
    total = Column(Numeric(12, 2))
    divisa = Column(String(3), default="EUR")
    tasa_conversion = Column(Numeric(10, 6), default=Decimal("1.0"))
    pagada = Column(Boolean, default=False)
    idfactura_fs = Column(Integer)

    documento = relationship("Documento")

    __table_args__ = (
        Index("ix_factura_empresa_tipo", "empresa_id", "tipo"),
        Index("ix_factura_cif_emisor", "cif_emisor"),
    )


class Pago(Base):
    """Pago asociado a una factura."""
    __tablename__ = "pagos"

    id = Column(Integer, primary_key=True)
    factura_id = Column(Integer, ForeignKey("facturas.id"), nullable=False)
    fecha = Column(Date, nullable=False)
    importe = Column(Numeric(12, 2), nullable=False)
    medio = Column(String(30))  # transferencia, tarjeta, efectivo, domiciliacion
    referencia = Column(String(100))

    factura = relationship("Factura")


class MovimientoBancario(Base):
    """Movimiento bancario importado."""
    __tablename__ = "movimientos_bancarios"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    fecha = Column(Date, nullable=False)
    concepto = Column(String(500))
    importe = Column(Numeric(12, 2), nullable=False)
    saldo = Column(Numeric(12, 2))
    referencia = Column(String(100))
    conciliado = Column(Boolean, default=False)
    asiento_id = Column(Integer, ForeignKey("asientos.id"))
    cuenta_bancaria = Column(String(30))  # IBAN o numero

    __table_args__ = (
        Index("ix_movbanco_empresa_fecha", "empresa_id", "fecha"),
    )


class ActivoFijo(Base):
    """Activo fijo amortizable."""
    __tablename__ = "activos_fijos"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    descripcion = Column(String(200), nullable=False)
    tipo_bien = Column(String(50))  # vehiculos, mobiliario, equipos_informaticos, etc.
    subcuenta_activo = Column(String(10), nullable=False)  # 21x
    subcuenta_amortizacion = Column(String(10))  # 281x
    valor_adquisicion = Column(Numeric(12, 2), nullable=False)
    valor_residual = Column(Numeric(12, 2), default=Decimal("0"))
    fecha_adquisicion = Column(Date, nullable=False)
    fecha_baja = Column(Date)
    pct_amortizacion = Column(Numeric(5, 2), nullable=False)  # anual
    amortizacion_acumulada = Column(Numeric(12, 2), default=Decimal("0"))
    activo = Column(Boolean, default=True)

    empresa = relationship("Empresa", back_populates="activos")


class OperacionPeriodica(Base):
    """Operacion periodica programada."""
    __tablename__ = "operaciones_periodicas"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    tipo = Column(String(30), nullable=False)  # amortizacion, provision_paga, regularizacion_iva, periodificacion
    descripcion = Column(String(200))
    periodicidad = Column(String(20), nullable=False)  # mensual, trimestral, anual
    dia_ejecucion = Column(Integer, default=1)  # dia del mes
    ultimo_ejecutado = Column(Date)
    parametros = Column(JSON, default=dict)  # datos especificos de la operacion
    activa = Column(Boolean, default=True)


class Cuarentena(Base):
    """Documento en cuarentena con pregunta estructurada."""
    __tablename__ = "cuarentena"

    id = Column(Integer, primary_key=True)
    documento_id = Column(Integer, ForeignKey("documentos.id"), nullable=False)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    tipo_pregunta = Column(String(30), nullable=False)  # subcuenta, iva, entidad, duplicado, importe, otro
    pregunta = Column(Text, nullable=False)
    opciones = Column(JSON)  # lista de opciones sugeridas
    respuesta = Column(Text)
    resuelta = Column(Boolean, default=False)
    fecha_creacion = Column(DateTime, default=datetime.now)
    fecha_resolucion = Column(DateTime)

    documento = relationship("Documento")

    __table_args__ = (
        Index("ix_cuarentena_resuelta", "resuelta"),
    )


class AuditLog(Base):
    """Log de auditoria de todas las operaciones."""
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"))
    accion = Column(String(50), nullable=False)  # crear_asiento, registrar_factura, corregir_partida, etc.
    entidad_tipo = Column(String(30))  # documento, asiento, factura, etc.
    entidad_id = Column(Integer)
    datos_antes = Column(JSON)
    datos_despues = Column(JSON)
    usuario = Column(String(50), default="sfce")
    timestamp = Column(DateTime, default=datetime.now, nullable=False)
    detalle = Column(Text)

    __table_args__ = (
        Index("ix_audit_empresa_ts", "empresa_id", "timestamp"),
    )


class AprendizajeLog(Base):
    """Registro de patrones aprendidos por el motor."""
    __tablename__ = "aprendizaje_log"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"))
    patron_tipo = Column(String(50), nullable=False)  # cif_subcuenta, nombre_subcuenta, correccion_campo
    clave = Column(String(200), nullable=False)  # ej: CIF, nombre proveedor
    valor = Column(String(200), nullable=False)  # ej: subcuenta asignada
    confianza = Column(Integer, default=85)
    usos = Column(Integer, default=1)
    fecha_creacion = Column(DateTime, default=datetime.now)
    fecha_ultimo_uso = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("ix_aprend_clave", "patron_tipo", "clave"),
    )


class ModeloFiscalGenerado(Base):
    """Registro de modelos fiscales generados."""
    __tablename__ = "modelos_fiscales_generados"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    modelo = Column(String(10), nullable=False)
    ejercicio = Column(String(4), nullable=False)
    periodo = Column(String(10), nullable=False)
    casillas_json = Column(Text)  # JSON con todas las casillas
    ruta_boe = Column(String(500))
    ruta_pdf = Column(String(500))
    estado = Column(String(20), default="generado")  # generado | presentado
    fecha_generacion = Column(DateTime, default=datetime.now)
    fecha_presentacion = Column(DateTime, nullable=True)
    valido = Column(Boolean, default=True)
    notas = Column(Text, nullable=True)

    empresa = relationship("Empresa")

    __table_args__ = (
        Index("ix_mfg_empresa_ejercicio", "empresa_id", "ejercicio"),
    )
