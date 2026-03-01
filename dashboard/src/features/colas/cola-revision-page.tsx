import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { CheckCircle, XCircle, ArrowUpCircle, Clock } from 'lucide-react'
import { api } from '@/lib/api-client'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { PageHeader } from '@/components/page-header'
import { EstadoVacio } from '@/components/estado-vacio'

interface ItemCola {
  id: number
  empresa_id: number
  nombre_archivo: string
  estado: string
  trust_level: string
  score_final: number | null
  decision: string
  created_at: string
}

function ScoreBadge({ score }: { score: number | null }) {
  if (score === null) return <Badge variant="outline">Sin score</Badge>
  if (score >= 85) return <Badge>{score.toFixed(0)}%</Badge>
  if (score >= 70) return <Badge variant="secondary">{score.toFixed(0)}%</Badge>
  return <Badge variant="destructive">{score.toFixed(0)}%</Badge>
}

function TrustBadge({ level }: { level: string }) {
  if (level === 'ALTA') return <Badge variant="default">Alta</Badge>
  if (level === 'MEDIA') return <Badge variant="secondary">Media</Badge>
  return <Badge variant="outline">Baja</Badge>
}

export default function ColaRevisionPage() {
  const { id } = useParams<{ id: string }>()
  const empresaId = Number(id)
  const qc = useQueryClient()
  const [pagina, setPagina] = useState(1)

  const clave = ['cola-revision', empresaId, pagina]
  const invalidar = () => qc.invalidateQueries({ queryKey: ['cola-revision', empresaId] })

  const { data, isLoading } = useQuery({
    queryKey: clave,
    queryFn: () =>
      api.get<{ items: ItemCola[]; total: number; pagina: number }>(
        `/api/colas/revision?empresa_id=${empresaId}&pagina=${pagina}`
      ),
    enabled: !isNaN(empresaId),
    refetchInterval: 30_000,
  })

  const aprobar = useMutation({
    mutationFn: (itemId: number) => api.post(`/api/colas/${itemId}/aprobar`, {}),
    onSuccess: invalidar,
  })

  const rechazar = useMutation({
    mutationFn: ({ id: itemId, motivo }: { id: number; motivo: string }) =>
      api.post(`/api/colas/${itemId}/rechazar`, { motivo }),
    onSuccess: invalidar,
  })

  const escalar = useMutation({
    mutationFn: (itemId: number) => api.post(`/api/colas/${itemId}/escalar`, {}),
    onSuccess: invalidar,
  })

  const isPending = aprobar.isPending || rechazar.isPending || escalar.isPending

  if (isLoading) {
    return (
      <div className="p-6 space-y-4">
        <PageHeader titulo="Cola de Revisión" descripcion="Cargando documentos pendientes..." />
        <div className="animate-pulse space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-24 bg-muted rounded-lg" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-4">
      <PageHeader
        titulo="Cola de Revisión"
        descripcion={
          data?.total
            ? `${data.total} documento${data.total !== 1 ? 's' : ''} pendiente${data.total !== 1 ? 's' : ''} de revisión`
            : 'Sin documentos pendientes'
        }
      />

      {!data?.items.length ? (
        <EstadoVacio
          icono={CheckCircle}
          titulo="Cola vacía"
          descripcion="No hay documentos pendientes de revisión"
        />
      ) : (
        <div className="space-y-3">
          {data.items.map((item) => (
            <div
              key={item.id}
              className="border rounded-lg p-4 bg-card shadow-sm space-y-3"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-sm truncate" title={item.nombre_archivo}>
                    {item.nombre_archivo}
                  </p>
                  <p className="text-xs text-muted-foreground mt-0.5 flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {new Date(item.created_at).toLocaleString('es-ES')}
                  </p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <ScoreBadge score={item.score_final} />
                  <TrustBadge level={item.trust_level} />
                </div>
              </div>

              <div className="flex gap-2">
                <Button
                  size="sm"
                  onClick={() => aprobar.mutate(item.id)}
                  disabled={isPending}
                  className="gap-1"
                >
                  <CheckCircle className="w-3.5 h-3.5" />
                  Aprobar
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() =>
                    rechazar.mutate({ id: item.id, motivo: 'Rechazado por gestor' })
                  }
                  disabled={isPending}
                  className="gap-1"
                >
                  <XCircle className="w-3.5 h-3.5" />
                  Rechazar
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => escalar.mutate(item.id)}
                  disabled={isPending}
                  className="gap-1"
                >
                  <ArrowUpCircle className="w-3.5 h-3.5" />
                  Escalar
                </Button>
              </div>
            </div>
          ))}

          {/* Paginación */}
          {data.total > 20 && (
            <div className="flex items-center justify-between pt-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPagina((p) => Math.max(1, p - 1))}
                disabled={pagina === 1}
              >
                Anterior
              </Button>
              <span className="text-sm text-muted-foreground">
                Pág. {pagina} · {data.total} total
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPagina((p) => p + 1)}
                disabled={pagina * 20 >= data.total}
              >
                Siguiente
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
