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
}

export function GlobalStatsStrip({ status, conectado }: Props) {
  const stats: Stat[] = [
    { label: 'Completados hoy', valor: status.done_hoy,   color: 'text-emerald-400' },
    { label: 'En cola',         valor: status.inbox,       color: 'text-slate-300' },
    { label: 'Procesando',      valor: status.procesando,  color: 'text-amber-400' },
    { label: 'Cuarentena',      valor: status.cuarentena,  color: 'text-orange-400' },
    { label: 'Error',           valor: status.error,       color: 'text-red-400' },
  ]

  return (
    <div className="flex items-center gap-4 px-6 py-2.5 border-b border-white/5 bg-black/30 backdrop-blur-md">
      {/* Indicador WS */}
      <div className="flex items-center gap-1.5 pr-4 border-r border-white/10">
        <span className="relative flex w-2.5 h-2.5">
          {conectado && (
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
          )}
          <span className={cn(
            'relative inline-flex rounded-full w-2.5 h-2.5',
            conectado ? 'bg-emerald-400' : 'bg-red-500'
          )} />
        </span>
        <span className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
          {conectado ? 'En vivo' : 'Desconectado'}
        </span>
      </div>

      {/* Stats */}
      {stats.map(s => (
        <div key={s.label} className="flex items-baseline gap-1.5">
          <span className={cn('text-xl font-bold tabular-nums leading-none', s.color)}>
            {s.valor}
          </span>
          <span className="text-[10px] text-muted-foreground/70 hidden sm:inline">{s.label}</span>
        </div>
      ))}

      {/* Timestamp */}
      <div className="ml-auto text-[9px] text-muted-foreground/40 tabular-nums hidden md:block">
        {status.actualizado_en ? new Date(status.actualizado_en).toLocaleTimeString('es-ES') : ''}
      </div>
    </div>
  )
}
