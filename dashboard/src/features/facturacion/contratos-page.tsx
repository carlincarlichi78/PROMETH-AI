import { Repeat } from 'lucide-react'
import { PageHeader } from '@/components/page-header'
import { EstadoVacio } from '@/components/estado-vacio'

export default function ContratosPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        titulo="Contratos Recurrentes"
        descripcion="Gestion de servicios y facturacion periodica"
      />

      <EstadoVacio
        titulo="Contratos Recurrentes"
        descripcion="Gestiona servicios y facturacion periodica. Proximamente disponible."
        icono={Repeat}
      />
    </div>
  )
}
