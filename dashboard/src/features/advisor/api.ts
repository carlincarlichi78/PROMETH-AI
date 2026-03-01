// dashboard/src/features/advisor/api.ts
import type {
  KPISectorial, ResumenHoy, EmpresaPortfolio,
  VentasDetalle, CompraProveedor,
} from './types'

const BASE = '/api/analytics'

async function apiFetch<T>(url: string): Promise<T> {
  const token = sessionStorage.getItem('sfce_token')
  const res = await fetch(url, {
    headers: { Authorization: token ? `Bearer ${token}` : '' },
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

export const advisorApi = {
  kpis: (empresaId: number, periodo?: string): Promise<{ kpis: KPISectorial[]; sector: string; alertas_activas: number }> =>
    apiFetch(`${BASE}/${empresaId}/kpis${periodo ? `?periodo=${periodo}` : ''}`),

  resumenHoy: (empresaId: number): Promise<ResumenHoy> =>
    apiFetch(`${BASE}/${empresaId}/resumen-hoy`),

  ventasDetalle: (empresaId: number, desde?: string, hasta?: string): Promise<VentasDetalle> => {
    const qs = [desde && `desde=${desde}`, hasta && `hasta=${hasta}`].filter(Boolean).join('&')
    return apiFetch(`${BASE}/${empresaId}/ventas-detalle${qs ? `?${qs}` : ''}`)
  },

  comprasProveedores: (empresaId: number, meses = 6): Promise<{ proveedores: CompraProveedor[] }> =>
    apiFetch(`${BASE}/${empresaId}/compras-proveedores?meses=${meses}`),

  portfolio: (): Promise<{ empresas: EmpresaPortfolio[] }> =>
    apiFetch('/api/empresas?resumen=true'),

  sectorBrain: (
    empresaId: number,
    kpi = 'ticket_medio',
  ): Promise<{
    disponible: boolean
    cnae?: string
    kpi?: string
    percentiles_sector?: { p25: number; p50: number; p75: number; n_empresas: number }
    valor_empresa?: number
    posicion?: { percentil: number; etiqueta: string; color: string }
    razon?: string
  }> =>
    apiFetch(`${BASE}/${empresaId}/sector-brain?kpi=${kpi}`),
}
