"""SFCE API — Esquemas Pydantic para request/response."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


# --- Empresa ---

class EmpresaOut(BaseModel):
    """Empresa en respuesta API."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    cif: str
    nombre: str
    forma_juridica: str
    territorio: str
    regimen_iva: str
    activa: bool


# --- Proveedor/Cliente ---

class ProveedorClienteOut(BaseModel):
    """Proveedor o cliente en respuesta API."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    cif: str
    nombre: str
    tipo: str
    subcuenta_gasto: Optional[str] = None
    codimpuesto: Optional[str] = None
    pais: Optional[str] = None


# --- Trabajador ---

class TrabajadorOut(BaseModel):
    """Trabajador en respuesta API."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    dni: str
    nombre: str
    bruto_mensual: Optional[float] = None
    pagas: Optional[int] = None
    activo: bool


# --- Documento ---

class DocumentoOut(BaseModel):
    """Documento procesado en respuesta API."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    tipo_doc: str
    ruta_pdf: Optional[str] = None
    estado: str
    confianza: Optional[int] = None
    ocr_tier: Optional[int] = None
    fecha_proceso: Optional[datetime] = None


# --- Cuarentena ---

class CuarentenaOut(BaseModel):
    """Cuarentena en respuesta API."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    documento_id: int
    empresa_id: int
    tipo_pregunta: str
    pregunta: str
    opciones: Optional[list] = None
    resuelta: bool
    respuesta: Optional[str] = None


class ResolverCuarentenaIn(BaseModel):
    """Body para resolver cuarentena."""
    respuesta: str


# --- Partida ---

class PartidaOut(BaseModel):
    """Partida (linea de asiento) en respuesta API."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    subcuenta: str
    debe: float
    haber: float
    concepto: Optional[str] = None


# --- Asiento ---

class AsientoOut(BaseModel):
    """Asiento contable en respuesta API."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    numero: Optional[int] = None
    fecha: date
    concepto: Optional[str] = None
    origen: Optional[str] = None
    partidas: list[PartidaOut] = []


# --- Factura ---

class FacturaOut(BaseModel):
    """Factura en respuesta API."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    tipo: str
    numero_factura: Optional[str] = None
    fecha_factura: Optional[date] = None
    cif_emisor: Optional[str] = None
    nombre_emisor: Optional[str] = None
    base_imponible: Optional[float] = None
    iva_importe: Optional[float] = None
    total: Optional[float] = None
    pagada: bool


# --- Activo fijo ---

class ActivoFijoOut(BaseModel):
    """Activo fijo en respuesta API."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    descripcion: str
    tipo_bien: Optional[str] = None
    valor_adquisicion: float
    amortizacion_acumulada: float
    fecha_adquisicion: date
    activo: bool


# --- PyG ---

class PyGOut(BaseModel):
    """Cuenta de Perdidas y Ganancias."""
    ingresos: float
    gastos: float
    resultado: float
    detalle_ingresos: dict[str, float]
    detalle_gastos: dict[str, float]


# --- Balance ---

class BalanceOut(BaseModel):
    """Balance de situacion."""
    activo: float
    pasivo: float
    patrimonio_neto: float


# --- Saldo subcuenta ---

class SaldoSubcuentaOut(BaseModel):
    """Saldo de una subcuenta."""
    subcuenta: str
    saldo: float


# --- Directorio ---

class DirectorioEntidadOut(BaseModel):
    """Entidad del directorio maestro."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    cif: Optional[str] = None
    nombre: str
    nombre_comercial: Optional[str] = None
    aliases: list[str] = []
    pais: str = "ESP"
    tipo_persona: Optional[str] = None
    forma_juridica: Optional[str] = None
    validado_aeat: bool = False
    validado_vies: bool = False
    fecha_alta: Optional[datetime] = None
    datos_enriquecidos: Optional[dict] = None


class DirectorioEntidadIn(BaseModel):
    """Body para crear/actualizar entidad en directorio."""
    cif: Optional[str] = None
    nombre: str
    nombre_comercial: Optional[str] = None
    aliases: list[str] = []
    pais: str = "ESP"
    tipo_persona: Optional[str] = None
    forma_juridica: Optional[str] = None


class DirectorioOverlayOut(BaseModel):
    """Overlay empresa-especifico de una entidad."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    empresa_id: int
    tipo: str
    subcuenta_gasto: Optional[str] = None
    codimpuesto: Optional[str] = None
    regimen: Optional[str] = None
    pais: Optional[str] = None


