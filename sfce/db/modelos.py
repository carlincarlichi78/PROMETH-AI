"""SFCE DB — Modelos SQLAlchemy (24 tablas)."""

import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Enum, Float, ForeignKey, Integer,
    Numeric, String, Text, JSON, UniqueConstraint, Index, func
)
from sqlalchemy.orm import relationship, validates

from sfce.db.base import Base
import sfce.db.modelos_auth  # noqa: F401 — necesario para registrar Gestoria en el mapper antes de resolver relationships


class EstadoOnboarding(str, enum.Enum):
    """Estados posibles del onboarding de una empresa en el sistema."""
    CONFIGURADA = "configurada"           # Alta por el gestor, sin invitacion enviada aun
    PENDIENTE_CLIENTE = "pendiente_cliente"  # Invitacion enviada, empresario no ha completado
    CLIENTE_COMPLETADO = "cliente_completado"  # Empresario completo el wizard de onboarding
    CREADA_MASIVO = "creada_masivo"       # Alta automatica via pipeline onboarding masivo


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
    slug = Column(String(50), unique=True, nullable=True)  # identificador URL-friendly
    idempresa_fs = Column(Integer)  # ID en FacturaScripts (nullable si solo BD local)
    codejercicio_fs = Column(String(10))
    codagente_fs = Column(String(10), nullable=True)  # Agente FS asignado (para filtro por grupo)
    cnae = Column(String(4), nullable=True)  # Código CNAE del sector principal
    activa = Column(Boolean, default=True)
    gestoria_id = Column(Integer, ForeignKey("gestorias.id"), nullable=True)
    fecha_alta = Column(Date, nullable=False, default=date.today)
    config_extra = Column(JSON, default=dict)  # datos adicionales del config.yaml
    estado_onboarding = Column(
        Enum(EstadoOnboarding, name="estado_onboarding_enum",
             values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=EstadoOnboarding.CONFIGURADA,
        server_default=EstadoOnboarding.CONFIGURADA.value,
    )

    # Relaciones
    proveedores_clientes = relationship("ProveedorCliente", back_populates="empresa")
    trabajadores = relationship("Trabajador", back_populates="empresa")
    documentos = relationship("Documento", back_populates="empresa")
    asientos = relationship("Asiento", back_populates="empresa")
    activos = relationship("ActivoFijo", back_populates="empresa")
    gestoria = relationship("Gestoria", foreign_keys=[gestoria_id])

    @validates("cnae")
    def validar_cnae(self, clave: str, valor) -> str | None:
        """Valida que el CNAE sea exactamente 4 dígitos numéricos o None."""
        import re
        if valor is None:
            return valor
        if not re.match(r"^\d{4}$", str(valor)):
            raise ValueError(f"CNAE invalido '{valor}': debe ser un codigo de exactamente 4 digitos numericos (ej: '1081')")
        return str(valor)


class OnboardingCliente(Base):
    """Datos operativos que completa el empresario al aceptar la invitación."""
    __tablename__ = "onboarding_cliente"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, unique=True)
    iban = Column(String(34))
    banco_nombre = Column(String(100))
    email_facturas = Column(String(200))
    proveedores_json = Column(Text, default="[]")  # JSON array de nombres
    completado_en = Column(DateTime)
    completado_por = Column(Integer, ForeignKey("usuarios.id"), nullable=True)

    empresa = relationship("Empresa", foreign_keys=[empresa_id])


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
    ruta_disco = Column(String(1000), nullable=True)   # ruta absoluta en disco local
    cola_id = Column(Integer, ForeignKey("cola_procesamiento.id"), nullable=True)
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

    # Campos añadidos en migración 029 (conciliación inteligente)
    gestoria_id     = Column(Integer, nullable=True)
    nombre_archivo  = Column(String(300), nullable=True)
    importe_total   = Column(Numeric(12, 2), nullable=True)
    nif_proveedor   = Column(String(20), nullable=True)
    numero_factura  = Column(String(50), nullable=True)
    fecha_documento = Column(Date, nullable=True)

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


