// dashboard/src/features/pipeline/components/GlobalStatsStrip.tsx
import { cn } from '@/lib/utils'
import type { FaseStatus } from '../hooks/usePipelineSyncStatus'

interface Props {
  status: FaseStatus
  conectado: boolean
}

interface Stat {
  label: string
  valor: number
  color: string
  icono: string
}

export function GlobalStatsStrip({ status, conectado }: Props) {
  const stats: Stat[] = [
    { label: 'Completados hoy', valor: status.done_hoy,   color: 'text-emerald-400', icono: '✓' },
    { label: 'En cola',         valor: status.inbox,       color: 'text-slate-300',   icono: '●' },
    { label: 'Procesando',      valor: status.procesando,  color: 'text-amber-400',   icono: '⟳' },
    { label: 'Cuarentena',      valor: status.cuarentena,  color: 'text-orange-400',  icono: '⚠' },
    { label: 'Error',           valor: status.error,       color: 'text-red-400',     icono: '✕' },
  ]

  return (
    <div className="flex items-center gap-6 px-6 py-3 border-b border-white/5 bg-black/20 backdrop-blur-sm">
      {/* Indicador conexión WS */}
      <div className="flex items-center gap-1.5 mr-2">
        <span className={cn(
          'w-2 h-2 rounded-full',
          conectado ? 'bg-emerald-400 animate-pulse' : 'bg-red-400'
        )} />
        <span className="text-[10px] text-muted-foreground uppercase tracking-wider">
          {conectado ? 'en vivo' : 'desconectado'}
        </span>
      </div>

      {stats.map(s => (
        <div key={s.label} className="flex items-center gap-2">
          <span className={cn('text-lg font-bold tabular-nums', s.color)}>
            {s.icono} {s.valor}
          </span>
          <span className="text-[11px] text-muted-foreground hidden sm:inline">{s.label}</span>
        </div>
      ))}
    </div>
  )
}
