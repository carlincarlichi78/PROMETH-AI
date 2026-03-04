import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

const BASE = '/api/bancario'

// ── Tipos existentes ──────────────────────────────────────────────────────────

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
  estado_conciliacion: 'pendiente' | 'sugerido' | 'revision' | 'conciliado' | 'parcial' | 'manual'
  asiento_id: number | null
  capa_match?: number
  score_confianza?: number
  documento_id?: number
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

// ── Tipos nuevos (conciliacion inteligente) ───────────────────────────────────

export interface DocumentoResumen {
  id: number
  // Campos del schema Pydantic DocumentoResumen (backend)
  tipo?: string | null
  fecha?: string | null
  nif_proveedor?: string
  numero_factura?: string
  importe_total?: number
  // Campos legacy usados por match-card.tsx
  nombre_archivo?: string
  tipo_doc?: string
  fecha_documento?: string
}

export interface MovimientoResumen {
  id: number
  fecha: string
  importe: number
  concepto_propio: string
  nombre_contraparte: string
}

/** Refleja exactamente el schema Pydantic SugerenciaOut del endpoint /sugerencias */
export interface SugerenciaOut {
  id: number
  movimiento_id: number
  documento_id: number
  score: number
  capa_origen: number
  movimiento: MovimientoResumen
  documento: DocumentoResumen | null
}

export interface SugerenciaMatch {
  id: number
  movimiento_id: number
  documento_id: number
  score: number
  capa_origen: number
  movimiento: MovimientoBancario
  documento?: DocumentoResumen
}

export interface SaldoDescuadre {
  cuenta_id: number
  iban: string
  alias: string
  saldo_bancario: number
  saldo_contable: number
  diferencia: number
  alerta: boolean
  mensaje_alerta?: string
}

export interface PatronConciliacion {
  id: number
  patron_texto: string
  patron_limpio?: string
  nif_proveedor?: string
  cuenta_contable?: string
  rango_importe_aprox: string
  frecuencia_exito: number
  ultima_confirmacion?: string
}

export interface ResultadoBulk {
  confirmados: number
  total_revisados: number
}

// ── Helpers internos ──────────────────────────────────────────────────────────

async function fetchJson<T>(url: string, opciones?: RequestInit): Promise<T> {
  const resp = await fetch(url, opciones)
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}))
    throw new Error((err as { detail?: string }).detail ?? `Error HTTP ${resp.status}`)
  }
  return resp.json() as Promise<T>
}

function postJson<T>(url: string, cuerpo: unknown): Promise<T> {
  return fetchJson<T>(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(cuerpo),
  })
}

function deleteReq<T>(url: string): Promise<T> {
  return fetchJson<T>(url, { method: 'DELETE' })
}

// ── API funcional (para componentes sin hooks) ────────────────────────────────

export const conciliacionApi = {
  listarMovimientos: (empresaId: number, estado?: string) =>
    fetchJson<MovimientoBancario[]>(
      `${BASE}/${empresaId}/movimientos${estado ? `?estado=${estado}` : ''}`
    ),

  listarSugerencias: (empresaId: number) =>
    fetchJson<SugerenciaMatch[]>(`${BASE}/${empresaId}/sugerencias`),

  confirmarMatch: (empresaId: number, movimientoId: number, documentoId: number) =>
    postJson<{ ok: boolean }>(`${BASE}/${empresaId}/confirmar-match`, {
      movimiento_id: movimientoId,
      documento_id: documentoId,
    }),

  rechazarMatch: (empresaId: number, movimientoId: number, documentoId: number) =>
    postJson<{ ok: boolean }>(`${BASE}/${empresaId}/rechazar-match`, {
      movimiento_id: movimientoId,
      documento_id: documentoId,
    }),

  confirmarBulk: (empresaId: number, scoreMinimo: number = 0.95) =>
    postJson<ResultadoBulk>(`${BASE}/${empresaId}/confirmar-bulk`, {
      score_minimo: scoreMinimo,
    }),

  saldoDescuadre: (empresaId: number) =>
    fetchJson<SaldoDescuadre[]>(`${BASE}/${empresaId}/saldo-descuadre`),

  listarPatrones: (empresaId: number) =>
    fetchJson<PatronConciliacion[]>(`${BASE}/${empresaId}/patrones`),

  eliminarPatron: (empresaId: number, patronId: number) =>
    deleteReq<{ ok: boolean }>(`${BASE}/${empresaId}/patrones/${patronId}`),
}

// ── Hooks existentes (sin cambios de interfaz) ────────────────────────────────

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

/** Sugerencias filtradas por movimiento_id. Solo activa la query cuando movimientoId no es null. */
export function useSugerencias(empresaId: number, movimientoId: number | null) {
  const params = movimientoId != null ? `?movimiento_id=${movimientoId}` : ''
  return useQuery<SugerenciaOut[]>({
    queryKey: ['sugerencias', empresaId, movimientoId],
    queryFn: () => fetchJson<SugerenciaOut[]>(`${BASE}/${empresaId}/sugerencias${params}`),
    enabled: empresaId > 0 && movimientoId != null,
  })
}

export function useConfirmarMatch(empresaId: number) {
  const qc = useQueryClient()
  return useMutation<{ ok: boolean }, Error, { movimiento_id: number; sugerencia_id: number }>({
    mutationFn: (body) => postJson(`${BASE}/${empresaId}/confirmar-match`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['sugerencias', empresaId] })
      qc.invalidateQueries({ queryKey: ['movimientos-bancarios', empresaId] })
      qc.invalidateQueries({ queryKey: ['estado-conciliacion', empresaId] })
    },
  })
}

export function useRechazarMatch(empresaId: number) {
  const qc = useQueryClient()
  return useMutation<{ ok: boolean }, Error, { sugerencia_id: number }>({
    mutationFn: (body) => postJson(`${BASE}/${empresaId}/rechazar-match`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['sugerencias', empresaId] })
      qc.invalidateQueries({ queryKey: ['movimientos-bancarios', empresaId] })
      qc.invalidateQueries({ queryKey: ['estado-conciliacion', empresaId] })
    },
  })
}
