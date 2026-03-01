import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api-client'

const ICONOS: Record<string, string> = {
  RECIBIDO: '📥',
  OCR_OK: '🔍',
  VALIDADO: '✓',
  REGISTRADO: '📋',
  PUBLICADO: '✅',
  COLA_REVISION: '⏳',
  APROBADO: '✅',
  RECHAZADO: '❌',
  ESCALADO: '⬆️',
  PROCESANDO: '🔄',
}

interface EstadoTracking {
  estado: string
  timestamp: string
  actor: string
}

interface TrackingResponse {
  documento_id: number
  nombre_archivo: string
  estados: EstadoTracking[]
}

export function TrackingDocumento({
  documentoId,
}: {
  documentoId: number
}) {
  const { data, isLoading } = useQuery({
    queryKey: ['tracking', documentoId],
    queryFn: () =>
      api.get<TrackingResponse>(`/api/colas/documentos/${documentoId}/tracking`),
    enabled: documentoId > 0,
  })

  if (isLoading) {
    return (
      <div className="space-y-2 animate-pulse">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-8 bg-muted rounded" />
        ))}
      </div>
    )
  }

  if (!data?.estados.length) {
    return <p className="text-sm text-muted-foreground">Sin historial de estados</p>
  }

  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground font-medium uppercase tracking-wide mb-3">
        Historial
      </p>
      {data.estados.map((e, i) => (
        <div key={i} className="flex items-center gap-3 text-sm">
          <span className="text-base leading-none w-5 text-center">
            {ICONOS[e.estado] ?? '•'}
          </span>
          <span className="font-medium flex-1">{e.estado.replace(/_/g, ' ')}</span>
          <span className="text-muted-foreground text-xs">
            {new Date(e.timestamp).toLocaleString('es-ES')}
          </span>
        </div>
      ))}
    </div>
  )
}
