// dashboard/src/features/pipeline/pipeline-live-page.tsx
import { useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '@/context/AuthContext'
import { usePipelineWebSocket } from './hooks/usePipelineWebSocket'
import { usePipelineSyncStatus } from './hooks/usePipelineSyncStatus'
import { GlobalStatsStrip } from './components/GlobalStatsStrip'
import { PipelineFlowDiagram } from './components/PipelineFlowDiagram'
import { FuentesPanel } from './components/FuentesPanel'
import { BreakdownPanel } from './components/BreakdownPanel'
import { SubirDocumentos } from './components/SubirDocumentos'

interface Empresa { id: number; nombre: string }

export default function PipelineLivePage() {
  const { token } = useAuth()
  const qc = useQueryClient()
  const [empresaSeleccionada, setEmpresaSeleccionada] = useState<number | undefined>()

  const { eventos, particulas, conectado, eliminarParticula, contadores_fuente } =
    usePipelineWebSocket(empresaSeleccionada)

  const { status, breakdown } = usePipelineSyncStatus(empresaSeleccionada)

  const { data: empresas = [] } = useQuery<Empresa[]>({
    queryKey: ['empresas-lista'],
    queryFn: async () => {
      const r = await fetch(`/api/empresas`, { headers: { Authorization: `Bearer ${token}` } })
      if (!r.ok) return []
      const data = await r.json()
      return Array.isArray(data) ? data : (data.items ?? [])
    },
    enabled: !!token,
    staleTime: 5 * 60_000,
  })

  // Invalidar breakdown cuando llega un nuevo PDF por WS
  const prevContadoresRef = useRef({ ...contadores_fuente })
  const totalWS = contadores_fuente.correo + contadores_fuente.manual + contadores_fuente.watcher
  const prevTotal = prevContadoresRef.current.correo + prevContadoresRef.current.manual + prevContadoresRef.current.watcher
  if (totalWS !== prevTotal) {
    qc.invalidateQueries({ queryKey: ['pipeline-breakdown'] })
    prevContadoresRef.current = { ...contadores_fuente }
  }

  return (
    <div
      className="flex flex-col h-full min-h-screen"
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

      {/* Layout principal 3 columnas */}
      <div className="flex-1 flex gap-0 overflow-hidden">

        {/* Col izquierda — Fuentes y empresas */}
        <div
          className="w-56 flex-shrink-0 border-r border-white/5 p-4 overflow-y-auto"
          style={{ background: 'oklch(0.095 0.01 260 / 0.8)' }}
        >
          <FuentesPanel
            breakdown={breakdown}
            contadores_ws={contadores_fuente}
            empresaSeleccionada={empresaSeleccionada}
            onSeleccionar={setEmpresaSeleccionada}
          />
        </div>

        {/* Col central — Diagrama de flujo */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Título */}
          <div className="flex items-center gap-3 px-6 pt-4 pb-1 flex-shrink-0">
            <h1 className="text-base font-semibold text-foreground">Pipeline en Vivo</h1>
            {empresaSeleccionada && (
              <span className="text-xs text-amber-400">
                {empresas.find(e => e.id === empresaSeleccionada)?.nombre ?? `Empresa ${empresaSeleccionada}`}
              </span>
            )}
            <span className="text-xs text-muted-foreground/50 ml-auto hidden lg:inline">
              Flujo de documentos en tiempo real
            </span>
          </div>

          {/* Diagrama — flex-1 */}
          <div className="flex-1 px-4 py-2 overflow-hidden">
            <PipelineFlowDiagram
              status={status}
              particulas={particulas}
              onParticulaCompleta={eliminarParticula}
              empresaSeleccionada={empresaSeleccionada}
            />
          </div>

          {/* Upload manual — parte inferior col central */}
          <div className="flex-shrink-0 border-t border-white/5">
            <SubirDocumentos empresaId={empresaSeleccionada} empresas={empresas} />
          </div>
        </div>

        {/* Col derecha — Breakdown y actividad */}
        <div
          className="w-64 flex-shrink-0 border-l border-white/5 p-4 overflow-y-auto"
          style={{ background: 'oklch(0.095 0.01 260 / 0.8)' }}
        >
          <BreakdownPanel
            breakdown={breakdown}
            eventos={eventos}
            empresaSeleccionada={empresaSeleccionada}
          />
        </div>
      </div>
    </div>
  )
}
