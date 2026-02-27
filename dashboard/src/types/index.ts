/** Usuario autenticado */
export interface Usuario {
  id: number
  email: string
  nombre: string
  rol: 'admin' | 'gestor' | 'cliente'
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
