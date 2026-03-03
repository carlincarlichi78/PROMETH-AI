// dashboard/src/features/pipeline/components/LiveEventFeed.tsx
import { cn } from '@/lib/utils'
import type { EventoWS } from '../hooks/usePipelineWebSocket'

interface Props {
  eventos: EventoWS[]
  empresaSeleccionada?: number
}

const ETIQUETA_EVENTO: Record<string, { label: string; icono: string; color: string }> = {
  pipeline_progreso:   { label: 'Procesando', icono: '⟳', color: 'text-amber-400' },
  documento_procesado: { label: 'Completado', icono: '✓', color: 'text-emerald-400' },
  cuarentena_nuevo:    { label: 'Cuarentena', icono: '⚠', color: 'text-orange-400' },
  cuarentena_resuelta: { label: 'Resuelta',   icono: '↩', color: 'text-blue-400' },
  watcher_nuevo_pdf:   { label: 'Nuevo PDF',  icono: '📄', color: 'text-slate-300' },
  error:               { label: 'Error',      icono: '✕', color: 'text-red-400' },
}

function formatHora(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch {
    return ''
  }
}

export function LiveEventFeed({ eventos, empresaSeleccionada }: Props) {
  const eventosFiltrados = empresaSeleccionada
    ? eventos.filter(e => e.datos.empresa_id === empresaSeleccionada)
    : eventos

  return (
    <div className="border-t border-white/5 bg-black/10 backdrop-blur-sm">
      {/* Header */}
      <div className="flex items-center gap-2 px-6 py-2 border-b border-white/5">
        <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
        <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
          Actividad en tiempo real
        </span>
        {eventosFiltrados.length > 0 && (
          <span className="ml-auto text-[10px] text-muted-foreground">
            {eventosFiltrados.length} evento{eventosFiltrados.length !== 1 ? 's' : ''}
          </span>
        )}
      </div>

      {/* Feed */}
      <div className="divide-y divide-white/[0.04] max-h-[200px] overflow-y-auto">
        {eventosFiltrados.length === 0 ? (
          <div className="px-6 py-4 text-center text-sm text-muted-foreground animate-in fade-in duration-300">
            Esperando eventos del pipeline...
          </div>
        ) : (
          eventosFiltrados.map(ev => {
            const meta = ETIQUETA_EVENTO[ev.evento] ?? { label: ev.evento, icono: '●', color: 'text-slate-400' }
            const nombre = ev.datos.nombre_archivo?.replace(/^[a-f0-9]+_/, '') ?? `Doc #${ev.datos.documento_id ?? '?'}`
            const motivo = ev.datos.motivo ? ` — ${ev.datos.motivo}` : ''
            const fase = ev.datos.fase_actual ? ` → ${ev.datos.fase_actual}` : ''

            return (
              <div
                key={ev.id}
                className="flex items-center gap-3 px-6 py-2 animate-in slide-in-from-top-2 fade-in duration-200"
              >
                {/* Hora */}
                <span className="text-[10px] text-muted-foreground tabular-nums w-20 flex-shrink-0">
                  {formatHora(ev.timestamp)}
                </span>

                {/* Icono + tipo */}
                <span className={cn('text-sm w-4 flex-shrink-0', meta.color)}>
                  {meta.icono}
                </span>

                {/* Tipo doc */}
                {ev.datos.tipo_doc && (
                  <span className="text-[10px] font-mono bg-white/5 px-1.5 py-0.5 rounded text-slate-300 flex-shrink-0">
                    {ev.datos.tipo_doc}
                  </span>
                )}

                {/* Nombre archivo */}
                <span className="text-xs text-foreground truncate flex-1">
                  {nombre}
                </span>

                {/* Estado */}
                <span className={cn('text-[10px] flex-shrink-0', meta.color)}>
                  {meta.label}{fase}{motivo}
                </span>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
