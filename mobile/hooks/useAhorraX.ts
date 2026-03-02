// mobile/hooks/useAhorraX.ts
import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/hooks/useApi'

export interface AhorraX {
  trimestre: string
  iva_estimado_trimestre: number
  irpf_estimado_trimestre: number
  total_estimado_trimestre: number
  aparta_mes: number
  meses_restantes: number
  vencimiento_trimestre: string
  nota: string
}

export function useAhorraX(empresaId: number | undefined) {
  return useQuery({
    queryKey: ['ahorra-mes', empresaId],
    queryFn: () => apiFetch<AhorraX>(`/api/portal/${empresaId}/ahorra-mes`),
    enabled: !!empresaId,
  })
}
