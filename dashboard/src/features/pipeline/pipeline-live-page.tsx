// dashboard/src/features/pipeline/pipeline-live-page.tsx
import { useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { usePipelineWebSocket } from './hooks/usePipelineWebSocket'
import { usePipelineSyncStatus } from './hooks/usePipelineSyncStatus'
import { GlobalStatsStrip } from './components/GlobalStatsStrip'
import { GestoriaColumn } from './components/GestoriaColumn'
import { PipelineFlowDiagramVertical } from './components/PipelineFlowDiagramVertical'
import { EMPRESAS_POR_GESTORIA, GESTORIA_CONFIG } from './tipos-pipeline'

export default function PipelineLivePage() {
  const qc = useQueryClient()

  const { eventos: _eventos, particulas: _particulas, conectado, contadores_fuente, eventosActivos, eliminarParticula: _eliminar } =
    usePipelineWebSocket()

  const { status, breakdown } = usePipelineSyncStatus()

  // Invalidar breakdown cuando llega nuevo PDF por WS
  const prevContadoresRef = useRef({ ...contadores_fuente })
  const totalWS = contadores_fuente.correo + contadores_fuente.manual + contadores_fuente.watcher
  const prevTotal = prevContadoresRef.current.correo + prevContadoresRef.current.manual + prevContadoresRef.current.watcher
  if (totalWS !== prevTotal) {
    qc.invalidateQueries({ queryKey: ['pipeline-breakdown'] })
    prevContadoresRef.current = { ...contadores_fuente }
  }

  return (
    <div
      className="flex flex-col h-full"
      style={{
        background: [
          'radial-gradient(ellipse at 10% 50%, oklch(0.16 0.05 270 / 0.5) 0%, transparent 55%)',
          'radial-gradient(ellipse at 90% 20%, oklch(0.14 0.04 310 / 0.4) 0%, transparent 45%)',
          'radial-gradient(ellipse at 50% 100%, oklch(0.12 0.03 250 / 0.3) 0%, transparent 50%)',
          'oklch(0.09 0.01 260)',
        ].join(', '),
      }}
    >
      {/* Barra superior de stats */}
      <GlobalStatsStrip status={status} conectado={conectado} />

      {/* Layout principal 4 columnas — ocupa todo el espacio restante */}
      <div className="flex-1 flex gap-3 p-3 overflow-hidden">

        {/* Col Uralde */}
        <div className="flex-1 min-w-0">
          <GestoriaColumn
            gestoria={GESTORIA_CONFIG.uralde}
            empresas={EMPRESAS_POR_GESTORIA.uralde}
            status={status}
            breakdown={breakdown}
            eventosActivos={eventosActivos}
          />
        </div>

        {/* Divisor vertical */}
        <div className="w-px bg-white/5 flex-shrink-0" />

        {/* Col Gestoria A */}
        <div className="flex-[1.2] min-w-0">
          <GestoriaColumn
            gestoria={GESTORIA_CONFIG.gestoria_a}
            empresas={EMPRESAS_POR_GESTORIA.gestoria_a}
            status={status}
            breakdown={breakdown}
            eventosActivos={eventosActivos}
          />
        </div>

        {/* Divisor vertical */}
        <div className="w-px bg-white/5 flex-shrink-0" />

        {/* Col Javier */}
        <div className="flex-1 min-w-0">
          <GestoriaColumn
            gestoria={GESTORIA_CONFIG.javier}
            empresas={EMPRESAS_POR_GESTORIA.javier}
            status={status}
            breakdown={breakdown}
            eventosActivos={eventosActivos}
          />
        </div>

        {/* Divisor vertical */}
        <div className="w-px bg-white/5 flex-shrink-0" />

        {/* Col Pipeline Global — más ancha */}
        <div
          className="w-48 flex-shrink-0 rounded-xl p-3"
          style={{ background: 'oklch(0.095 0.01 260 / 0.6)' }}
        >
          <PipelineFlowDiagramVertical status={status} />
        </div>
      </div>
    </div>
  )
}
