// Tipos TypeScript — Modulo Economico-Financiero

export interface Ratio {
  nombre: string
  categoria: 'liquidez' | 'solvencia' | 'rentabilidad' | 'eficiencia' | 'estructura'
  valor: number
  unidad: 'ratio' | 'porcentaje' | 'dias' | 'euros' | 'veces'
  semaforo: 'verde' | 'amarillo' | 'rojo'
  benchmark: number | null
  evolucion: { mes: string; valor: number }[]
  explicacion: string
}

export interface RatiosEmpresa {
  empresa_id: number
  fecha_calculo: string
  ratios: Ratio[]
}

export interface KPI {
  nombre: string
  valor: number
  objetivo: number | null
  unidad: string
  semaforo: 'verde' | 'amarillo' | 'rojo'
  evolucion: { mes: string; valor: number }[]
}

export interface KPIsEmpresa {
  empresa_id: number
  kpis: KPI[]
}

export interface Tesoreria {
  saldo_actual: number
  flujo_operativo: number
  flujo_inversion: number
  flujo_financiacion: number
  prevision_30d: number
  prevision_60d: number
  prevision_90d: number
  movimientos_recientes: {
    fecha: string
    concepto: string
    importe: number
    saldo: number
  }[]
}

export interface CashflowMensual {
  empresa_id: number
  ejercicio: string
  cashflow_mensual: { mes: string; flujo: number }[]
}

export interface ScoringEntidad {
  entidad_id: number
  nombre: string
  tipo: 'proveedor' | 'cliente'
  puntuacion: number
  factores: Record<string, number>
  limite_sugerido: number | null
}

export interface ScoringEmpresa {
  empresa_id: number
  tipo: 'proveedor' | 'cliente'
  scoring: {
    entidad_id: number
    puntuacion: number
    factores: Record<string, number>
    fecha: string | null
  }[]
}

export interface PresupuestoLinea {
  subcuenta: string
  descripcion: string
  presupuestado: number
  real: number
  desviacion: number
  desviacion_pct: number
  semaforo: 'verde' | 'amarillo' | 'rojo'
}

export interface PresupuestoEmpresa {
  empresa_id: number
  ejercicio: string
  lineas: PresupuestoLinea[]
}

export interface ComparativaItem {
  concepto: string
  valores: Record<string, number>
  variacion: number | null
  cagr: number | null
}

export interface ComparativaEmpresa {
  empresa_id: number
  ejercicios: string[]
  comparativa: ComparativaItem[]
}

export interface CentroCoste {
  id: number
  empresa_id: number
  nombre: string
  tipo: 'departamento' | 'proyecto' | 'sucursal' | 'obra'
  activo: boolean
  fecha_creacion: string
}

export interface InformeProgramado {
  id: number
  nombre: string
  plantilla: string
  periodicidad: 'mensual' | 'trimestral' | 'anual' | 'manual'
  email_destino: string
  ultimo_generado: string | null
}

export interface PlantillaInforme {
  id: string
  nombre: string
  descripcion: string
  secciones: string[]
  periodicidad: string
}
