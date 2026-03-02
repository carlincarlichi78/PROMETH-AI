// mobile/hooks/useSemaforo.ts
import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/hooks/useApi'

interface Alerta {
  tipo: string
  mensaje: string
  urgente: boolean
}

export interface Semaforo {
  color: 'verde' | 'amarillo' | 'rojo'
  alertas: Alerta[]
  resultado_acumulado: number
}

export function useSemaforo(empresaId: number | undefined) {
  return useQuery({
    queryKey: ['semaforo', empresaId],
    queryFn: () => apiFetch<Semaforo>(`/api/portal/${empresaId}/semaforo`),
    enabled: !!empresaId,
    refetchInterval: 5 * 60 * 1000,
  })
}