class CuentaBancaria(Base):
    """Cuenta bancaria de una empresa. Origen de movimientos C43."""
    __tablename__ = "cuentas_bancarias"

    id = Column(Integer, primary_key=True, autoincrement=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    gestoria_id = Column(Integer, nullable=False)  # FK logica, sin constraint para no acoplar BDs
    banco_codigo = Column(String(10), nullable=False)   # "2100" = CaixaBank
    banco_nombre = Column(String(100), nullable=False)
    iban = Column(String(34), nullable=False)
    alias = Column(String(100), nullable=False, default="")
    divisa = Column(String(3), nullable=False, default="EUR")
    activa = Column(Boolean, nullable=False, default=True)
    email_c43 = Column(String(200), nullable=True)  # email para recepcion automatica futura

    # Campos añadidos en migración 029
    saldo_bancario_ultimo = Column(Numeric(12, 2), nullable=True)
    fecha_saldo_ultimo    = Column(Date, nullable=True)

    __table_args__ = (
        UniqueConstraint("empresa_id", "iban", name="uq_cuenta_empresa_iban"),
    )

    movimientos = relationship("MovimientoBancario", back_populates="cuenta")


class MovimientoBancario(Base):
    """Movimiento bancario importado desde C43 u otras fuentes."""
    __tablename__ = "movimientos_bancarios"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenant
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    cuenta_id = Column(Integer, ForeignKey("cuentas_bancarias.id"), nullable=True)

    # Fechas
    fecha = Column(Date, nullable=False)
    fecha_valor = Column(Date, nullable=True)

    # Importes
    importe = Column(Numeric(12, 2), nullable=False)
    divisa = Column(String(3), nullable=False, default="EUR")
    importe_eur = Column(Numeric(12, 2), nullable=True)  # siempre en EUR para informes
    tipo_cambio = Column(Numeric(10, 6), nullable=True)
    saldo = Column(Numeric(12, 2), nullable=True)  # saldo tras el movimiento

    # Clasificacion
    signo = Column(String(1), nullable=False, default="D")  # 'D' cargo | 'H' abono
    concepto_comun = Column(String(5), nullable=False, default="")   # codigo AEB
    concepto_propio = Column(String(500), nullable=False, default="")
    referencia_1 = Column(String(100), nullable=False, default="")
    referencia_2 = Column(String(100), nullable=False, default="")
    nombre_contraparte = Column(String(200), nullable=False, default="")

    # Estado
    tipo_clasificado = Column(String(20), nullable=True)  # TPV|PROVEEDOR|NOMINA|IMPUESTO|COMISION|OTRO
    estado_conciliacion = Column(String(15), nullable=False, default="pendiente")  # pendiente|conciliado|revision|manual
    asiento_id = Column(Integer, ForeignKey("asientos.id"), nullable=True)

    # Deduplicacion: SHA256(iban + fecha + importe + referencia + num_orden)
    hash_unico = Column(String(64), nullable=False, unique=True)

    # Campos añadidos en migración 029 (conciliación inteligente)
    documento_id    = Column(Integer, ForeignKey("documentos.id"), nullable=True)
    score_confianza = Column(Float, nullable=True)
    metadata_match  = Column(Text, nullable=True)  # JSON
    capa_match      = Column(Integer, nullable=True)

    __table_args__ = (
        Index("ix_movbanco_empresa_fecha", "empresa_id", "fecha"),
        Index("ix_movbanco_estado", "estado_conciliacion"),
    )

    cuenta = relationship("CuentaBancaria", back_populates="movimientos")
    documento = relationship("Documento", foreign_keys=[documento_id], lazy="select")


class ArchivoIngestado(Base):
    """Registro de archivos bancarios procesados. Hash garantiza idempotencia."""
    __tablename__ = "archivos_ingestados"

    id = Column(Integer, primary_key=True, autoincrement=True)
    hash_archivo = Column(String(64), nullable=False, unique=True)
    nombre_original = Column(String(300), nullable=False)
    fuente = Column(String(20), nullable=False)   # 'email' | 'manual'
    tipo = Column(String(20), nullable=False)      # 'c43' | 'ticket_z' | 'factura'
    empresa_id = Column(Integer, nullable=False)
    gestoria_id = Column(Integer, nullable=False)
    fecha_proceso = Column(DateTime, nullable=False)
    movimientos_totales = Column(Integer, nullable=False, default=0)
    movimientos_nuevos = Column(Integer, nullable=False, default=0)
    movimientos_duplicados = Column(Integer, nullable=False, default=0)


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


# --- Tablas nuevas para dashboard rewrite ---

class Presupuesto(Base):
    """Presupuesto anual por partida contable."""
    __tablename__ = "presupuestos"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    ejercicio = Column(String(4), nullable=False)
    subcuenta = Column(String(20), nullable=False)
    descripcion = Column(String(200))
    importe_mensual = Column(JSON)  # {"01": 1000, "02": 1000, ...}
    importe_total = Column(Float, default=0)
    fecha_creacion = Column(DateTime, server_default=func.now())


class CentroCoste(Base):
    """Centro de coste (departamento, proyecto, sucursal)."""
    __tablename__ = "centros_coste"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    nombre = Column(String(100), nullable=False)
    tipo = Column(String(50))  # departamento | proyecto | sucursal | obra
    activo = Column(Boolean, default=True)
    fecha_creacion = Column(DateTime, server_default=func.now())


class AsignacionCoste(Base):
    """Asignacion de gasto a centro de coste."""
    __tablename__ = "asignaciones_coste"

    id = Column(Integer, primary_key=True)
    centro_id = Column(Integer, ForeignKey("centros_coste.id"), nullable=False)
    partida_id = Column(Integer, ForeignKey("partidas.id"), nullable=False)
    porcentaje = Column(Float, default=100)
    fecha_asignacion = Column(DateTime, server_default=func.now())


class ScoringHistorial(Base):
    """Historial de scoring de clientes/proveedores."""
    __tablename__ = "scoring_historial"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    entidad_tipo = Column(String(20))  # proveedor | cliente
    entidad_id = Column(Integer, nullable=False)
    puntuacion = Column(Integer)  # 0-100
    factores = Column(JSON)
    fecha = Column(DateTime, server_default=func.now())


class CopilotConversacion(Base):
    """Conversacion del copiloto IA."""
    __tablename__ = "copilot_conversaciones"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    usuario_id = Column(Integer, nullable=False)
    titulo = Column(String(200))
    mensajes = Column(JSON, default=list)  # [{rol, contenido, timestamp}]
    fecha_creacion = Column(DateTime, server_default=func.now())
    fecha_actualizacion = Column(DateTime, server_default=func.now())


class CopilotFeedback(Base):
    """Feedback del usuario sobre respuestas del copiloto."""
    __tablename__ = "copilot_feedback"

    id = Column(Integer, primary_key=True)
    conversacion_id = Column(Integer, ForeignKey("copilot_conversaciones.id"), nullable=False)
    mensaje_idx = Column(Integer, nullable=False)
    valoracion = Column(Integer)  # 1 (dislike) | 5 (like)
    correccion = Column(Text)
    fecha = Column(DateTime, server_default=func.now())


class InformeProgramado(Base):
    """Informe programado para generacion automatica."""
    __tablename__ = "informes_programados"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    nombre = Column(String(200), nullable=False)
    plantilla = Column(String(50))  # mensual | trimestral | anual | adhoc
    secciones = Column(JSON)  # ["pyg", "balance", "ratios", ...]
    periodicidad = Column(String(20))  # mensual | trimestral | anual | manual
    email_destino = Column(String(200))
    activo = Column(Boolean, default=True)
    ultimo_generado = Column(DateTime)
    fecha_creacion = Column(DateTime, server_default=func.now())


class VistaUsuario(Base):
    """Vista personalizada de filtros guardada por usuario."""
    __tablename__ = "vistas_usuario"

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, nullable=False)
    pagina = Column(String(100), nullable=False)  # ej: "facturas-emitidas"
    nombre = Column(String(100), nullable=False)
    filtros = Column(JSON, default=dict)
    columnas = Column(JSON)  # columnas visibles y orden
    es_default = Column(Boolean, default=False)
    fecha_creacion = Column(DateTime, server_default=func.now())


