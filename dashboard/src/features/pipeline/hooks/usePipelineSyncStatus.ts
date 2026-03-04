// dashboard/src/features/pipeline/hooks/usePipelineSyncStatus.ts
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '@/context/AuthContext'

export interface FaseStatus {
  inbox: number
  procesando: number
  cuarentena: number
  error: number
  done_hoy: number
  por_empresa: Record<number, {
    inbox: number
    procesando: number
    cuarentena: number
    error: number
    done_hoy: number
  }>
  actualizado_en: string
}

export interface BreakdownStatus {
  tipo_doc: Record<string, number>        // { FC: 12, FV: 8, SUM: 4 }
  por_empresa: Array<{ empresa_id: number; nombre: string; total: number }>
  fuentes: { correo: number; manual: number; watcher: number }
  actualizado_en: string
}

const STATUS_VACIO: FaseStatus = {
  inbox: 0, procesando: 0, cuarentena: 0, error: 0, done_hoy: 0,
  por_empresa: {}, actualizado_en: '',
}

const BREAKDOWN_VACIO: BreakdownStatus = {
  tipo_doc: {}, por_empresa: [], fuentes: { correo: 0, manual: 0, watcher: 0 }, actualizado_en: '',
}

export function usePipelineSyncStatus(empresaId?: number) {
  const { token } = useAuth()

  const { data, isLoading } = useQuery<FaseStatus>({
    queryKey: ['pipeline-status', empresaId],
    queryFn: async () => {
      const url = empresaId
        ? `/api/dashboard/pipeline-status?empresa_id=${empresaId}`
        : `/api/dashboard/pipeline-status`
      const r = await fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      if (!r.ok) return STATUS_VACIO
      return r.json()
    },
    refetchInterval: 30_000,
    enabled: !!token,
    placeholderData: STATUS_VACIO,
  })

  const { data: breakdown } = useQuery<BreakdownStatus>({
    queryKey: ['pipeline-breakdown', empresaId],
    queryFn: async () => {
      const url = empresaId
        ? `/api/dashboard/pipeline-breakdown?empresa_id=${empresaId}`
        : `/api/dashboard/pipeline-breakdown`
      const r = await fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      if (!r.ok) return BREAKDOWN_VACIO
      return r.json()
    },
    refetchInterval: 60_000,
    enabled: !!token,
    placeholderData: BREAKDOWN_VACIO,
  })

  return { status: data ?? STATUS_VACIO, breakdown: breakdown ?? BREAKDOWN_VACIO, isLoading }
}
