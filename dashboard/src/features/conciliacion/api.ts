import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api-client'

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
  conciliados_auto?: number
  sugeridos?: number
  revision?: number
  pendientes?: number
}

export interface DetalleCuenta {
  iban: string
  alias: string
  creada: boolean
  movimientos_totales: number
  movimientos_nuevos: number
  movimientos_duplicados: number
  ya_procesado: boolean
}

export interface ResultadoIngesta {
  movimientos_totales: number
  movimientos_nuevos: number
  movimientos_duplicados: number
  ya_procesado: boolean
  // Campos adicionales para C43 multi-cuenta
  cuentas_procesadas?: number
  cuentas_creadas?: number
  detalle?: DetalleCuenta[]
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

// ── Helpers internos (usan api-client con Authorization automático) ───────────

function fetchJson<T>(url: string): Promise<T> {
  return api.get<T>(url)
}

function postJson<T>(url: string, cuerpo: unknown): Promise<T> {
  return api.post<T>(url, cuerpo)
}

function deleteReq<T>(url: string): Promise<T> {
  return api.delete<T>(url)
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
    queryFn: () => api.get<CuentaBancaria[]>(`${BASE}/${empresaId}/cuentas`),
    enabled: empresaId > 0,
  })
}

export function useMovimientos(empresaId: number, estado?: string) {
  const params = estado ? `?estado=${estado}` : ''
  return useQuery<MovimientoBancario[]>({
    queryKey: ['movimientos-bancarios', empresaId, estado],
    queryFn: () => api.get<MovimientoBancario[]>(`${BASE}/${empresaId}/movimientos${params}`),
    enabled: empresaId > 0,
  })
}

export function useEstadoConciliacion(empresaId: number) {
  return useQuery<EstadoConciliacion>({
    queryKey: ['estado-conciliacion', empresaId],
    queryFn: () => api.get<EstadoConciliacion>(`${BASE}/${empresaId}/estado_conciliacion`),
    enabled: empresaId > 0,
  })
}

export function useIngestarExtracto(empresaId: number) {
  const qc = useQueryClient()
  return useMutation<ResultadoIngesta, Error, { archivo: File; iban?: string }>({
    mutationFn: ({ archivo, iban }) => {
      const form = new FormData()
      form.append('archivo', archivo)
      const ibanParam = iban ? `?cuenta_iban=${encodeURIComponent(iban)}` : ''
      return api.postForm<ResultadoIngesta>(
        `${BASE}/${empresaId}/ingestar${ibanParam}`,
        form
      )
    },
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ['movimientos-bancarios', empresaId] })
      qc.invalidateQueries({ queryKey: ['estado-conciliacion', empresaId] })
      // Si se crearon cuentas nuevas, refrescar la lista de cuentas
      if (data.cuentas_creadas && data.cuentas_creadas > 0) {
        qc.invalidateQueries({ queryKey: ['cuentas-bancarias', empresaId] })
      }
    },
  })
}

export function useConciliar(empresaId: number) {
  const qc = useQueryClient()
  return useMutation<ResultadoConciliacion, Error>({
    mutationFn: () => api.post<ResultadoConciliacion>(`${BASE}/${empresaId}/conciliar`, {}),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['movimientos-bancarios', empresaId] })
      qc.invalidateQueries({ queryKey: ['estado-conciliacion', empresaId] })
    },
  })
}

/**
 * Sugerencias de conciliación.
 * - movimientoId = número → filtra por ese movimiento (pestaña Pendientes)
 * - movimientoId = null   → devuelve todas las sugerencias activas (pestaña Sugerencias global)
 */
export function useSugerencias(empresaId: number, movimientoId: number | null) {
  const params = movimientoId != null ? `?movimiento_id=${movimientoId}` : ''
  return useQuery<SugerenciaOut[]>({
    queryKey: ['sugerencias', empresaId, movimientoId],
    queryFn: () => fetchJson<SugerenciaOut[]>(`${BASE}/${empresaId}/sugerencias${params}`),
    enabled: empresaId > 0,
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
