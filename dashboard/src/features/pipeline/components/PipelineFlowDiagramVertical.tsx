// dashboard/src/features/pipeline/components/PipelineFlowDiagramVertical.tsx
import { cn } from '@/lib/utils'
import type { FaseStatus } from '../hooks/usePipelineSyncStatus'

interface Props {
  status: FaseStatus
}

interface NodoVertical {
  id: string
  label: string
  icono: string
  count: number
  color: string       // clase tailwind
  bgColor: string     // oklch bg
  borderColor: string
  activo: boolean
}

export function PipelineFlowDiagramVertical({ status }: Props) {
  const nodos: NodoVertical[] = [
    {
      id: 'inbox',
      label: 'INBOX',
      icono: '📥',
      count: status.inbox,
      color: 'text-slate-300',
      bgColor: 'oklch(0.15 0.01 260 / 0.8)',
      borderColor: 'oklch(0.3 0.02 260)',
      activo: status.inbox > 0,
    },
    {
      id: 'ocr',
      label: 'OCR',
      icono: '🔍',
      count: Math.ceil(status.procesando / 3),
      color: 'text-amber-300',
      bgColor: 'oklch(0.15 0.04 60 / 0.5)',
      borderColor: status.procesando > 0 ? 'oklch(0.75 0.18 70 / 0.5)' : 'oklch(0.3 0.02 260)',
      activo: status.procesando > 0,
    },
    {
      id: 'validacion',
      label: 'VALID',
      icono: '✓',
      count: Math.ceil(status.procesando / 3),
      color: 'text-amber-300',
      bgColor: 'oklch(0.15 0.04 60 / 0.5)',
      borderColor: status.procesando > 0 ? 'oklch(0.75 0.18 70 / 0.5)' : 'oklch(0.3 0.02 260)',
      activo: status.procesando > 0,
    },
    {
      id: 'fs',
      label: 'FS',
      icono: '🏦',
      count: Math.ceil(status.procesando / 3),
      color: 'text-blue-300',
      bgColor: 'oklch(0.15 0.04 250 / 0.5)',
      borderColor: status.procesando > 0 ? 'oklch(0.65 0.20 250 / 0.5)' : 'oklch(0.3 0.02 260)',
      activo: status.procesando > 0,
    },
    {
      id: 'asiento',
      label: 'ASIENTO',
      icono: '📊',
      count: Math.ceil(status.procesando / 3),
      color: 'text-blue-300',
      bgColor: 'oklch(0.15 0.04 250 / 0.5)',
      borderColor: status.procesando > 0 ? 'oklch(0.65 0.20 250 / 0.5)' : 'oklch(0.3 0.02 260)',
      activo: status.procesando > 0,
    },
    {
      id: 'done',
      label: 'DONE',
      icono: '✅',
      count: status.done_hoy,
      color: 'text-emerald-300',
      bgColor: 'oklch(0.15 0.08 145 / 0.5)',
      borderColor: status.done_hoy > 0 ? 'oklch(0.52 0.17 145 / 0.5)' : 'oklch(0.3 0.02 260)',
      activo: status.done_hoy > 0,
    },
  ]

  return (
    <div className="flex flex-col h-full">
      {/* Título */}
      <div className="flex-shrink-0 mb-4">
        <h2 className="text-[10px] font-semibold uppercase tracking-widest text-white/30 text-center">
          Flujo Global
        </h2>
      </div>

      {/* Nodos verticales — flex-1 para llenar altura */}
      <div className="flex flex-col flex-1 relative">
        {/* Línea conectora de fondo */}
        <div
          className="absolute w-px"
          style={{
            left: '50%',
            top: '24px',
            bottom: '24px',
            background: 'linear-gradient(to bottom, oklch(0.3 0.02 260), oklch(0.52 0.17 145 / 0.3))',
          }}
        />

        {nodos.map((nodo, idx) => (
          <div key={nodo.id} className="flex-1 flex flex-col items-center justify-center relative">
            {/* Nodo */}
            <div
              className={cn(
                'relative flex flex-col items-center justify-center gap-1',
                'rounded-xl px-3 py-2 w-full',
                'border transition-all duration-500',
                nodo.activo && 'pipeline-node-pulse',
              )}
              style={{
                background: nodo.bgColor,
                borderColor: nodo.borderColor,
                boxShadow: nodo.activo ? `0 0 12px -2px ${nodo.borderColor}` : 'none',
              }}
            >
              <span className="text-base select-none">{nodo.icono}</span>
              <span className={cn('text-[9px] font-semibold tracking-wider', nodo.color)}>
                {nodo.label}
              </span>
              <span className={cn(
                'text-lg font-bold tabular-nums leading-none transition-all duration-300',
                nodo.activo ? nodo.color : 'text-white/20',
              )}>
                {nodo.count}
              </span>

              {/* Punto pulsante si activo */}
              {nodo.activo && (
                <span
                  className="absolute top-1 right-1 w-1.5 h-1.5 rounded-full animate-pulse"
                  style={{ background: nodo.borderColor }}
                />
              )}
            </div>

            {/* Flecha entre nodos (excepto último) */}
            {idx < nodos.length - 1 && (
              <div className="flex items-center justify-center py-0.5">
                <span className="text-white/15 text-[10px]">↓</span>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Cuarentena y Error — fila inferior */}
      <div className="flex-shrink-0 mt-3 grid grid-cols-2 gap-2">
        <div
          className="flex flex-col items-center gap-0.5 rounded-lg px-2 py-2 border"
          style={{
            background: 'oklch(0.13 0.04 50 / 0.5)',
            borderColor: status.cuarentena > 0 ? 'oklch(0.75 0.18 50 / 0.5)' : 'oklch(0.25 0.01 260)',
          }}
        >
          <span className="text-sm">⚠️</span>
          <span className={cn(
            'text-base font-bold tabular-nums',
            status.cuarentena > 0 ? 'text-orange-400' : 'text-white/20',
          )}>
            {status.cuarentena}
          </span>
          <span className="text-[8px] text-white/20 uppercase tracking-wide">cuarent.</span>
        </div>
        <div
          className="flex flex-col items-center gap-0.5 rounded-lg px-2 py-2 border"
          style={{
            background: 'oklch(0.13 0.04 22 / 0.5)',
            borderColor: status.error > 0 ? 'oklch(0.65 0.20 22 / 0.5)' : 'oklch(0.25 0.01 260)',
          }}
        >
          <span className="text-sm">✕</span>
          <span className={cn(
            'text-base font-bold tabular-nums',
            status.error > 0 ? 'text-red-400' : 'text-white/20',
          )}>
            {status.error}
          </span>
          <span className="text-[8px] text-white/20 uppercase tracking-wide">error</span>
        </div>
      </div>
    </div>
  )
}
