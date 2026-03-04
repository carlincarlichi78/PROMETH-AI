// dashboard/src/features/pipeline/components/PipelineFlowDiagram.tsx
import { useRef, useLayoutEffect, useState } from 'react'
import { PipelineNode, type NodoId } from './PipelineNode'
import { FlowConnector } from './FlowConnector'
import { DocumentParticle } from './DocumentParticle'
import type { FaseStatus } from '../hooks/usePipelineSyncStatus'
import type { ParticulaActiva } from '../hooks/usePipelineWebSocket'

interface Props {
  status: FaseStatus
  particulas: ParticulaActiva[]
  onParticulaCompleta: (id: string) => void
  empresaSeleccionada?: number
}

// Definición de los nodos del pipeline
const NODOS_PRINCIPALES: Array<{
  id: NodoId
  label: string
  icono: string
  color: 'slate' | 'amber' | 'blue' | 'green'
  statusKey: keyof FaseStatus
}> = [
  { id: 'inbox',      label: 'Inbox',      icono: '📥', color: 'slate',  statusKey: 'inbox' },
  { id: 'ocr',        label: 'OCR',        icono: '🔍', color: 'amber',  statusKey: 'procesando' },
  { id: 'validacion', label: 'Validación', icono: '✓',  color: 'amber',  statusKey: 'procesando' },
  { id: 'fs',         label: 'FS',         icono: '🏦', color: 'blue',   statusKey: 'procesando' },
  { id: 'asiento',    label: 'Asiento',    icono: '📊', color: 'blue',   statusKey: 'procesando' },
  { id: 'done',       label: 'Completado', icono: '✅', color: 'green',  statusKey: 'done_hoy' },
]

const CONEXIONES_PRINCIPALES: Array<{ desde: NodoId; hasta: NodoId }> = [
  { desde: 'inbox',      hasta: 'ocr' },
  { desde: 'ocr',        hasta: 'validacion' },
  { desde: 'validacion', hasta: 'fs' },
  { desde: 'fs',         hasta: 'asiento' },
  { desde: 'asiento',    hasta: 'done' },
]

interface Punto { x: number; y: number }

export function PipelineFlowDiagram({ status, particulas, onParticulaCompleta, empresaSeleccionada }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const nodoRefs = useRef<Partial<Record<NodoId, HTMLDivElement | null>>>({})
  const [centros, setCentros] = useState<Partial<Record<NodoId, Punto>>>({})
  const [svgSize, setSvgSize] = useState({ w: 0, h: 0 })

  // Recalcular centros tras render
  useLayoutEffect(() => {
    const container = containerRef.current
    if (!container) return

    const rect = container.getBoundingClientRect()
    setSvgSize({ w: rect.width, h: rect.height })

    const nuevos: Partial<Record<NodoId, Punto>> = {}
    for (const [id, el] of Object.entries(nodoRefs.current)) {
      if (!el) continue
      const r = el.getBoundingClientRect()
      nuevos[id as NodoId] = {
        x: r.left - rect.left + r.width / 2,
        y: r.top - rect.top + r.height / 2,
      }
    }
    setCentros(nuevos)
  }, [status])  // recalcular si cambia status (tamaño puede variar)

  const estaAtenuado = (_nodo: typeof NODOS_PRINCIPALES[0]) => {
    if (!empresaSeleccionada) return false
    const empresa = status.por_empresa[empresaSeleccionada]
    if (!empresa) return true
    return false  // si hay empresa con datos, no atenuar
  }

  return (
    <div ref={containerRef} className="relative w-full" style={{ minHeight: 200 }}>
      {/* Fuentes de entrada — indicadores sobre el nodo Inbox */}
      <div className="flex items-start justify-between px-4 pt-2 pb-0">
        <div className="flex flex-col items-center gap-1 w-28">
          <p className="text-[9px] text-muted-foreground/60 uppercase tracking-wider">Fuentes</p>
          <div className="flex flex-wrap justify-center gap-1">
            {[
              { icono: '📧', label: 'Correo' },
              { icono: '📁', label: 'Watcher' },
              { icono: '💻', label: 'Manual' },
            ].map(f => (
              <span
                key={f.label}
                title={f.label}
                className="inline-flex items-center gap-0.5 text-[9px] bg-slate-700/40 border border-slate-600/30 rounded px-1 py-0.5 text-slate-400"
              >
                {f.icono} {f.label}
              </span>
            ))}
          </div>
        </div>
        <div className="flex-1" /> {/* spacer */}
      </div>

      {/* Fila principal de nodos */}
      <div className="flex items-center justify-between gap-2 px-4 py-8">
        {NODOS_PRINCIPALES.map(nodo => (
          <div
            key={nodo.id}
            ref={el => { nodoRefs.current[nodo.id] = el }}
          >
            <PipelineNode
              id={nodo.id}
              label={nodo.label}
              count={nodo.id === 'done' ? status.done_hoy : nodo.id === 'inbox' ? status.inbox : Math.ceil(status.procesando / 3)}
              icono={nodo.icono}
              color={nodo.color}
              activo={nodo.id !== 'inbox' && nodo.id !== 'done' && status.procesando > 0}
              atenuado={estaAtenuado(nodo)}
            />
          </div>
        ))}
      </div>

      {/* Nodos de cuarentena y error */}
      <div className="flex justify-around px-4 pb-4">
        <div ref={el => { nodoRefs.current['cuarentena'] = el }} className="flex flex-col items-center gap-1">
          <PipelineNode id="cuarentena" label="Cuarentena" icono="⚠️" color="orange" count={status.cuarentena} />
        </div>
        <div ref={el => { nodoRefs.current['error'] = el }} className="flex flex-col items-center gap-1">
          <PipelineNode id="error" label="Error" icono="✕" color="red" count={status.error} />
        </div>
      </div>

      {/* SVG overlay para conectores */}
      {svgSize.w > 0 && (
        <svg
          className="absolute inset-0 pointer-events-none overflow-visible"
          width={svgSize.w}
          height={svgSize.h}
        >
          {/* Conexiones principales */}
          {CONEXIONES_PRINCIPALES.map(({ desde, hasta }) => {
            const p1 = centros[desde]
            const p2 = centros[hasta]
            if (!p1 || !p2) return null
            return (
              <FlowConnector
                key={`${desde}-${hasta}`}
                id={`${desde}-${hasta}`}
                desde={p1}
                hasta={p2}
                activo={status.procesando > 0}
              />
            )
          })}

          {/* Rama OCR → Cuarentena */}
          {centros.ocr && centros.cuarentena && (
            <FlowConnector
              id="ocr-cuarentena"
              desde={centros.ocr}
              hasta={centros.cuarentena}
              color="oklch(0.75 0.18 50)"
              activo={status.cuarentena > 0}
              vertical
            />
          )}

          {/* Rama Validación → Cuarentena */}
          {centros.validacion && centros.cuarentena && (
            <FlowConnector
              id="validacion-cuarentena"
              desde={centros.validacion}
              hasta={centros.cuarentena}
              color="oklch(0.75 0.18 50)"
              activo={status.cuarentena > 0}
              vertical
            />
          )}
        </svg>
      )}

      {/* Partículas en tránsito */}
      {particulas.map(p => (
        <DocumentParticle
          key={p.id}
          particula={p}
          onCompleta={onParticulaCompleta}
        />
      ))}
    </div>
  )
}
