import { useEmpresaStore } from '@/stores/empresa-store'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { PanelSugerencias } from './components/panel-sugerencias'
import { TablaPatrones } from './components/tabla-patrones'
import { VistaPendientes } from './components/vista-pendientes'

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
          <TabsTrigger value="patrones">Patrones</TabsTrigger>
        </TabsList>

        <TabsContent value="pendientes" className="mt-4">
          <VistaPendientes />
        </TabsContent>

        <TabsContent value="sugerencias" className="mt-4">
          <PanelSugerencias empresaId={empresaId} />
        </TabsContent>

        <TabsContent value="revision" className="mt-4">
          <div className="py-12 text-center text-muted-foreground border rounded-lg">
            Movimientos marcados para revisión manual — próxima iteración.
          </div>
        </TabsContent>

        <TabsContent value="conciliados" className="mt-4">
          <div className="py-12 text-center text-muted-foreground border rounded-lg">
            Historial de movimientos conciliados — próxima iteración.
          </div>
        </TabsContent>

        <TabsContent value="patrones" className="mt-4">
          <TablaPatrones empresaId={empresaId} />
        </TabsContent>
      </Tabs>
    </div>
  )
}