# --- Modelos Fiscales ---

class CasillaOut(BaseModel):
    """Casilla de un modelo fiscal."""
    numero: str
    descripcion: str
    valor: float
    editable: bool = False


class ResultadoValidacionOut(BaseModel):
    """Resultado de validacion de casillas AEAT."""
    valido: bool
    errores: list[str]
    advertencias: list[str]


class ModeloFiscalCalcOut(BaseModel):
    """Casillas calculadas de un modelo fiscal."""
    modelo: str
    ejercicio: str
    periodo: str
    casillas: list[CasillaOut]
    validacion: ResultadoValidacionOut


class GenerarModeloIn(BaseModel):
    """Request para calcular/generar un modelo fiscal."""
    empresa_id: int
    modelo: str
    ejercicio: str
    periodo: str
    casillas_override: Optional[dict[str, float]] = None


class CalendarioFiscalOut(BaseModel):
    """Entrada del calendario de obligaciones fiscales."""
    modelo: str
    nombre: str
    periodo: str
    ejercicio: str
    fecha_limite: str
    estado: str  # "pendiente" | "generado" | "presentado"


class HistoricoModeloOut(BaseModel):
    """Modelo fiscal generado anteriormente."""
    id: int
    modelo: str
    ejercicio: str
    periodo: str
    fecha_generacion: str
    ruta_boe: Optional[str] = None
    ruta_pdf: Optional[str] = None
    valido: bool = True


# --- Importar / Exportar / Cierre ---

class AsientoPreviewOut(BaseModel):
    """Linea de preview de asiento para confirmacion de importacion."""
    fecha: str
    concepto: str
    subcuenta: str
    debe: float
    haber: float


class ImportarPreviewOut(BaseModel):
    """Respuesta del endpoint de importacion (previo a confirmacion)."""
    importar_id: str
    total: int
    asientos_preview: list[AsientoPreviewOut]
    errores: list[str] = []


class CierreEstadoOut(BaseModel):
    """Estado de los pasos del cierre de ejercicio."""
    empresa_id: int
    ejercicio: str
    pasos: list[dict]  # [{numero, titulo, descripcion, estado}]


class ExportarOut(BaseModel):
    """Metadatos de la exportacion generada."""
    archivo: str
    total_registros: int


# --- Economico-Financiero ---

class RatioOut(BaseModel):
    """Ratio financiero calculado."""
    nombre: str
    categoria: str  # liquidez | solvencia | rentabilidad | eficiencia | estructura
    valor: float
    unidad: str  # ratio | porcentaje | dias | euros | veces
    semaforo: str  # verde | amarillo | rojo
    benchmark: Optional[float] = None
    evolucion: list[dict] = []  # [{mes, valor}]
    explicacion: str = ""


class RatiosEmpresaOut(BaseModel):
    """Todos los ratios de una empresa."""
    empresa_id: int
    fecha_calculo: str
    ratios: list[RatioOut]


class KPIOut(BaseModel):
    """KPI sectorial."""
    nombre: str
    valor: float
    objetivo: Optional[float] = None
    unidad: str
    semaforo: str
    evolucion: list[dict] = []


class TesoreriaOut(BaseModel):
    """Estado de tesoreria."""
    saldo_actual: float
    flujo_operativo: float
    flujo_inversion: float
    flujo_financiacion: float
    prevision_30d: float
    prevision_60d: float
    prevision_90d: float
    movimientos_recientes: list[dict] = []


class ScoringOut(BaseModel):
    """Credit scoring de entidad."""
    entidad_id: int
    nombre: str
    tipo: str
    puntuacion: int
    factores: dict = {}
    limite_sugerido: Optional[float] = None


class PresupuestoLineaOut(BaseModel):
    """Linea de presupuesto vs real."""
    subcuenta: str
    descripcion: str
    presupuestado: float
    real: float
    desviacion: float
    desviacion_pct: float
    semaforo: str


class ComparativaOut(BaseModel):
    """Comparativa interanual."""
    concepto: str
    valores: dict  # {"2023": 1000, "2024": 1200, ...}
    variacion: Optional[float] = None
    cagr: Optional[float] = None


# --- Copilot ---

class CopilotMensajeIn(BaseModel):
    """Mensaje del usuario al copiloto."""
    mensaje: str
    conversacion_id: Optional[int] = None


