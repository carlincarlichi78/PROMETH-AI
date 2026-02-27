import { ClipboardList } from 'lucide-react'
import { PageHeader } from '@/components/page-header'
import { EstadoVacio } from '@/components/estado-vacio'
import { Button } from '@/components/ui/button'

export default function PresupuestosPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        titulo="Presupuestos"
        descripcion="Crea y gestiona presupuestos para tus clientes"
      />

      <EstadoVacio
        titulo="Presupuestos"
        descripcion="Crea y gestiona presupuestos para tus clientes. Proximamente disponible."
        icono={ClipboardList}
        accion={
          <Button disabled variant="default">
            Nuevo presupuesto
          </Button>
        }
      />
    </div>
  )
}
