/**
 * Vista maestro-detalle de movimientos pendientes de conciliación.
 * Columna izquierda: lista de movimientos | Columna derecha: detalle del seleccionado.
 */
import { useState } from 'react'
import { useEmpresaStore } from '@/stores/empresa-store'
import { useMovimientos } from '../api'
import type { MovimientoBancario } from '../api'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Skeleton } from '@/components/ui/skeleton'
import { ArrowDownLeft, ArrowUpRight, MousePointerClick } from 'lucide-react'
import { cn } from '@/lib/utils'
import { PanelConciliacion } from './panel-conciliacion'

function formatImporte(importe: number, signo: 'D' | 'H'): string {
  const valor = importe.toLocaleString('es-ES', { style: 'currency', currency: 'EUR' })
  return signo === 'H' ? `+${valor}` : `-${valor}`
}

// ── Skeleton de carga ──────────────────────────────────────────────────────────

function ListaSkeleton() {
  return (
    <div className="space-y-1 p-2">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="px-3 py-3 space-y-2">
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-3 w-1/2" />
        </div>
      ))}
    </div>
  )
}

// ── Item de la lista (columna izquierda) ──────────────────────────────────────

function MovimientoItem({
  mov,
  seleccionado,
  onClick,
}: {
  mov: MovimientoBancario
  seleccionado: boolean
  onClick: () => void
}) {
  const esAbono = mov.signo === 'H'

  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'w-full text-left px-4 py-3 flex items-start gap-3 transition-colors',
        'hover:bg-muted/60 border-b border-border/50',
        seleccionado && 'bg-primary/8 border-l-2 border-l-primary'
      )}
    >
      <span className={cn(
        'mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full',
        esAbono ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
      )}>
        {esAbono
          ? <ArrowUpRight className="h-3.5 w-3.5" />
          : <ArrowDownLeft className="h-3.5 w-3.5" />}
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium leading-tight">{mov.concepto_propio || '—'}</p>
        <p className="truncate text-xs text-muted-foreground mt-0.5">{mov.nombre_contraparte}</p>
        <p className="text-xs text-muted-foreground">{mov.fecha}</p>
      </div>
      <span className={cn(
        'shrink-0 text-sm font-semibold tabular-nums',
        esAbono ? 'text-green-700' : 'text-red-700'
      )}>
        {formatImporte(mov.importe, mov.signo)}
      </span>
    </button>
  )
}

// ── Componente principal ──────────────────────────────────────────────────────

export function VistaPendientes() {
  const empresaId = useEmpresaStore((s) => s.empresaActiva?.id ?? 0)
  const [selectedId, setSelectedId] = useState<number | null>(null)

  const { data: movimientos = [], isLoading, isError } = useMovimientos(empresaId, 'pendiente')

  const movSeleccionado = movimientos.find((m) => m.id === selectedId) ?? null

  return (
    <div className="flex h-[calc(100vh-14rem)] overflow-hidden rounded-lg border">
      {/* ── Columna izquierda — lista maestro ── */}
      <div className="flex w-[38%] shrink-0 flex-col border-r">
        <div className="border-b px-4 py-2.5">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            {isLoading ? '…' : `${movimientos.length} movimientos`}
          </p>
        </div>

        <ScrollArea className="flex-1">
          {isLoading && <ListaSkeleton />}

          {isError && (
            <p className="p-4 text-sm text-destructive">Error al cargar movimientos.</p>
          )}

          {!isLoading && !isError && movimientos.length === 0 && (
            <p className="p-6 text-center text-sm text-muted-foreground">
              No hay movimientos pendientes.
            </p>
          )}

          {!isLoading && movimientos.map((mov) => (
            <MovimientoItem
              key={mov.id}
              mov={mov}
              seleccionado={mov.id === selectedId}
              onClick={() => setSelectedId(mov.id === selectedId ? null : mov.id)}
            />
          ))}
        </ScrollArea>
      </div>

      {/* ── Columna derecha — detalle ── */}
      <div className="flex flex-1 flex-col overflow-y-auto p-4">
        {movSeleccionado ? (
          <PanelConciliacion mov={movSeleccionado} />
        ) : (
          <div className="flex flex-1 flex-col items-center justify-center gap-2 text-muted-foreground">
            <MousePointerClick className="h-10 w-10 opacity-25" />
            <p className="text-sm font-medium">Selecciona un movimiento</p>
            <p className="text-xs">para ver sus detalles y sugerencias</p>
          </div>
        )}
      </div>
    </div>
  )
}
