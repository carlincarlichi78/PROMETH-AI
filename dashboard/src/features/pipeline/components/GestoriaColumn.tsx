// dashboard/src/features/pipeline/components/GestoriaColumn.tsx
import { cn } from '@/lib/utils'
import type { EmpresaInfo, GestoriaConfig } from '../tipos-pipeline'
import { EmpresaCard } from './EmpresaCard'
import type { FaseStatus, BreakdownStatus } from '../hooks/usePipelineSyncStatus'
import type { EventoWS } from '../hooks/usePipelineWebSocket'
import { esProcesandoAhora } from '../hooks/usePipelineWebSocket'

interface Props {
  gestoria: GestoriaConfig
  empresas: EmpresaInfo[]
  status: FaseStatus
  breakdown: BreakdownStatus
  eventosActivos: Record<number, EventoWS>
}

const STATS_VACIOS = { inbox: 0, procesando: 0, cuarentena: 0, error: 0, done_hoy: 0 }

export function GestoriaColumn({ gestoria, empresas, status, breakdown: _breakdown, eventosActivos }: Props) {
  // Total docs hoy para la gestoría
  const totalHoy = empresas.reduce((sum, e) => {
    return sum + (status.por_empresa[e.id]?.done_hoy ?? 0)
  }, 0)

  // Cuántas empresas procesando ahora
  const procesandoAhora = empresas.filter(e => esProcesandoAhora(eventosActivos[e.id])).length

  return (
    <div className="flex flex-col h-full min-w-0">
      {/* Header gestoria */}
      <div
        className="flex-shrink-0 rounded-xl px-4 py-3 mb-3 border"
        style={{
          background: `oklch(from ${gestoria.color} l c h / 0.06)`,
          borderColor: `oklch(from ${gestoria.color} l c h / 0.25)`,
        }}
      >
        {/* Nombre + indicador */}
        <div className="flex items-center gap-2 mb-1">
          {procesandoAhora > 0 && (
            <span
              className="w-2 h-2 rounded-full empresa-dot-ping flex-shrink-0"
              style={{ background: gestoria.color }}
            />
          )}
          <span
            className="text-sm font-bold tracking-wide"
            style={{ color: gestoria.color }}
          >
            {gestoria.nombre.toUpperCase()}
          </span>
          <span className={cn('text-[9px] text-white/30 font-mono truncate')}>
            {gestoria.email}
          </span>
        </div>

        {/* Stats resumen */}
        <div className="flex items-center gap-3">
          <span className="text-[10px] text-white/40">
            {empresas.length} empresas
          </span>
          {totalHoy > 0 && (
            <span className="text-[10px] text-emerald-400/70">
              {totalHoy} docs hoy
            </span>
          )}
          {procesandoAhora > 0 && (
            <span className="text-[10px] font-semibold" style={{ color: gestoria.color }}>
              {procesandoAhora} procesando
            </span>
          )}
        </div>
      </div>

      {/* Tarjetas de empresa — distribuidas verticalmente para llenar la columna */}
      <div className="flex flex-col flex-1 gap-2 overflow-y-auto">
        {empresas.map(empresa => {
          const stats = status.por_empresa[empresa.id] ?? STATS_VACIOS
          const eventoActivo = eventosActivos[empresa.id]
          return (
            <div key={empresa.id} className="flex-1 min-h-[80px] flex flex-col justify-center">
              <EmpresaCard
                empresa={empresa}
                stats={stats}
                eventoActivo={eventoActivo}
                gestoria={gestoria}
              />
            </div>
          )
        })}
      </div>
    </div>
  )
}
