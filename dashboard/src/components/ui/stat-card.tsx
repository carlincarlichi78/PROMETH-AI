// src/components/ui/stat-card.tsx
import { cn } from '@/lib/utils'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

interface StatCardProps {
  titulo: string
  valor: string | number
  subtitulo?: string
  tendencia?: 'up' | 'down' | 'neutral'
  tendenciaTexto?: string
  variante?: 'default' | 'success' | 'warning' | 'danger' | 'info'
  icono?: React.ReactNode
  cargando?: boolean
  className?: string
  onClick?: () => void
}

const varianteClases = {
  default:  'border-border/50',
  success:  'border-[var(--state-success)]/30',
  warning:  'border-[var(--state-warning)]/30',
  danger:   'border-[var(--state-danger)]/30',
  info:     'border-[var(--state-info)]/30',
}

const tendenciaIcono = {
  up:      <TrendingUp  className="h-3.5 w-3.5 text-[var(--state-success)]" />,
  down:    <TrendingDown className="h-3.5 w-3.5 text-[var(--state-danger)]" />,
  neutral: <Minus       className="h-3.5 w-3.5 text-muted-foreground" />,
}

export function StatCard({
  titulo, valor, subtitulo, tendencia, tendenciaTexto,
  variante = 'default', icono, cargando, className, onClick,
}: StatCardProps) {
  if (cargando) {
    return (
      <div className={cn(
        'rounded-xl border p-5 bg-[var(--surface-1)] animate-pulse',
        varianteClases[variante], className
      )}>
        <div className="h-3 w-24 bg-[var(--surface-2)] rounded mb-3" />
        <div className="h-8 w-32 bg-[var(--surface-2)] rounded mb-2" />
        <div className="h-3 w-20 bg-[var(--surface-2)] rounded" />
      </div>
    )
  }

  return (
    <div
      className={cn(
        'rounded-xl border p-5 bg-[var(--surface-1)] transition-all duration-150',
        varianteClases[variante],
        onClick && 'cursor-pointer hover:bg-[var(--surface-2)] hover:-translate-y-0.5',
        className
      )}
      onClick={onClick}
    >
      <div className="flex items-start justify-between mb-2">
        <span className="text-[13px] font-medium text-muted-foreground uppercase tracking-wide">
          {titulo}
        </span>
        {icono && <span className="text-muted-foreground">{icono}</span>}
      </div>

      <div className="text-[32px] font-bold tracking-tight tabular-nums leading-none mb-2">
        {valor}
      </div>

      {(subtitulo || tendencia) && (
        <div className="flex items-center gap-1.5">
          {tendencia && tendenciaIcono[tendencia]}
          <span className="text-[13px] text-muted-foreground">{tendenciaTexto ?? subtitulo}</span>
        </div>
      )}
    </div>
  )
}
