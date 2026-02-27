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
