// dashboard/src/features/pipeline/components/PipelineNode.tsx
import { useEffect, useState } from 'react'
import { cn } from '@/lib/utils'

export type NodoId = 'inbox' | 'ocr' | 'validacion' | 'fs' | 'asiento' | 'done' | 'cuarentena' | 'error'

interface Props {
  id: NodoId
  label: string
  sublabel?: string
  count: number
  icono: string          // emoji o char — mantiene sin deps extra
  color: 'amber' | 'blue' | 'green' | 'orange' | 'red' | 'slate'
  activo?: boolean       // true = worker procesando ahora mismo
  atenuado?: boolean     // true = empresa filtrada, no es la seleccionada
  className?: string
}

const COLOR_MAP: Record<Props['color'], {
  glow: string
  border: string
  bg: string
  text: string
  badge: string
}> = {
  amber: {
    glow:   'pipeline-node-pulse',
    border: 'border-amber-400/40',
    bg:     'bg-amber-500/5',
    text:   'text-amber-300',
    badge:  'bg-amber-500/20 text-amber-200',
  },
  blue: {
    glow:   'pipeline-node-pulse',
    border: 'border-blue-400/40',
    bg:     'bg-blue-500/5',
    text:   'text-blue-300',
    badge:  'bg-blue-500/20 text-blue-200',
  },
  green: {
    glow:   '',
    border: 'border-emerald-400/40',
    bg:     'bg-emerald-500/5',
    text:   'text-emerald-300',
    badge:  'bg-emerald-500/20 text-emerald-200',
  },
  orange: {
    glow:   '',
    border: 'border-orange-400/40',
    bg:     'bg-orange-500/5',
    text:   'text-orange-300',
    badge:  'bg-orange-500/20 text-orange-200',
  },
  red: {
    glow:   '',
    border: 'border-red-400/40',
    bg:     'bg-red-500/5',
    text:   'text-red-300',
    badge:  'bg-red-500/20 text-red-200',
  },
  slate: {
    glow:   '',
    border: 'border-slate-500/30',
    bg:     'bg-slate-500/5',
    text:   'text-slate-300',
    badge:  'bg-slate-500/20 text-slate-300',
  },
}

/** Count con transición suave al cambiar */
function AnimatedCount({ value }: { value: number }) {
  const [displayed, setDisplayed] = useState(value)
  const [flipping, setFlipping] = useState(false)

  useEffect(() => {
    if (value === displayed) return
    setFlipping(true)
    const t = setTimeout(() => {
      setDisplayed(value)
      setFlipping(false)
    }, 150)
    return () => clearTimeout(t)
  }, [value]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <span
      className={cn(
        'text-2xl font-bold tabular-nums transition-all duration-150',
        flipping && 'opacity-0 -translate-y-1'
      )}
    >
      {displayed}
    </span>
  )
}

export function PipelineNode({ id, label, sublabel, count, icono, color, activo, atenuado, className }: Props) {
  const c = COLOR_MAP[color]
  const tieneActividad = count > 0

  return (
    <div
      data-node-id={id}
      className={cn(
        // Base glassmorphism
        'relative flex flex-col items-center justify-center gap-1',
        'w-32 min-h-[110px] rounded-2xl px-3 py-4',
        'backdrop-blur-sm border',
        'transition-all duration-500',
        c.bg, c.border,
        // Glow cuando hay docs
        tieneActividad && !atenuado && (activo ? 'pipeline-node-active' : c.glow),
        // Aurora border wrapper via outline
        activo && !atenuado && 'outline outline-2 outline-offset-2 outline-amber-400/60',
        // Shadow cuando activo
        activo && !atenuado && 'shadow-amber-500/20 shadow-lg',
        // Atenuado (otro empresa seleccionada)
        atenuado ? 'opacity-30 scale-95' : 'opacity-100 scale-100',
        className,
      )}
    >
      {/* Glow ring exterior cuando hay actividad */}
      {tieneActividad && !atenuado && (
        <div className={cn(
          'absolute inset-0 rounded-2xl opacity-20 pointer-events-none',
          color === 'amber' && 'ring-2 ring-amber-400 animate-pulse',
          color === 'blue'  && 'ring-2 ring-blue-400',
          color === 'green' && 'ring-2 ring-emerald-400',
        )} />
      )}

      {/* Icono */}
      <span className="text-xl select-none">{icono}</span>

      {/* Label */}
      <span className={cn('text-[10px] font-semibold uppercase tracking-wider', c.text)}>
        {label}
      </span>

      {/* Count */}
      <div className={cn(
        'rounded-full px-2 py-0.5 min-w-[36px] text-center mt-1 transition-transform duration-200',
        c.badge,
        count > 0 && 'scale-110',
      )}>
        <AnimatedCount value={count} />
      </div>

      {/* Sublabel */}
      {sublabel && (
        <span className="text-[9px] text-muted-foreground text-center leading-tight">
          {sublabel}
        </span>
      )}

      {/* Indicador "activo" — punto pulsante */}
      {activo && !atenuado && (
        <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
      )}
    </div>
  )
}
