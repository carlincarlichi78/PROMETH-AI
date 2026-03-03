// dashboard/src/features/pipeline/components/EmpresaBadges.tsx
import { cn } from '@/lib/utils'

interface Empresa {
  id: number
  nombre: string
}

interface Props {
  empresas: Empresa[]
  seleccionada?: number
  onSeleccionar: (id: number | undefined) => void
}

// Paleta de colores por posición (hasta 13 empresas)
const PALETA = [
  'bg-violet-500/20 border-violet-400/40 text-violet-300 hover:bg-violet-500/30',
  'bg-blue-500/20 border-blue-400/40 text-blue-300 hover:bg-blue-500/30',
  'bg-emerald-500/20 border-emerald-400/40 text-emerald-300 hover:bg-emerald-500/30',
  'bg-amber-500/20 border-amber-400/40 text-amber-300 hover:bg-amber-500/30',
  'bg-rose-500/20 border-rose-400/40 text-rose-300 hover:bg-rose-500/30',
  'bg-cyan-500/20 border-cyan-400/40 text-cyan-300 hover:bg-cyan-500/30',
  'bg-orange-500/20 border-orange-400/40 text-orange-300 hover:bg-orange-500/30',
  'bg-pink-500/20 border-pink-400/40 text-pink-300 hover:bg-pink-500/30',
  'bg-teal-500/20 border-teal-400/40 text-teal-300 hover:bg-teal-500/30',
  'bg-indigo-500/20 border-indigo-400/40 text-indigo-300 hover:bg-indigo-500/30',
  'bg-lime-500/20 border-lime-400/40 text-lime-300 hover:bg-lime-500/30',
  'bg-sky-500/20 border-sky-400/40 text-sky-300 hover:bg-sky-500/30',
  'bg-fuchsia-500/20 border-fuchsia-400/40 text-fuchsia-300 hover:bg-fuchsia-500/30',
]

function abreviatura(nombre: string): string {
  return nombre.split(' ').slice(0, 2).map(w => w[0]).join('').toUpperCase()
}

export function EmpresaBadges({ empresas, seleccionada, onSeleccionar }: Props) {
  if (empresas.length === 0) return null

  return (
    <div className="flex flex-wrap items-center gap-2 px-6 py-2 border-b border-white/5">
      {/* Chip "Todas" */}
      <button
        onClick={() => onSeleccionar(undefined)}
        className={cn(
          'px-3 py-1 rounded-full text-xs font-medium border transition-all duration-200',
          !seleccionada
            ? 'bg-white/10 border-white/30 text-white'
            : 'bg-transparent border-white/10 text-muted-foreground hover:border-white/20'
        )}
      >
        Todas
      </button>

      {empresas.map((e, i) => {
        const activa = seleccionada === e.id
        const clases = PALETA[i % PALETA.length]
        return (
          <button
            key={e.id}
            onClick={() => onSeleccionar(activa ? undefined : e.id)}
            className={cn(
              'flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border transition-all duration-200',
              activa ? clases : 'bg-transparent border-white/10 text-muted-foreground hover:border-white/20 hover:text-foreground',
            )}
            title={e.nombre}
          >
            <span className={cn(
              'w-5 h-5 rounded-full flex items-center justify-center text-[9px] font-bold flex-shrink-0',
              activa ? 'bg-current/20' : 'bg-white/10'
            )}>
              {abreviatura(e.nombre)}
            </span>
            <span className="max-w-[100px] truncate">{e.nombre.split(' ')[0]}</span>
            {activa && <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" />}
          </button>
        )
      })}
    </div>
  )
}
