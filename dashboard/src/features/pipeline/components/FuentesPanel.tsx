// dashboard/src/features/pipeline/components/FuentesPanel.tsx
import { cn } from '@/lib/utils'
import type { BreakdownStatus } from '../hooks/usePipelineSyncStatus'

interface Props {
  breakdown: BreakdownStatus
  contadores_ws: { correo: number; manual: number; watcher: number }
  empresaSeleccionada?: number
  onSeleccionar: (id: number | undefined) => void
}

const FUENTES = [
  { key: 'correo',  icono: '📧', label: 'Correo IMAP',    color: 'text-violet-400',  border: 'border-violet-500/30', bg: 'bg-violet-500/5' },
  { key: 'watcher', icono: '📁', label: 'Watcher local',  color: 'text-sky-400',     border: 'border-sky-500/30',    bg: 'bg-sky-500/5' },
  { key: 'manual',  icono: '💻', label: 'Subida manual',  color: 'text-amber-400',   border: 'border-amber-500/30',  bg: 'bg-amber-500/5' },
] as const

function abreviarNombre(nombre: string): string {
  // "GERARDO GONZALEZ CALLEJON" → "Gerardo G."
  const partes = nombre.split(' ')
  const primero = partes[0] ?? ''
  const segundo = partes[1]
  if (partes.length === 1) return nombre
  return primero.charAt(0).toUpperCase() + primero.slice(1).toLowerCase() +
    (segundo ? ' ' + segundo.charAt(0).toUpperCase() + '.' : '')
}

export function FuentesPanel({ breakdown, contadores_ws, empresaSeleccionada, onSeleccionar }: Props) {
  const fuentesHoy = breakdown.fuentes
  const topEmpresas = breakdown.por_empresa.slice(0, 6)
  const totalHoy = breakdown.por_empresa.reduce((s, e) => s + e.total, 0)

  return (
    <div className="flex flex-col gap-4 h-full">
      {/* Fuentes de entrada */}
      <div>
        <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/60 mb-2 px-1">
          Fuentes hoy
        </p>
        <div className="flex flex-col gap-1.5">
          {FUENTES.map(f => {
            const totalHoyFuente = fuentesHoy[f.key] ?? 0
            const wsHoy = contadores_ws[f.key] ?? 0
            const activo = wsHoy > 0 || totalHoyFuente > 0
            return (
              <div
                key={f.key}
                className={cn(
                  'flex items-center gap-2.5 rounded-lg px-3 py-2 border transition-all',
                  f.bg, f.border,
                  activo ? 'opacity-100' : 'opacity-50',
                )}
              >
                <span className="text-base">{f.icono}</span>
                <div className="flex-1 min-w-0">
                  <p className={cn('text-xs font-medium truncate', f.color)}>{f.label}</p>
                  <p className="text-[10px] text-muted-foreground">
                    {totalHoyFuente > 0 ? `${totalHoyFuente} docs hoy` : 'sin actividad hoy'}
                  </p>
                </div>
                <div className="flex flex-col items-end gap-0.5">
                  <span className={cn('text-sm font-bold tabular-nums', f.color)}>
                    {totalHoyFuente}
                  </span>
                  {wsHoy > 0 && (
                    <span className="text-[9px] text-emerald-400 animate-pulse">+{wsHoy} live</span>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Divisor */}
      <div className="border-t border-white/5" />

      {/* Ranking empresas */}
      <div className="flex-1">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/60 mb-2 px-1">
          Empresas — {totalHoy} docs hoy
        </p>
        {topEmpresas.length === 0 ? (
          <p className="text-xs text-muted-foreground/50 px-1">Sin actividad registrada hoy</p>
        ) : (
          <div className="flex flex-col gap-1">
            {topEmpresas.map((emp, i) => {
              const pct = totalHoy > 0 ? Math.round((emp.total / totalHoy) * 100) : 0
              const seleccionada = empresaSeleccionada === emp.empresa_id
              return (
                <button
                  key={emp.empresa_id}
                  type="button"
                  onClick={() => onSeleccionar(seleccionada ? undefined : emp.empresa_id)}
                  className={cn(
                    'flex items-center gap-2 rounded-lg px-2 py-1.5 text-left transition-all',
                    'hover:bg-white/5 border',
                    seleccionada
                      ? 'border-amber-500/40 bg-amber-500/10'
                      : 'border-transparent',
                  )}
                >
                  <span className="text-[10px] font-mono text-muted-foreground/50 w-4 flex-shrink-0">
                    {i + 1}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-foreground truncate">{abreviarNombre(emp.nombre)}</p>
                    <div className="mt-0.5 h-1 rounded-full bg-white/5 overflow-hidden">
                      <div
                        className="h-full rounded-full bg-amber-400/60 transition-all duration-700"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                  <span className="text-xs font-semibold tabular-nums text-muted-foreground flex-shrink-0">
                    {emp.total}
                  </span>
                </button>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
