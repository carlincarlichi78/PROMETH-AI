// API client — Modulo Economico-Financiero

import type {
  RatiosEmpresa, KPIsEmpresa, Tesoreria, CashflowMensual,
  ScoringEmpresa, PresupuestoEmpresa, ComparativaEmpresa,
  PlantillaInforme,
} from '@/types/economico'

const BASE = '/api/economico'

async function apiFetch<T>(url: string): Promise<T> {
  const token = localStorage.getItem('sfce_token')
  const res = await fetch(url, {
    headers: { Authorization: token ? `Bearer ${token}` : '' },
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

export const economicoApi = {
  ratios: (empresaId: number, ejercicio?: string): Promise<RatiosEmpresa> =>
    apiFetch(`${BASE}/${empresaId}/ratios${ejercicio ? `?ejercicio=${ejercicio}` : ''}`),

  kpis: (empresaId: number): Promise<KPIsEmpresa> =>
    apiFetch(`${BASE}/${empresaId}/kpis`),

  tesoreria: (empresaId: number): Promise<Tesoreria> =>
    apiFetch(`${BASE}/${empresaId}/tesoreria`),

  cashflow: (empresaId: number): Promise<CashflowMensual> =>
    apiFetch(`${BASE}/${empresaId}/cashflow`),

  scoring: (empresaId: number, tipo: 'proveedor' | 'cliente'): Promise<ScoringEmpresa> =>
    apiFetch(`${BASE}/${empresaId}/scoring?tipo=${tipo}`),

  presupuesto: (empresaId: number, ejercicio?: string): Promise<PresupuestoEmpresa> =>
    apiFetch(`${BASE}/${empresaId}/presupuesto${ejercicio ? `?ejercicio=${ejercicio}` : ''}`),

  comparativa: (empresaId: number, ejercicios?: string[]): Promise<ComparativaEmpresa> => {
    const qs = ejercicios ? `?ejercicios=${ejercicios.join(',')}` : ''
    return apiFetch(`${BASE}/${empresaId}/comparativa${qs}`)
  },

  plantillasInformes: (): Promise<{ plantillas: PlantillaInforme[] }> =>
    apiFetch('/api/informes/plantillas'),

  generarInforme: (empresaId: number, plantillaId: string, ejercicio?: string): void => {
    const token = localStorage.getItem('sfce_token')
    const ej = ejercicio ? `&ejercicio=${ejercicio}` : ''
    const url = `/api/informes/generar?empresa_id=${empresaId}&plantilla_id=${plantillaId}${ej}`
    // Descarga directa via anchor
    const a = document.createElement('a')
    a.href = url
    if (token) a.setAttribute('data-token', token)
    a.download = `informe_${plantillaId}.pdf`
    a.click()
  },
}
