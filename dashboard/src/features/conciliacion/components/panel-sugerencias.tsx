/**
 * Panel global de sugerencias pendientes de revisión.
 * Usa useSugerencias(empresaId, null) para obtener todas las sugerencias activas.
 * Agrupa en tarjetas con acciones de confirmar / rechazar.
 */
import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Loader2, Zap, Search, X } from 'lucide-react'
import { MatchCard } from './match-card'
import { useSugerencias, useConfirmarMatch, useRechazarMatch, conciliacionApi } from '../api'

interface PanelSugerenciasProps {
  empresaId: number
}

export function PanelSugerencias({ empresaId }: PanelSugerenciasProps) {
  const qc = useQueryClient()
  const [filtroDoc, setFiltroDoc] = useState('')

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

  const q = filtroDoc.toLowerCase()
  const sugerenciasFiltradas = q
    ? sugerencias.filter(s =>
        s.documento?.nif_proveedor?.toLowerCase().includes(q) ||
        s.documento?.numero_factura?.toLowerCase().includes(q) ||
        s.movimiento.concepto_propio?.toLowerCase().includes(q) ||
        s.movimiento.nombre_contraparte?.toLowerCase().includes(q)
      )
    : sugerencias

  const altaConfianza = sugerenciasFiltradas.filter(s => s.score >= 0.95)

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
      {/* Filtro de documentos */}
      <div className="flex items-center gap-2">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
          <Input
            placeholder="Filtrar por NIF, factura o concepto…"
            value={filtroDoc}
            onChange={(e) => setFiltroDoc(e.target.value)}
            className="pl-8 h-8 text-sm"
          />
        </div>
        {filtroDoc && (
          <Button variant="ghost" size="sm" className="h-8 px-2 text-muted-foreground" onClick={() => setFiltroDoc('')}>
            <X className="h-3.5 w-3.5 mr-1" />
            Limpiar
          </Button>
        )}
        <span className="text-xs text-muted-foreground ml-auto">
          {sugerenciasFiltradas.length} de {sugerencias.length}
        </span>
      </div>

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

      {(confirmar.isError || rechazar.isError) && (
        <Alert variant="destructive">
          <AlertDescription>
            {confirmar.error?.message ?? rechazar.error?.message}
          </AlertDescription>
        </Alert>
      )}

      {sugerenciasFiltradas.length === 0 && filtroDoc ? (
        <p className="text-center py-8 text-sm text-muted-foreground">
          Sin resultados para «{filtroDoc}».
        </p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {sugerenciasFiltradas.map(s => (
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
      )}
    </div>
  )
}