# ---------------------------------------------------------------------------
# Módulo de correo (migración 005)
# ---------------------------------------------------------------------------

class CuentaCorreo(Base):
    """Cuenta de correo IMAP o Microsoft Graph configurada por empresa o gestoría."""
    __tablename__ = "cuentas_correo"

    id = Column(Integer, primary_key=True)
    # empresa_id es nullable: cuentas de tipo 'gestoria'/'sistema'/'dedicada' no tienen empresa
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=True)
    gestoria_id = Column(Integer, ForeignKey("gestorias.id"), nullable=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    # 'empresa' | 'dedicada' | 'gestoria' | 'sistema' | 'asesor'
    tipo_cuenta = Column(String(20), nullable=False, default="empresa")
    nombre = Column(String(200), nullable=False)
    protocolo = Column(String(10), nullable=False)   # 'imap' | 'graph'
    servidor = Column(String(200))
    puerto = Column(Integer, default=993)
    ssl = Column(Boolean, default=True)
    usuario = Column(String(200), nullable=False)
    contrasena_enc = Column(Text)
    oauth_token_enc = Column(Text)
    oauth_refresh_enc = Column(Text)
    oauth_expires_at = Column(String(50))
    carpeta_entrada = Column(String(100), default="INBOX")
    ultimo_uid = Column(Integer, default=0)
    activa = Column(Boolean, default=True)
    polling_intervalo_segundos = Column(Integer, default=120)
    created_at = Column(DateTime, default=datetime.now)

    emails = relationship("EmailProcesado", back_populates="cuenta",
                          cascade="all, delete-orphan",
                          primaryjoin="CuentaCorreo.id == EmailProcesado.cuenta_id",
                          foreign_keys="[EmailProcesado.cuenta_id]")


class EmailProcesado(Base):
    """Email recibido y procesado por el módulo de correo."""
    __tablename__ = "emails_procesados"

    id = Column(Integer, primary_key=True)
    cuenta_id = Column(Integer, ForeignKey("cuentas_correo.id"), nullable=True)
    uid_servidor = Column(String(100), nullable=False)
    message_id = Column(String(200))
    remitente = Column(String(200), nullable=False)
    asunto = Column(String(500), default="")
    fecha_email = Column(String(50))
    # PENDIENTE | CLASIFICADO | CUARENTENA | PROCESADO | ERROR | IGNORADO
    estado = Column(String(20), nullable=False, default="PENDIENTE")
    # REGLA | IA | MANUAL
    nivel_clasificacion = Column(String(10))
    empresa_destino_id = Column(Integer, ForeignKey("empresas.id"))
    confianza_ia = Column(Float)
    procesado_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)
    es_respuesta_ack = Column(Boolean, default=False)
    score_confianza = Column(Float)
    motivo_cuarentena = Column(String(50))

    __table_args__ = (UniqueConstraint("cuenta_id", "uid_servidor"),)

    cuenta = relationship("CuentaCorreo", back_populates="emails")
    adjuntos = relationship("AdjuntoEmail", back_populates="email",
                            cascade="all, delete-orphan")
    enlaces = relationship("EnlaceEmail", back_populates="email",
                           cascade="all, delete-orphan")


