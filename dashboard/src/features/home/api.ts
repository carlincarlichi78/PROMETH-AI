// src/features/home/api.ts
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api-client'

export interface ResumenEmpresa {
  empresa_id: number
  bandeja: {
    pendientes: number
    errores_ocr: number
    cuarentena: number
    ultimo_procesado: string | null
  }
  fiscal: {
    proximo_modelo: string | null
    dias_restantes: number | null
    fecha_limite: string | null
    importe_estimado: number | null
  }
  contabilidad: {
    errores_asientos: number
    ultimo_asiento: string | null
  }
  facturacion: {
    ventas_ytd: number
    facturas_vencidas: number
    pendientes_cobro: number
  }
  scoring: number | null
  alertas_ia: string[]
  ventas_6m: number[]
}

export function useResumenEmpresa(empresaId: number) {
  return useQuery<ResumenEmpresa>({
    queryKey: ['resumen-empresa', empresaId],
    queryFn: () => api.get<ResumenEmpresa>(`/api/empresas/${empresaId}/resumen`),
    staleTime: 5 * 60 * 1000,
    retry: false,
  })
}

export interface EstadisticasGlobales {
  total_clientes: number
  docs_pendientes_total: number
  alertas_urgentes: number
  proximo_deadline: { modelo: string; dias: number; fecha: string } | null
  volumen_gestionado: number
}

export function useEstadisticasGlobales() {
  return useQuery<EstadisticasGlobales>({
    queryKey: ['estadisticas-globales'],
    queryFn: () => api.get<EstadisticasGlobales>('/api/empresas/estadisticas-globales'),
    staleTime: 5 * 60 * 1000,
    retry: false,
  })
}
