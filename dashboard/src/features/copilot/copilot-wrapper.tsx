// CopilotWrapper — integra CopilotPanel en AppShell via Sheet
// Requiere merge con Stream A para que Sheet y los stores estén disponibles
import { lazy, Suspense } from 'react'
import { useUIStore } from '@/stores/ui-store'
import { useEmpresaStore } from '@/stores/empresa-store'
import { Sheet, SheetContent } from '@/components/ui/sheet'

const CopilotPanel = lazy(() => import('./copilot-panel'))

export function CopilotWrapper() {
  const copilotAbierto = useUIStore((s) => s.copilotAbierto)
  const toggleCopilot = useUIStore((s) => s.toggleCopilot)
  const empresaActiva = useEmpresaStore((s) => s.empresaActiva)

  if (!empresaActiva) return null

  return (
    <Sheet open={copilotAbierto} onOpenChange={toggleCopilot}>
      <SheetContent side="right" className="w-[400px] p-0">
        <Suspense fallback={<div className="p-4 text-sm text-gray-500">Cargando copiloto...</div>}>
          <CopilotPanel empresaId={empresaActiva.id} />
        </Suspense>
      </SheetContent>
    </Sheet>
  )
}
