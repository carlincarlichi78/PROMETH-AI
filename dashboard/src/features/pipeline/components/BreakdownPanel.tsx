// dashboard/src/features/pipeline/components/BreakdownPanel.tsx
import { cn } from '@/lib/utils'
import type { BreakdownStatus } from '../hooks/usePipelineSyncStatus'
import type { EventoWS } from '../hooks/usePipelineWebSocket'

interface Props {
  breakdown: BreakdownStatus
  eventos: EventoWS[]
  empresaSeleccionada?: number
}

const COLOR_TIPO: Record<string, { bg: string; text: string }> = {
  FC:  { bg: 'bg-emerald-500',  text: 'text-emerald-300' },
  FV:  { bg: 'bg-blue-500',     text: 'text-blue-300' },
  NC:  { bg: 'bg-amber-500',    text: 'text-amber-300' },
  SUM: { bg: 'bg-purple-500',   text: 'text-purple-300' },
  IMP: { bg: 'bg-teal-500',     text: 'text-teal-300' },
  NOM: { bg: 'bg-pink-500',     text: 'text-pink-300' },
  BAN: { bg: 'bg-sky-500',      text: 'text-sky-300' },
  '?': { bg: 'bg-slate-500',    text: 'text-slate-300' },
}

const ICONO_EVENTO: Record<string, string> = {
  pipeline_progreso:   '⟳',
  documento_procesado: '✓',
  cuarentena_nuevo:    '⚠',
  cuarentena_resuelta: '↩',
  watcher_nuevo_pdf:   '📄',
  error:               '✕',
}

const COLOR_EVENTO: Record<string, string> = {
  pipeline_progreso:   'text-amber-400',
  documento_procesado: 'text-emerald-400',
  cuarentena_nuevo:    'text-orange-400',
  cuarentena_resuelta: 'text-blue-400',
  watcher_nuevo_pdf:   'text-slate-300',
  error:               'text-red-400',
}

function formatHora(iso: string): string {
  try { return new Date(iso).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) }
  catch { return '' }
}

export function BreakdownPanel({ breakdown, eventos, empresaSeleccionada }: Props) {
  const tipoDocs = Object.entries(breakdown.tipo_doc).slice(0, 8)
  const maxDocs = tipoDocs.length > 0 ? Math.max(...tipoDocs.map(([, n]) => n)) : 1

  const eventosFiltrados = empresaSeleccionada
    ? eventos.filter(e => e.datos.empresa_id === empresaSeleccionada)
    : eventos

  return (
    <div className="flex flex-col gap-4 h-full overflow-hidden">
      {/* Breakdown por tipo_doc */}
      <div>
        <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/60 mb-2 px-1">
          Tipos procesados hoy
        </p>
        {tipoDocs.length === 0 ? (
          <p className="text-xs text-muted-foreground/50 px-1">Sin documentos procesados hoy</p>
        ) : (
          <div className="flex flex-col gap-1.5">
            {tipoDocs.map(([tipo, n]) => {
              const pct = Math.round((n / maxDocs) * 100)
              const c = COLOR_TIPO[tipo] ?? COLOR_TIPO['?'] ?? { bg: 'bg-slate-500', text: 'text-slate-300' }
              return (
                <div key={tipo} className="flex items-center gap-2">
                  <span className={cn('text-[10px] font-mono font-semibold w-8 flex-shrink-0 text-right', c.text)}>
                    {tipo}
                  </span>
                  <div className="flex-1 h-4 bg-white/5 rounded overflow-hidden">
                    <div
                      className={cn('h-full rounded transition-all duration-700 opacity-70', c.bg)}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className="text-xs tabular-nums text-muted-foreground w-6 text-right flex-shrink-0">
                    {n}
                  </span>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Divisor */}
      <div className="border-t border-white/5" />

      {/* Feed de actividad reciente */}
      <div className="flex-1 overflow-hidden flex flex-col">
        <div className="flex items-center gap-2 mb-2 px-1">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/60">
            Actividad reciente
          </p>
        </div>
        <div className="flex-1 overflow-y-auto space-y-0 divide-y divide-white/[0.04]">
          {eventosFiltrados.length === 0 ? (
            <p className="text-xs text-muted-foreground/50 px-1 py-3 text-center">
              Esperando eventos...
            </p>
          ) : (
            eventosFiltrados.map(ev => {
              const icono = ICONO_EVENTO[ev.evento] ?? '●'
              const colorEvento = COLOR_EVENTO[ev.evento] ?? 'text-slate-400'
              const fuente = (ev.datos as { fuente?: string }).fuente
              const iconoFuente = fuente === 'correo' ? '📧' : fuente === 'watcher' ? '📁' : fuente === 'manual' ? '💻' : null
              const nombre = ev.datos.nombre_archivo?.replace(/^[a-f0-9]{8,}_/, '') ?? `Doc #${ev.datos.documento_id ?? '?'}`

              return (
                <div
                  key={ev.id}
                  className="flex items-start gap-2 py-1.5 px-1 animate-in slide-in-from-top-1 fade-in duration-200"
                >
                  <span className="text-[10px] text-muted-foreground/50 tabular-nums w-16 flex-shrink-0 pt-px">
                    {formatHora(ev.timestamp)}
                  </span>
                  <span className={cn('flex-shrink-0 text-xs w-4', colorEvento)}>{icono}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1 flex-wrap">
                      {ev.datos.tipo_doc && (
                        <span className="text-[9px] font-mono bg-white/5 px-1 rounded text-slate-400">
                          {ev.datos.tipo_doc}
                        </span>
                      )}
                      {iconoFuente && <span className="text-[10px]">{iconoFuente}</span>}
                    </div>
                    <p className="text-[10px] text-foreground/70 truncate mt-0.5">{nombre}</p>
                    {ev.datos.motivo && (
                      <p className="text-[9px] text-orange-400/70 truncate">{ev.datos.motivo}</p>
                    )}
                  </div>
                </div>
              )
            })
          )}
        </div>
      </div>
    </div>
  )
}
