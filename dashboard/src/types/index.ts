/** Usuario autenticado */
export interface Usuario {
  id: number
  email: string
  nombre: string
  rol: 'superadmin' | 'admin_gestoria' | 'asesor' | 'asesor_independiente' | 'cliente'
  gestoria_id?: number | null
  plan_tier?: 'basico' | 'pro' | 'premium'
}

/** Empresa/cliente contable (coincide con EmpresaOut del backend) */
export interface Empresa {
  id: number
  cif: string
  nombre: string
  forma_juridica: string
  territorio: string
  regimen_iva: string
  activa: boolean
  estado_onboarding?: string
}

/** Cuenta de Perdidas y Ganancias (coincide con PyGOut) */
export interface PyG {
  ingresos: number
  gastos: number
  resultado: number
  detalle_ingresos: Record<string, number>
  detalle_gastos: Record<string, number>
}

/** Balance de situacion (coincide con BalanceOut) */
export interface Balance {
  activo: number
  pasivo: number
  patrimonio_neto: number
}

/** Partida de asiento (coincide con PartidaOut) */
export interface Partida {
  id: number
  subcuenta: string
  debe: number
  haber: number
  concepto: string | null
}

/** Asiento contable (coincide con AsientoOut) */
export interface Asiento {
  id: number
  numero: number | null
  fecha: string
  concepto: string | null
  origen: string | null
  partidas: Partida[]
}

/** Factura (coincide con FacturaOut) */
export interface Factura {
  id: number
  tipo: string
  numero_factura: string | null
  fecha_factura: string | null
  cif_emisor: string | null
  nombre_emisor: string | null
  base_imponible: number | null
  iva_importe: number | null
  total: number | null
  pagada: boolean
}

/** Activo fijo (coincide con ActivoFijoOut) */
export interface ActivoFijo {
  id: number
  descripcion: string
  tipo_bien: string | null
  valor_adquisicion: number
  amortizacion_acumulada: number
  fecha_adquisicion: string
  activo: boolean
}

/** Proveedor o cliente (coincide con ProveedorClienteOut) */
export interface ProveedorCliente {
  id: number
  cif: string
  nombre: string
  tipo: string
  subcuenta_gasto: string | null
  codimpuesto: string | null
  pais: string | null
}

/** Trabajador (coincide con TrabajadorOut) */
export interface Trabajador {
  id: number
  dni: string
  nombre: string
  bruto_mensual: number | null
  pagas: number | null
  activo: boolean
}

/** Documento en pipeline (coincide con DocumentoOut) */
export interface Documento {
  id: number
  tipo_doc: string
  ruta_pdf: string | null
  estado: string
  confianza: number | null
  ocr_tier: number | null
  fecha_proceso: string | null
}

/** Documento en cuarentena (coincide con CuarentenaOut) */
export interface Cuarentena {
  id: number
  documento_id: number
  empresa_id: number
  tipo_pregunta: string
  pregunta: string
  opciones: string[] | null
  resuelta: boolean
  respuesta: string | null
}

/** Evento WebSocket */
export interface EventoWS {
  tipo: string
  canal: string
  datos: Record<string, unknown>
  timestamp: string
}

/** Respuesta de login */
export interface LoginResponse {
  access_token: string
  token_type: string
}

// --- PyG enriquecido (Task 5/6) ---

export interface PyGDetalleSubcuenta {
  subcuenta: string
  nombre: string
  importe: number
}

export interface PyGLinea {
  id: string
  descripcion: string
  importe: number
  pct_ventas: number | null
  tipo: 'ingreso' | 'gasto' | 'subtotal_positivo' | 'subtotal_destacado' | 'resultado_final'
  detalle: PyGDetalleSubcuenta[]
}

export interface PyGWaterfallItem {
  nombre: string
  valor: number
  offset: number
  tipo: 'inicio' | 'negativo' | 'positivo' | 'subtotal' | 'final'
}

export interface PyGResumen {
  ventas_netas: number
  margen_bruto: number
  margen_bruto_pct: number
  ebitda: number
  ebitda_pct: number
  ebit: number
  ebit_pct: number
  resultado: number
  resultado_pct: number
}

export interface PyGEvolucionMes {
  mes: string
  ingresos: number
  gastos: number
  resultado: number
}

export interface PyG2 {
  periodo: { desde: string; hasta: string }
  resumen: PyGResumen
  lineas: PyGLinea[]
  waterfall: PyGWaterfallItem[]
  evolucion_mensual: PyGEvolucionMes[]
}

// --- Diario paginado (Task 10/11) ---

export interface DiarioPartida {
  subcuenta: string
  nombre: string
  debe: number
  haber: number
}

export interface DiarioAsiento {
  id: number
  numero: number | null
  fecha: string | null
  concepto: string | null
  origen: string | null
  total_debe: number
  total_haber: number
  cuadrado: boolean
  partidas: DiarioPartida[]
}

export interface DiarioPaginado {
  total: number
  offset: number
  limite: number
  asientos: DiarioAsiento[]
}

// --- Balance enriquecido (Task 8/9) ---

export interface BalanceLinea {
  id: string
  descripcion: string
  importe: number
  badge?: string
  detalle?: Array<{ subcuenta: string; nombre: string; importe: number }>
}

export interface BalanceSeccion {
  total: number
  lineas: BalanceLinea[]
}

export interface BalanceRatios {
  fondo_maniobra: number
  liquidez_corriente: number
  acid_test: number
  endeudamiento: number
  autonomia_financiera: number
  pmc_dias: number | null
  pmp_dias: number | null
  nof: number
  roe: number | null
  roa: number | null
}

export interface BalanceAlerta {
  codigo: string
  nivel: 'critical' | 'warning' | 'info'
  mensaje: string
  valor_actual?: number
  benchmark?: number
}

export interface Balance2 {
  fecha_corte: string
  ejercicio_abierto: boolean
  activo: { total: number; no_corriente: BalanceSeccion; corriente: BalanceSeccion }
  patrimonio_neto: { total: number; lineas: BalanceLinea[] }
  pasivo: { total: number; no_corriente: BalanceSeccion; corriente: BalanceSeccion }
  ratios: BalanceRatios
  alertas: BalanceAlerta[]
  cuadre: { ok: boolean; diferencia: number }
}
