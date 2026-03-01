// dashboard/src/features/advisor/types.ts
export interface KPISectorial {
  id: string
  nombre: string
  valor: number
  unidad: string
  semaforo: 'verde' | 'amarillo' | 'rojo'
  benchmark_p50: number | null
}

export interface ResumenHoy {
  empresa_id: number
  fecha: string
  hoy: { ventas: number; covers: number; ticket_medio: number }
  variacion_vs_ayer_pct: number
  alertas: AlertaAdvisor[]
}

export interface AlertaAdvisor {
  id: string
  severidad: 'alta' | 'media' | 'baja'
  mensaje: string
}

export interface EmpresaPortfolio {
  id: number
  nombre: string
  sector: string
  cnae: string
  health_score: number
  ventas_hoy: number
  variacion_hoy_pct: number
  alerta_critica: AlertaAdvisor | null
}

export interface VentasDetalle {
  empresa_id: number
  periodo: { desde: string; hasta: string }
  por_familia: Record<string, number>
  top_productos: ProductoVenta[]
}

export interface ProductoVenta {
  nombre: string
  familia: string
  qty: number
  total: number
}

export interface CompraProveedor {
  nombre: string
  familia: string
  meses: Record<string, number>
  total: number
  variacion_mom_pct: number
}
