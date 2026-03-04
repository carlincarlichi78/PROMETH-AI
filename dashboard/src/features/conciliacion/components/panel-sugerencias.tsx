/**
 * Panel global de sugerencias pendientes de revisión.
 * Usa useSugerencias(empresaId, null) para obtener todas las sugerencias activas.
 * Agrupa en tarjetas con acciones de confirmar / rechazar.
 */
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Loader2, Zap } from 'lucide-react'
import { MatchCard } from './match-card'
import { useSugerencias, useConfirmarMatch, useRechazarMatch, conciliacionApi } from '../api'

interface PanelSugerenciasProps {
  empresaId: number
}

export function PanelSugerencias({ empresaId }: PanelSugerenciasProps) {
  const qc = useQueryClient()

  // Todas las sugerencias activas de la empresa (sin filtro de movimiento)
  const { data: sugerencias = [], isLoading } = useSugerencias(empresaId, null)

  // Mutaciones atómicas (misma firma que en PanelConciliacion)
  const confirmar = useConfirmarMatch(empresaId)
  const rechazar = useRechazarMatch(empresaId)

  // Confirmación en bloque para sugerencias de alta confianza
  const bulk = useMutation({
    mutationFn: () => conciliacionApi.confirmarBulk(empresaId, 0.95),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['sugerencias', empresaId] })
      qc.invalidateQueries({ queryKey: ['movimientos-bancarios', empresaId] })
      qc.invalidateQueries({ queryKey: ['estado-conciliacion', empresaId] })
    },
  })

  const altaConfianza = sugerencias.filter(s => s.score >= 0.95)

  if (isLoading) {
    return (
      <div className="flex justify-center p-8">
        <Loader2 className="animate-spin" />
      </div>
    )
  }

  if (sugerencias.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        No hay sugerencias pendientes de revisión.
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {altaConfianza.length > 0 && (
        <Alert>
          <AlertDescription className="flex items-center justify-between">
            <span>
              {altaConfianza.length} sugerencias con confianza ≥95%. Puedes confirmarlas en bloque.
            </span>
            <Button
              size="sm"
              variant="default"
              disabled={bulk.isPending}
              onClick={() => bulk.mutate()}
              className="ml-4"
            >
              {bulk.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin mr-1" />
              ) : (
                <Zap className="w-4 h-4 mr-1" />
              )}
              Confirmar bulk
            </Button>
          </AlertDescription>
        </Alert>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {sugerencias.map(s => (
          <MatchCard
            key={s.id}
            sugerencia={s}
            onConfirmar={(movId, sugId) =>
              confirmar.mutate({ movimiento_id: movId, sugerencia_id: sugId })
            }
            onRechazar={(sugId) => rechazar.mutate({ sugerencia_id: sugId })}
            cargando={confirmar.isPending || rechazar.isPending}
          />
        ))}
      </div>
    </div>
  )
}