class AdjuntoEmail(Base):
    """Adjunto PDF/imagen extraído de un email procesado."""
    __tablename__ = "adjuntos_email"

    id = Column(Integer, primary_key=True)
    email_id = Column(Integer, ForeignKey("emails_procesados.id"), nullable=False)
    nombre_original = Column(String(300), nullable=False)
    nombre_renombrado = Column(String(300))
    ruta_archivo = Column(String(500))
    mime_type = Column(String(100), default="application/pdf")
    tamano_bytes = Column(Integer, default=0)
    documento_id = Column(Integer)   # FK lógica a documentos del pipeline
    # PENDIENTE | OCR_OK | OCR_ERROR | DUPLICADO
    estado = Column(String(20), nullable=False, default="PENDIENTE")
    created_at = Column(DateTime, default=datetime.now)

    email = relationship("EmailProcesado", back_populates="adjuntos")


class EnlaceEmail(Base):
    """Enlace extraído del cuerpo HTML de un email."""
    __tablename__ = "enlaces_email"

    id = Column(Integer, primary_key=True)
    email_id = Column(Integer, ForeignKey("emails_procesados.id"), nullable=False)
    url = Column(Text, nullable=False)
    dominio = Column(String(200))
    # AEAT | BANCO | SUMINISTRO | CLOUD | OTRO
    patron_detectado = Column(String(20), default="OTRO")
    # PENDIENTE | DESCARGANDO | DESCARGADO | ERROR | IGNORADO
    estado = Column(String(20), nullable=False, default="PENDIENTE")
    nombre_archivo = Column(String(300))
    ruta_archivo = Column(String(500))
    tamano_bytes = Column(Integer)
    adjunto_id = Column(Integer, ForeignKey("adjuntos_email.id"))
    created_at = Column(DateTime, default=datetime.now)

    email = relationship("EmailProcesado", back_populates="enlaces")


