// dashboard/src/features/pipeline/components/DocumentParticle.tsx
import { useEffect, useRef } from 'react'
import type { ParticulaActiva } from '../hooks/usePipelineWebSocket'
import { obtenerPathConector } from './FlowConnector'

const COLOR_TIPO: Record<string, string> = {
  FC: 'oklch(0.75 0.18 145)',    // green — factura cliente
  FV: 'oklch(0.65 0.20 250)',    // blue — factura proveedor
  NC: 'oklch(0.75 0.18 70)',     // amber — nota crédito
  SUM: 'oklch(0.70 0.15 300)',   // purple — suministro
  IMP: 'oklch(0.75 0.18 200)',   // teal — impuesto/modelo
  NOM: 'oklch(0.70 0.15 350)',   // pink — nómina
  BAN: 'oklch(0.75 0.10 210)',   // light blue — banco
  default: 'oklch(0.78 0.15 70)', // amber fallback
}

const DURACION_MS = 3000

interface Props {
  particula: ParticulaActiva
  onCompleta: (id: string) => void
}

export function DocumentParticle({ particula, onCompleta }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const connectorId = `${particula.nodo_origen}-${particula.nodo_destino}`
  const color = COLOR_TIPO[particula.tipo_doc] ?? COLOR_TIPO.default

  useEffect(() => {
    const el = ref.current
    if (!el) return

    // Obtener el path SVG del conector correspondiente
    const pathD = obtenerPathConector(connectorId)
    if (!pathD) {
      // Si no hay path (aún no renderizado), cancelar
      const t = setTimeout(() => onCompleta(particula.id), 100)
      return () => clearTimeout(t)
    }

    el.style.offsetPath = `path('${pathD}')`
    el.style.offsetDistance = '0%'
    el.style.animation = `particle-travel ${DURACION_MS}ms ease-in-out forwards`

    const t = setTimeout(() => onCompleta(particula.id), DURACION_MS)
    return () => clearTimeout(t)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div
      ref={ref}
      className="fixed pointer-events-none z-50"
      style={{
        width: 10,
        height: 10,
        borderRadius: '50%',
        backgroundColor: color,
        boxShadow: `0 0 8px 3px ${color}`,
        transform: 'translate(-50%, -50%)',
      }}
    />
  )
}
