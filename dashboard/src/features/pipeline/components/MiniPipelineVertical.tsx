// dashboard/src/features/pipeline/components/MiniPipelineVertical.tsx
import { useState, useEffect } from 'react'
import { cn } from '@/lib/utils'
import { NODOS_PIPELINE, NODO_LABEL, type NodoPipeline, COLOR_TIPO_DOC } from '../tipos-pipeline'

interface Props {
  nodoActivo: NodoPipeline | null    // nodo actualmente iluminado (del ultimo evento WS)
  particulaOrigen: NodoPipeline | null
  particulaDestino: NodoPipeline | null
  tipDoc: string                      // para color de partícula
  colorGestoria: string               // oklch del gestor
}

// Porcentaje vertical de cada nodo dentro del contenedor (0-100)
const NODO_TOP_PCT: Record<NodoPipeline, number> = {
  inbox:     0,
  ocr:       20,
  validacion:40,
  fs:        60,
  asiento:   80,
  done:      100,
}

export function MiniPipelineVertical({ nodoActivo, particulaOrigen, particulaDestino, tipDoc, colorGestoria }: Props) {
  const color = COLOR_TIPO_DOC[tipDoc] ?? COLOR_TIPO_DOC.default

  // Partícula: inicia en el origen, transiciona al destino
  const [particulaPct, setParticulaPct] = useState<number | null>(null)

  useEffect(() => {
    if (!particulaOrigen || !particulaDestino) {
      setParticulaPct(null)
      return
    }
    // Comenzar en origen
    const originPct = NODO_TOP_PCT[particulaOrigen]
    setParticulaPct(originPct)
    // Un frame después, animar al destino
    const raf = requestAnimationFrame(() => {
      const destPct = NODO_TOP_PCT[particulaDestino]
      setParticulaPct(destPct)
    })
    return () => cancelAnimationFrame(raf)
  }, [particulaOrigen, particulaDestino])

  return (
    <div className="relative flex flex-col items-center" style={{ width: 36, height: 120 }}>
      {/* Línea vertical central */}
      <div
        className="absolute top-2 bottom-2 w-px"
        style={{ left: 17, background: 'oklch(0.3 0.01 260)' }}
      />

      {/* Nodos */}
      {NODOS_PIPELINE.map((nodo) => {
        const topPct = NODO_TOP_PCT[nodo]
        const esActivo = nodo === nodoActivo
        const esDone = nodo === 'done'

        return (
          <div
            key={nodo}
            className="absolute flex items-center gap-1.5"
            style={{ top: `calc(${topPct}% - 5px)`, left: 0, right: 0 }}
          >
            {/* Punto del nodo */}
            <div
              className={cn(
                'rounded-full transition-all duration-300 flex-shrink-0',
                esActivo ? 'w-3 h-3' : 'w-2 h-2',
                esDone && !esActivo && 'w-2.5 h-2.5',
              )}
              style={{
                background: esActivo
                  ? colorGestoria
                  : esDone
                  ? 'oklch(0.52 0.17 145)'
                  : 'oklch(0.3 0.02 260)',
                boxShadow: esActivo ? `0 0 6px 2px ${colorGestoria}` : 'none',
                marginLeft: esActivo ? 11 : 12,
              }}
            />
            {/* Label del nodo */}
            <span
              className={cn(
                'text-[8px] font-mono tracking-wide transition-all duration-300',
                esActivo ? 'text-white' : 'text-white/20',
              )}
            >
              {NODO_LABEL[nodo]}
            </span>
          </div>
        )
      })}

      {/* Partícula viajando */}
      {particulaPct !== null && (
        <div
          className="absolute rounded-full pointer-events-none z-10"
          style={{
            width: 6,
            height: 6,
            background: color,
            boxShadow: `0 0 6px 2px ${color}`,
            left: 14,
            top: `calc(${particulaPct}% - 3px)`,
            transition: 'top 1.5s ease-in-out',
          }}
        />
      )}
    </div>
  )
}
