/** Usuario autenticado */
export interface Usuario {
  id: number
  email: string
  nombre: string
  rol: 'admin' | 'gestor' | 'cliente'
}

/** Empresa/cliente contable */
export interface Empresa {
  id: number
  nombre: string
  cif: string
  forma_juridica: string
  regimen_iva: string
  territorio: string
  ejercicio_activo: string
  estado: string
  documentos_pendientes: number
  cuarentena_pendiente: number
}

/** Cuenta de Perdidas y Ganancias */
export interface PyG {
  empresa_id: number
  ejercicio: string
  hasta_fecha: string
  ingresos: LineaPyG[]
  gastos: LineaPyG[]
  resultado_explotacion: number
  resultado_financiero: number
  resultado_antes_impuestos: number
  impuesto_sociedades: number
  resultado_neto: number
}

export interface LineaPyG {
  cuenta: string
  descripcion: string
  debe: number
  haber: number
  saldo: number
}

/** Balance de situacion */
export interface Balance {
  empresa_id: number
  hasta_fecha: string
  activo: LineaBalance[]
  pasivo: LineaBalance[]
  patrimonio_neto: LineaBalance[]
  total_activo: number
  total_pasivo_patrimonio: number
  cuadra: boolean
}

export interface LineaBalance {
  cuenta: string
  descripcion: string
  saldo: number
}

/** Asiento contable */
export interface Asiento {
  id: number
  numero: number
  fecha: string
  concepto: string
  documento: string
  importe: number
  partidas: Partida[]
}

export interface Partida {
  id: number
  codsubcuenta: string
  concepto: string
  debe: number
  haber: number
}

/** Factura (cliente o proveedor) */
export interface Factura {
  id: number
  tipo: 'cliente' | 'proveedor'
  numero: string
  fecha: string
  nombre_entidad: string
  cif_entidad: string
  base_imponible: number
  iva_importe: number
  irpf_importe: number
  total: number
  pagada: boolean
  codejercicio: string
}

/** Documento en pipeline */
export interface Documento {
  id: number
  nombre_archivo: string
  tipo_doc: string
  estado: 'pendiente' | 'procesado' | 'cuarentena' | 'error'
  confianza: number
  fecha_recepcion: string
  fecha_proceso: string | null
  emisor_nombre: string | null
  importe_total: number | null
  ocr_tier: number | null
}

/** Documento en cuarentena */
export interface Cuarentena {
  id: number
  documento_id: number
  nombre_archivo: string
  motivo: string
  pregunta: string
  opciones: string[]
  respuesta: string | null
  resuelto: boolean
  fecha_creacion: string
  fecha_resolucion: string | null
}

/** Activo fijo */
export interface ActivoFijo {
  id: number
  descripcion: string
  fecha_alta: string
  valor_adquisicion: number
  valor_residual: number
  vida_util_anos: number
  amortizacion_anual: number
  amortizacion_acumulada: number
  valor_neto_contable: number
  cuenta_activo: string
  cuenta_amortizacion: string
}

/** Proveedor o cliente */
export interface ProveedorCliente {
  id: number
  tipo: 'proveedor' | 'cliente'
  nombre: string
  cif: string
  codsubcuenta: string
  codpais: string
  email: string | null
  telefono: string | null
}

/** Trabajador */
export interface Trabajador {
  id: number
  nombre: string
  nif: string
  nss: string | null
  categoria: string | null
  salario_bruto_anual: number
  fecha_alta: string
  fecha_baja: string | null
  activo: boolean
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

/** Respuesta paginada */
export interface RespuestaPaginada<T> {
  items: T[]
  total: number
  pagina: number
  por_pagina: number
}