class CopilotRespuestaOut(BaseModel):
    """Respuesta del copiloto."""
    conversacion_id: int
    respuesta: str
    datos_enriquecidos: Optional[dict] = None  # tablas, charts, links
    funciones_invocadas: list[str] = []


class CopilotFeedbackIn(BaseModel):
    """Feedback sobre respuesta del copiloto."""
    conversacion_id: int
    mensaje_idx: int
    valoracion: int  # 1 o 5
    correccion: Optional[str] = None


# --- Configuracion ---

class ConfigAparienciaIn(BaseModel):
    """Configuracion de apariencia."""
    tema: str = "system"  # light | dark | system
    densidad: str = "comoda"
    idioma: str = "es"
    formato_fecha: str = "dd/MM/yyyy"
    formato_numero: str = "es-ES"


class BackupOut(BaseModel):
    """Informacion de backup."""
    id: str
    fecha: str
    tamano: str
    tipo: str  # manual | automatico


# --- PyG enriquecido (Task 5) ---

class PyGDetalleSubcuenta(BaseModel):
    subcuenta: str
    nombre: str
    importe: float


class PyGLineaOut(BaseModel):
    id: str                       # "L1", "L4", "MB", "EBITDA", "EBIT", "RES"
    descripcion: str
    importe: float
    pct_ventas: Optional[float] = None
    tipo: str                     # "ingreso"|"gasto"|"subtotal_positivo"|"subtotal_destacado"|"resultado_final"
    detalle: list[PyGDetalleSubcuenta] = []


class PyGWaterfallItem(BaseModel):
    nombre: str
    valor: float
    offset: float
    tipo: str                     # "inicio"|"negativo"|"positivo"|"subtotal"|"final"


class PyGResumen(BaseModel):
    ventas_netas: float
    margen_bruto: float
    margen_bruto_pct: float
    ebitda: float
    ebitda_pct: float
    ebit: float
    ebit_pct: float
    resultado: float
    resultado_pct: float


class PyGEvolucionMes(BaseModel):
    mes: str                      # "2022-01"
    ingresos: float
    gastos: float
    resultado: float


class PyGOut2(BaseModel):
    periodo: dict[str, str]
    resumen: PyGResumen
    lineas: list[PyGLineaOut]
    waterfall: list[PyGWaterfallItem]
    evolucion_mensual: list[PyGEvolucionMes]


# --- Balance enriquecido (Task 8) ---

class BalanceLinea(BaseModel):
    id: str
    descripcion: str
    importe: float
    badge: Optional[str] = None
    detalle: list[dict] = []


class BalanceSeccion(BaseModel):
    total: float
    lineas: list[BalanceLinea]


class BalanceActivo(BaseModel):
    total: float
    no_corriente: BalanceSeccion
    corriente: BalanceSeccion


class BalancePasivoOut(BaseModel):
    total: float
    no_corriente: BalanceSeccion
    corriente: BalanceSeccion


class BalancePatrimonio(BaseModel):
    total: float
    lineas: list[BalanceLinea]


class BalanceRatios(BaseModel):
    fondo_maniobra: float
    liquidez_corriente: float
    acid_test: float
    endeudamiento: float
    autonomia_financiera: float
    pmc_dias: Optional[int] = None
    pmp_dias: Optional[int] = None
    nof: float
    roe: Optional[float] = None
    roa: Optional[float] = None


class BalanceAlerta(BaseModel):
    codigo: str
    nivel: str                    # "critical"|"warning"|"info"
    mensaje: str
    valor_actual: Optional[float] = None
    benchmark: Optional[float] = None


class BalanceCuadre(BaseModel):
    ok: bool
    diferencia: float


class BalanceOut2(BaseModel):
    fecha_corte: str
    ejercicio_abierto: bool
    activo: BalanceActivo
    patrimonio_neto: BalancePatrimonio
    pasivo: BalancePasivoOut
    ratios: BalanceRatios
    alertas: list[BalanceAlerta]
    cuadre: BalanceCuadre


# --- Diario paginado (Task 10) ---

class DiarioAsientoOut(BaseModel):
    id: int
    numero: Optional[int] = None
    fecha: Optional[str] = None
    concepto: Optional[str] = None
    origen: Optional[str] = None
    total_debe: float = 0.0
    total_haber: float = 0.0
    cuadrado: bool = True
    partidas: list[dict] = []


class DiarioPaginadoOut(BaseModel):
    total: int
    offset: int
    limite: int
    asientos: list[DiarioAsientoOut]