class RemitenteAutorizado(Base):
    """Whitelist de remitentes de email por empresa."""
    __tablename__ = "remitentes_autorizados"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    email = Column(String(200), nullable=False)
    nombre = Column(String(200))
    activo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)


class ContrasenaZip(Base):
    """Contraseñas para descomprimir ZIPs protegidos por empresa/remitente."""
    __tablename__ = "contrasenas_zip"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    remitente_patron = Column(String(200))   # None = aplica a todos
    contrasenas_json = Column(Text, default="[]")  # lista JSON de strings
    activo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)


class ReglaClasificacionCorreo(Base):
    """Regla de clasificación automática de emails entrantes."""
    __tablename__ = "reglas_clasificacion_correo"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"))
    # REMITENTE_EXACTO | DOMINIO | ASUNTO_CONTIENE | COMPOSITE
    tipo = Column(String(30), nullable=False)
    condicion_json = Column(Text, nullable=False, default="{}")
    # CLASIFICAR | IGNORAR | APROBAR_MANUAL
    accion = Column(String(20), nullable=False, default="CLASIFICAR")
    slug_destino = Column(String(100))
    confianza = Column(Float, default=1.0)
    # MANUAL | APRENDIZAJE
    origen = Column(String(15), default="MANUAL")
    activa = Column(Boolean, default=True)
    prioridad = Column(Integer, default=100)
    created_at = Column(DateTime, default=datetime.now)


class CertificadoAAP(Base):
    """Certificado digital de una empresa (metadatos, sin el P12)."""
    __tablename__ = "certificados_aap"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    cif = Column(String(20), nullable=False)
    nombre = Column(String(200), nullable=False)
    tipo = Column(String(50), nullable=False)      # representante | firma | sello
    organismo = Column(String(100))                # AEAT | SEDE | SEGURIDAD_SOCIAL
    caducidad = Column(Date, nullable=False)
    alertado_30d = Column(Boolean, default=False)
    alertado_7d = Column(Boolean, default=False)
    creado_en = Column(DateTime, default=datetime.utcnow)
    actualizado_en = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class NotificacionAAP(Base):
    """Notificacion/requerimiento de una AAPP para una empresa."""
    __tablename__ = "notificaciones_aap"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    organismo = Column(String(100), nullable=False)  # AEAT | DGT | DEHU | JUNTA
    asunto = Column(String(500), nullable=False)
    tipo = Column(String(50), nullable=False)         # requerimiento | notificacion | sancion | embargo
    fecha_recepcion = Column(DateTime, default=datetime.utcnow)
    fecha_limite = Column(Date)
    leida = Column(Boolean, default=False)
    url_documento = Column(String(500))
    origen = Column(String(50), default="certigestor")  # certigestor | manual | webhook
    creado_en = Column(DateTime, default=datetime.utcnow)


