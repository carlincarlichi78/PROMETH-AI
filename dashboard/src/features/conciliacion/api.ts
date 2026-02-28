import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

const BASE = '/api/bancario'

export interface CuentaBancaria {
  id: number
  empresa_id: number
  banco_codigo: string
  banco_nombre: string
  iban: string
  alias: string
  divisa: string
  activa: boolean
}

export interface MovimientoBancario {
  id: number
  fecha: string
  importe: number
  signo: 'D' | 'H'
  concepto_propio: string
  nombre_contraparte: string
  tipo_clasificado: string | null
  estado_conciliacion: 'pendiente' | 'conciliado' | 'revision' | 'manual'
  asiento_id: number | null
}

export interface EstadoConciliacion {
  total: number
  conciliados: number
  pendientes: number
  revision: number
  pct_conciliado: number
}

export interface ResultadoConciliacion {
  matches_exactos: number
  matches_aproximados: number
  total: number
}

export interface ResultadoIngesta {
  movimientos_totales: number
  movimientos_nuevos: number
  movimientos_duplicados: number
  ya_procesado: boolean
}

// ---------------------------------------------------------------------------
// Queries
// ---------------------------------------------------------------------------

export function useCuentas(empresaId: number) {
  return useQuery<CuentaBancaria[]>({
    queryKey: ['cuentas-bancarias', empresaId],
    queryFn: () =>
      fetch(`${BASE}/${empresaId}/cuentas`).then(r => {
        if (!r.ok) throw new Error('Error al cargar cuentas')
        return r.json()
      }),
    enabled: empresaId > 0,
  })
}

export function useMovimientos(empresaId: number, estado?: string) {
  const params = estado ? `?estado=${estado}` : ''
  return useQuery<MovimientoBancario[]>({
    queryKey: ['movimientos-bancarios', empresaId, estado],
    queryFn: () =>
      fetch(`${BASE}/${empresaId}/movimientos${params}`).then(r => {
        if (!r.ok) throw new Error('Error al cargar movimientos')
        return r.json()
      }),
    enabled: empresaId > 0,
  })
}

export function useEstadoConciliacion(empresaId: number) {
  return useQuery<EstadoConciliacion>({
    queryKey: ['estado-conciliacion', empresaId],
    queryFn: () =>
      fetch(`${BASE}/${empresaId}/estado_conciliacion`).then(r => {
        if (!r.ok) throw new Error('Error al cargar estado')
        return r.json()
      }),
    enabled: empresaId > 0,
  })
}

// ---------------------------------------------------------------------------
// Mutations
// ---------------------------------------------------------------------------

export function useIngestarExtracto(empresaId: number) {
  const qc = useQueryClient()
  return useMutation<ResultadoIngesta, Error, { archivo: File; iban: string }>({
    mutationFn: ({ archivo, iban }) => {
      const form = new FormData()
      form.append('archivo', archivo)
      return fetch(
        `${BASE}/${empresaId}/ingestar?cuenta_iban=${encodeURIComponent(iban)}`,
        { method: 'POST', body: form }
      ).then(async r => {
        if (!r.ok) {
          const err = await r.json().catch(() => ({}))
          throw new Error((err as { detail?: string }).detail ?? 'Error al ingestar')
        }
        return r.json()
      })
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['movimientos-bancarios', empresaId] })
      qc.invalidateQueries({ queryKey: ['estado-conciliacion', empresaId] })
    },
  })
}

export function useConciliar(empresaId: number) {
  const qc = useQueryClient()
  return useMutation<ResultadoConciliacion, Error>({
    mutationFn: () =>
      fetch(`${BASE}/${empresaId}/conciliar`, { method: 'POST' }).then(r => {
        if (!r.ok) throw new Error('Error al conciliar')
        return r.json()
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['movimientos-bancarios', empresaId] })
      qc.invalidateQueries({ queryKey: ['estado-conciliacion', empresaId] })
    },
  })
}
