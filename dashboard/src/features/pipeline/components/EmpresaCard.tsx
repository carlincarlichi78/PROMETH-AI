// dashboard/src/features/pipeline/components/EmpresaCard.tsx
import { useEffect, useRef, useState } from 'react'
import { cn } from '@/lib/utils'
import type { EmpresaInfo, GestoriaConfig } from '../tipos-pipeline'
import { FASES_A_NODO, type NodoPipeline } from '../tipos-pipeline'
import { MiniPipelineVertical } from './MiniPipelineVertical'
import type { EventoWS } from '../hooks/usePipelineWebSocket'
import { esProcesandoAhora } from '../hooks/usePipelineWebSocket'

interface EmpresaStats {
  inbox: number
  procesando: number
  cuarentena: number
  error: number
  done_hoy: number
}

interface Props {
  empresa: EmpresaInfo
  stats: EmpresaStats
  eventoActivo: EventoWS | undefined
  gestoria: GestoriaConfig
}

export function EmpresaCard({ empresa, stats, eventoActivo, gestoria }: Props) {
  const procesandoAhora = esProcesandoAhora(eventoActivo)
  const tieneActividad = stats.done_hoy > 0 || stats.procesando > 0 || stats.inbox > 0
  const tieneCuarentena = stats.cuarentena > 0
  const tieneError = stats.error > 0

  // Determinar estado visual
  const estado: 'procesando' | 'activo' | 'cuarentena' | 'error' | 'inactivo' =
    procesandoAhora        ? 'procesando'  :
    tieneError             ? 'error'       :
    tieneCuarentena        ? 'cuarentena'  :
    tieneActividad         ? 'activo'      :
    'inactivo'

  // Ring pulse al llegar nuevo evento
  const [ringActivo, setRingActivo] = useState(false)
  const prevEventoId = useRef<string | undefined>(undefined)

  useEffect(() => {
    if (!eventoActivo || eventoActivo.id === prevEventoId.current) return
    prevEventoId.current = eventoActivo.id
    setRingActivo(true)
    const t = setTimeout(() => setRingActivo(false), 700)
    return () => clearTimeout(t)
  }, [eventoActivo])

  // Nodo activo y partícula según último evento
  const nodoActivo: NodoPipeline | null = eventoActivo?.datos.fase_actual
    ? (FASES_A_NODO[eventoActivo.datos.fase_actual] ?? null)
    : null

  const tipDoc = eventoActivo?.datos.tipo_doc ?? ''

  // Calcular origen y destino de la partícula
  const particulaOrigen: NodoPipeline | null = procesandoAhora && nodoActivo
    ? nodoActivo
    : null
  const particulaDestino: NodoPipeline | null = (() => {
    if (!particulaOrigen) return null
    const nodos: NodoPipeline[] = ['inbox', 'ocr', 'validacion', 'fs', 'asiento', 'done']
    const idx = nodos.indexOf(particulaOrigen)
    return idx >= 0 && idx < nodos.length - 1 ? nodos[idx + 1]! : 'done'
  })()

  // Colores según estado
  const borderColor =
    estado === 'procesando' ? gestoria.color :
    estado === 'error'      ? 'oklch(0.65 0.20 22)'  :
    estado === 'cuarentena' ? 'oklch(0.75 0.18 50)'  :
    'transparent'

  const indicadorColor =
    estado === 'procesando' ? gestoria.colorRgb :
    estado === 'activo'     ? '74, 222, 128'       :  // emerald
    estado === 'cuarentena' ? '251, 146, 60'        :  // orange
    estado === 'error'      ? '248, 113, 113'       :  // red
    '71, 85, 105'                                       // slate inactivo

  return (
    <div
      className={cn(
        'relative rounded-xl px-3 py-2.5 flex items-center gap-3',
        'border transition-all duration-500',
        'backdrop-blur-sm',
        estado === 'inactivo' && 'opacity-50',
        ringActivo && 'empresa-ring-pulse',
      )}
      style={{
        background: estado === 'procesando'
          ? `oklch(from ${gestoria.color} l c h / 0.08)`
          : 'oklch(0.12 0.01 260 / 0.8)',
        borderColor: estado !== 'inactivo' ? borderColor : 'oklch(0.2 0.01 260)',
        '--empresa-ring-color': `rgb(${indicadorColor} / 0.7)`,
        boxShadow: estado === 'procesando'
          ? `0 0 12px 0 ${gestoria.color}40`
          : 'none',
      } as React.CSSProperties}
    >
      {/* Indicador de estado (punto izquierdo) */}
      <div className="flex-shrink-0">
        <div className="relative w-2.5 h-2.5">
          {estado === 'procesando' && (
            <span
              className="empresa-dot-ping absolute inset-0 rounded-full"
              style={{ background: `rgb(${indicadorColor})` }}
            />
          )}
          <div
            className={cn(
              'absolute inset-0 rounded-full',
              estado === 'procesando' && 'empresa-border-glow',
            )}
            style={{ background: `rgb(${indicadorColor})` }}
          />
        </div>
      </div>

      {/* Contenido principal */}
      <div className="flex-1 min-w-0 space-y-1">
        {/* Nombre + badge tipo doc */}
        <div className="flex items-center gap-2">
          <span className={cn(
            'text-[11px] font-semibold truncate',
            estado === 'inactivo' ? 'text-white/30' : 'text-white/90',
          )}>
            {empresa.nombreCorto}
          </span>
          {tipDoc && estado === 'procesando' && (
            <span
              className="text-[9px] font-bold px-1.5 py-0.5 rounded-md flex-shrink-0"
              style={{
                background: `${gestoria.color}30`,
                color: gestoria.color,
                border: `1px solid ${gestoria.color}50`,
              }}
            >
              {tipDoc}
            </span>
          )}
        </div>

        {/* Stats */}
        <div className="flex items-center gap-2">
          <span className={cn(
            'text-[9px] tabular-nums',
            stats.done_hoy > 0 ? 'text-emerald-400/70' : 'text-white/15',
          )}>
            {stats.done_hoy} hoy
          </span>
          {(stats.inbox + stats.procesando) > 0 && (
            <span className="text-[9px] tabular-nums text-amber-400/70">
              {stats.inbox + stats.procesando} cola
            </span>
          )}
          {stats.cuarentena > 0 && (
            <span className="text-[9px] tabular-nums text-orange-400/80">
              ⚠ {stats.cuarentena}
            </span>
          )}
          {stats.error > 0 && (
            <span className="text-[9px] tabular-nums text-red-400/80">
              ✕ {stats.error}
            </span>
          )}
        </div>
      </div>

      {/* Mini pipeline vertical */}
      <div className="flex-shrink-0">
        <MiniPipelineVertical
          nodoActivo={nodoActivo}
          particulaOrigen={particulaOrigen}
          particulaDestino={particulaDestino}
          tipDoc={tipDoc}
          colorGestoria={gestoria.color}
        />
      </div>
    </div>
  )
}
