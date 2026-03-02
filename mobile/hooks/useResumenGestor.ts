// mobile/hooks/useResumenGestor.ts
import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/hooks/useApi'

export interface EmpresaResumen {
  id: number
  nombre: string
  cif: string
  estado_onboarding: string
  semaforo: 'verde' | 'amarillo' | 'rojo'
  alertas_count: number
  alerta_texto: string | null
}

export function useResumenGestor() {
  return useQuery({
    queryKey: ['gestor-resumen-v2'],
    queryFn: () => apiFetch<{ empresas: EmpresaResumen[]; total: number }>('/api/gestor/resumen'),
    refetchInterval: 3 * 60 * 1000,
  })
}
