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

const STATUS_VACIO: FaseStatus = {
  inbox: 0, procesando: 0, cuarentena: 0, error: 0, done_hoy: 0,
  por_empresa: {}, actualizado_en: '',
}

export function usePipelineSyncStatus(empresaId?: number) {
  const { token } = useAuth()

  const { data, isLoading } = useQuery<FaseStatus>({
    queryKey: ['pipeline-status', empresaId],
    queryFn: async () => {
      const base = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
      const url = empresaId
        ? `${base}/api/dashboard/pipeline-status?empresa_id=${empresaId}`
        : `${base}/api/dashboard/pipeline-status`
      const r = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!r.ok) return STATUS_VACIO
      return r.json()
    },
    refetchInterval: 30_000,  // cada 30s
    enabled: !!token,
    placeholderData: STATUS_VACIO,
  })

  return { status: data ?? STATUS_VACIO, isLoading }
}
