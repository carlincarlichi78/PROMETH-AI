// dashboard/src/features/pipeline/pipeline-live-page.tsx
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '@/context/AuthContext'
import { usePipelineWebSocket } from './hooks/usePipelineWebSocket'
import { usePipelineSyncStatus } from './hooks/usePipelineSyncStatus'
import { GlobalStatsStrip } from './components/GlobalStatsStrip'
import { EmpresaBadges } from './components/EmpresaBadges'
import { PipelineFlowDiagram } from './components/PipelineFlowDiagram'
import { LiveEventFeed } from './components/LiveEventFeed'
import { SubirDocumentos } from './components/SubirDocumentos'

interface Empresa { id: number; nombre: string }

export default function PipelineLivePage() {
  const { token } = useAuth()
  const [empresaSeleccionada, setEmpresaSeleccionada] = useState<number | undefined>()

  // WebSocket
  const { eventos, particulas, conectado, eliminarParticula } = usePipelineWebSocket(empresaSeleccionada)

  // Polling de contadores
  const { status } = usePipelineSyncStatus(empresaSeleccionada)

  // Lista de empresas (para los chips)
  const { data: empresas = [] } = useQuery<Empresa[]>({
    queryKey: ['empresas-lista'],
    queryFn: async () => {
      const r = await fetch(`/api/empresas`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!r.ok) return []
      const data = await r.json()
      // La API puede devolver {items: [...]} o directamente un array
      return Array.isArray(data) ? data : (data.items ?? [])
    },
    enabled: !!token,
    staleTime: 5 * 60_000,
  })

  return (
    <div
      className="flex flex-col h-full min-h-screen"
      style={{
        background: 'radial-gradient(ellipse at 20% 50%, oklch(0.18 0.04 260 / 0.4) 0%, transparent 60%), radial-gradient(ellipse at 80% 20%, oklch(0.15 0.04 300 / 0.3) 0%, transparent 50%), oklch(0.10 0.01 260)',
      }}
    >
      {/* Título */}
      <div className="flex items-center gap-3 px-6 pt-6 pb-2">
        <h1 className="text-xl font-semibold text-foreground">Pipeline en Vivo</h1>
        <span className="text-sm text-muted-foreground">Flujo de documentos en tiempo real</span>
      </div>

      {/* KPIs */}
      <GlobalStatsStrip status={status} conectado={conectado} />

      {/* Chips empresa */}
      <EmpresaBadges
        empresas={empresas}
        seleccionada={empresaSeleccionada}
        onSeleccionar={setEmpresaSeleccionada}
      />

      {/* Diagrama principal — flex-1 para ocupar espacio disponible */}
      <div className="flex-1 px-4 py-6">
        <PipelineFlowDiagram
          status={status}
          particulas={particulas}
          onParticulaCompleta={eliminarParticula}
          empresaSeleccionada={empresaSeleccionada}
        />
      </div>

      {/* Zona de upload manual */}
      <SubirDocumentos empresaId={empresaSeleccionada} empresas={empresas} />

      {/* Live feed */}
      <LiveEventFeed eventos={eventos} empresaSeleccionada={empresaSeleccionada} />
    </div>
  )
}
