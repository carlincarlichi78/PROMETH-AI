import { useState, useCallback } from 'react'
import { useEmpresaStore } from '@/stores/empresa-store'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { PanelSugerencias } from './components/panel-sugerencias'
import { TablaPatrones } from './components/tabla-patrones'
import { TablaMovimientos } from './components/tabla-movimientos'
import { VistaPendientes } from './components/vista-pendientes'
import { FilterBar, type FiltrosMovimientos } from './components/filter-bar'
import { useMovimientos } from './api'

const FILTROS_VACIOS: FiltrosMovimientos = { q: '', fechaDesde: '', fechaHasta: '' }

/** Wrapper que carga y renderiza movimientos filtrados por estado, con FilterBar */
function TabMovimientos({
  empresaId,
  estado,
  mostrarDocumento = false,
}: {
  empresaId: number
  estado: string
  mostrarDocumento?: boolean
}) {
  const [filtros, setFiltros] = useState<FiltrosMovimientos>(FILTROS_VACIOS)
  const onFiltrosChange = useCallback((f: FiltrosMovimientos) => setFiltros(f), [])

  const { data: paginados, isLoading } = useMovimientos(empresaId, {
    estado,
    q: filtros.q || undefined,
    fechaDesde: filtros.fechaDesde || undefined,
    fechaHasta: filtros.fechaHasta || undefined,
  })
  return (
    <div className="space-y-3">
      <FilterBar onChange={onFiltrosChange} />
      <TablaMovimientos
        movimientos={paginados?.items ?? []}
        isLoading={isLoading}
        mostrarDocumento={mostrarDocumento}
      />
    </div>
  )
}

export default function ConciliacionPage() {
  const empresaActiva = useEmpresaStore((s) => s.empresaActiva)
  const empresaId = empresaActiva?.id ?? 0

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-2xl font-semibold">Conciliación Bancaria</h1>

      <Tabs defaultValue="pendientes">
        <TabsList>
          <TabsTrigger value="pendientes">Pendientes</TabsTrigger>
          <TabsTrigger value="sugerencias">Sugerencias</TabsTrigger>
          <TabsTrigger value="revision">Revisión</TabsTrigger>
          <TabsTrigger value="conciliados">Conciliados</TabsTrigger>
          <TabsTrigger value="manuales">Asiento Directo</TabsTrigger>
          <TabsTrigger value="patrones">Patrones</TabsTrigger>
        </TabsList>

        <TabsContent value="pendientes" className="mt-4">
          <VistaPendientes />
        </TabsContent>

        <TabsContent value="sugerencias" className="mt-4">
          <PanelSugerencias empresaId={empresaId} />
        </TabsContent>

        <TabsContent value="revision" className="mt-4">
          <TabMovimientos
            empresaId={empresaId}
            estado="revision"
          />
        </TabsContent>

        <TabsContent value="conciliados" className="mt-4">
          <TabMovimientos
            empresaId={empresaId}
            estado="conciliado"
            mostrarDocumento
          />
        </TabsContent>

        <TabsContent value="manuales" className="mt-4">
          <TabMovimientos
            empresaId={empresaId}
            estado="manual"
            mostrarDocumento
          />
        </TabsContent>

        <TabsContent value="patrones" className="mt-4">
          <TablaPatrones empresaId={empresaId} />
        </TabsContent>
      </Tabs>
    </div>
  )
}
