// dashboard/src/features/pipeline/components/FlowConnector.tsx
import { cn } from '@/lib/utils'

interface Punto { x: number; y: number }

interface Props {
  desde: Punto
  hasta: Punto
  id: string             // para referencia desde DocumentParticle
  color?: string         // stroke color, default amber
  activo?: boolean       // si hay docs fluyendo
  vertical?: boolean     // rama hacia abajo (cuarentena)
  atenuado?: boolean
}

/** Genera un path bezier cuadrático entre dos puntos */
function bezierPath(desde: Punto, hasta: Punto, vertical?: boolean): string {
  if (vertical) {
    // Rama vertical hacia abajo: curva suave
    const cx = desde.x
    const cy = desde.y + (hasta.y - desde.y) * 0.5
    return `M ${desde.x} ${desde.y} Q ${cx} ${cy} ${hasta.x} ${hasta.y}`
  }
  // Horizontal: control point en el punto medio
  const cx = (desde.x + hasta.x) / 2
  const cy = desde.y
  return `M ${desde.x} ${desde.y} Q ${cx} ${cy} ${hasta.x} ${hasta.y}`
}

export function FlowConnector({ desde, hasta, id, color = 'oklch(0.78 0.15 70)', activo, vertical, atenuado }: Props) {
  const path = bezierPath(desde, hasta, vertical)
  const dashLen = vertical ? 4 : 8
  const dashGap = vertical ? 4 : 12
  const duracion = vertical ? '1s' : '1.5s'

  return (
    <g
      id={`connector-${id}`}
      className={cn('transition-opacity duration-500', atenuado && 'opacity-20')}
    >
      {/* Línea base (sombra/halo) */}
      <path
        d={path}
        fill="none"
        stroke={color}
        strokeWidth={activo ? 3 : 1.5}
        strokeOpacity={activo ? 0.15 : 0.08}
      />

      {/* Línea animada con dashoffset */}
      <path
        d={path}
        fill="none"
        stroke={color}
        strokeWidth={activo ? 2 : 1}
        strokeOpacity={activo ? 0.7 : 0.3}
        strokeDasharray={`${dashLen} ${dashGap}`}
        style={{
          animation: activo
            ? `flow-dash ${duracion} linear infinite`
            : undefined,
          strokeDashoffset: activo ? undefined : 0,
        }}
      />

      {/* Punta de flecha */}
      <path
        d={`M ${hasta.x - 6} ${hasta.y - 4} L ${hasta.x} ${hasta.y} L ${hasta.x - 6} ${hasta.y + 4}`}
        fill="none"
        stroke={color}
        strokeWidth={1.5}
        strokeOpacity={activo ? 0.7 : 0.3}
      />
    </g>
  )
}

/** Exporta el string del path para que DocumentParticle lo use como offset-path */
export function obtenerPathConector(id: string): string | null {
  const el = document.getElementById(`connector-${id}`)?.querySelector('path')
  return el ? el.getAttribute('d') : null
}