class ColaProcesamiento(Base):
    """Cola de procesamiento de documentos para Gate 0."""
    __tablename__ = "cola_procesamiento"

    id = Column(Integer, primary_key=True, autoincrement=True)
    empresa_id = Column(Integer, nullable=False, index=True)
    documento_id = Column(Integer, nullable=True)
    nombre_archivo = Column(String(500), nullable=False)
    ruta_archivo = Column(String(1000), nullable=False)
    estado = Column(String(20), default="PENDIENTE", index=True)
    trust_level = Column(String(20), default="BAJA")
    score_final = Column(Float, nullable=True)
    decision = Column(String(30), nullable=True)
    hints_json = Column(Text, default="{}")
    sha256 = Column(String(64), nullable=True, index=True)
    datos_ocr_json = Column(Text, nullable=True)          # JSON datos extraídos por OCR
    coherencia_score = Column(Float, nullable=True)        # Score coherencia fiscal [0-100]
    worker_inicio = Column(DateTime, nullable=True)        # Timestamp inicio procesamiento (para recovery)
    reintentos = Column(Integer, default=0)                # Contador de reintentos por recovery
    empresa_origen_correo_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DocumentoTracking(Base):
    """Tracking de estados de documentos."""
    __tablename__ = "documento_tracking"

    id = Column(Integer, primary_key=True, autoincrement=True)
    documento_id = Column(Integer, nullable=False, index=True)
    estado = Column(String(30), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    actor = Column(String(50), default="sistema")
    detalle_json = Column(Text, default="{}")


class NotificacionUsuario(Base):
    """Notificaciones para empresarios: errores doc, avisos gestor, info pipeline."""
    __tablename__ = "notificaciones_usuario"

    id = Column(Integer, primary_key=True, autoincrement=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    documento_id = Column(Integer, ForeignKey("documentos.id"), nullable=True)
    titulo = Column(String(200), nullable=False)
    descripcion = Column(Text, nullable=True)
    # tipo: error_doc | aviso_gestor | info | duplicado | doc_ilegible
    tipo = Column(String(30), nullable=False, default="aviso_gestor")
    # origen: manual (gestor) | pipeline (automático)
    origen = Column(String(20), nullable=False, default="manual")
    leida = Column(Boolean, nullable=False, default=False)
    fecha_creacion = Column(DateTime, nullable=False, default=datetime.utcnow)
    fecha_lectura = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_notif_empresa_leida", "empresa_id", "leida"),
    )


class SupplierRule(Base):
    """Reglas aprendidas por proveedor para pre-rellenar campos en Gate 0."""
    __tablename__ = "supplier_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    empresa_id = Column(Integer, nullable=True, index=True)
    emisor_cif = Column(String(20), nullable=True, index=True)
    emisor_nombre_patron = Column(String(200), nullable=True)
    tipo_doc_sugerido = Column(String(10), nullable=True)
    subcuenta_gasto = Column(String(20), nullable=True)
    codimpuesto = Column(String(10), nullable=True)
    regimen = Column(String(30), nullable=True)
    aplicaciones = Column(Integer, default=0)
    confirmaciones = Column(Integer, default=0)
    tasa_acierto = Column(Float, default=0.0)
    auto_aplicable = Column(Boolean, default=False)
    nivel = Column(String(20), default="empresa")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ConfigProcesamientoEmpresa(Base):
    """Configuración del modo de procesamiento automático por empresa."""
    __tablename__ = "config_procesamiento_empresa"

    id                    = Column(Integer, primary_key=True, autoincrement=True)
    empresa_id            = Column(Integer, ForeignKey("empresas.id"), nullable=False, unique=True)
    modo                  = Column(String(20), nullable=False, default="revision")  # auto | revision
    schedule_minutos      = Column(Integer, nullable=True, default=None)  # None = manual
    ocr_previo            = Column(Boolean, nullable=False, default=True)
    notif_calidad_cliente = Column(Boolean, nullable=False, default=True)
    notif_contable_gestor = Column(Boolean, nullable=False, default=True)
    ultimo_pipeline       = Column(DateTime, nullable=True, default=None)
    created_at            = Column(DateTime, default=datetime.utcnow)
    updated_at            = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    empresa = relationship("Empresa", backref="config_procesamiento", uselist=False)


class MensajeEmpresa(Base):
    """Mensajes contextuales entre cliente y gestor por empresa."""
    __tablename__ = "mensajes_empresa"

    id = Column(Integer, primary_key=True, autoincrement=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    autor_id = Column(Integer, nullable=False)
    contenido = Column(Text, nullable=False)
    contexto_tipo = Column(String(20), nullable=True)   # documento | fiscal | libre
    contexto_id = Column(Integer, nullable=True)
    contexto_desc = Column(String(200), nullable=True)
    leido_cliente = Column(Boolean, nullable=False, default=False)
    leido_gestor = Column(Boolean, nullable=False, default=False)
    fecha_creacion = Column(DateTime, nullable=False, default=datetime.utcnow)

    empresa = relationship("Empresa", backref="mensajes")


class PushToken(Base):
    """Token de dispositivo para notificaciones push via Expo."""
    __tablename__ = "push_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    usuario_id = Column(Integer, nullable=False, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=True)
    token = Column(String(200), nullable=False, unique=True)
    plataforma = Column(String(10), nullable=True)  # ios | android
    activo = Column(Boolean, nullable=False, default=True)
    fecha_registro = Column(DateTime, nullable=False, default=datetime.utcnow)
    fecha_ultimo_uso = Column(DateTime, nullable=True)


class SugerenciaMatch(Base):
    """Candidato de conciliación sugerido por el motor inteligente."""
    __tablename__ = "sugerencias_match"

    id = Column(Integer, primary_key=True)
    movimiento_id = Column(Integer, ForeignKey("movimientos_bancarios.id"), nullable=False)
    documento_id = Column(Integer, ForeignKey("documentos.id"), nullable=False)
    score = Column(Float, nullable=False)
    capa_origen = Column(Integer, nullable=False)
    activa = Column(Boolean, default=True, nullable=False)
    confirmada = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    movimiento = relationship("MovimientoBancario", foreign_keys=[movimiento_id])
    documento = relationship("Documento", foreign_keys=[documento_id])

    __table_args__ = (
        UniqueConstraint("movimiento_id", "documento_id"),
    )


class PatronConciliacion(Base):
    """Patrón aprendido de confirmaciones manuales."""
    __tablename__ = "patrones_conciliacion"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    patron_texto = Column(String(500), nullable=False)
    patron_limpio = Column(String(500))
    nif_proveedor = Column(String(20))
    cuenta_contable = Column(String(10))
    rango_importe_aprox = Column(String(20), nullable=False)
    frecuencia_exito = Column(Integer, default=1, nullable=False)
    ultima_confirmacion = Column(Date)

    __table_args__ = (
        UniqueConstraint("empresa_id", "patron_texto", "rango_importe_aprox"),
    )


class ConciliacionParcial(Base):
    """Conciliación N:1 — una transferencia cubre múltiples facturas."""
    __tablename__ = "conciliaciones_parciales"

    id = Column(Integer, primary_key=True)
    movimiento_id = Column(Integer, ForeignKey("movimientos_bancarios.id"), nullable=False)
    documento_id = Column(Integer, ForeignKey("documentos.id"), nullable=False)
    importe_asignado = Column(Numeric(12, 2), nullable=False)
    confirmado_en = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("movimiento_id", "documento_id"),
    )


# Registro automático de modelos auxiliares en Base.metadata
# para que create_all() los cree junto al resto de tablas.
try:
    from sfce.db import modelos_testing as _mt  # noqa: F401
except ImportError:
    pass

