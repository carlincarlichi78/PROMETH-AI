import { Banknote } from 'lucide-react'
import { PageHeader } from '@/components/page-header'
import { EstadoVacio } from '@/components/estado-vacio'

export default function ConciliacionPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        titulo="Conciliacion Bancaria"
        descripcion="Comprobacion de movimientos entre extracto bancario y contabilidad"
      />
      <EstadoVacio
        titulo="Conciliacion Bancaria"
        descripcion="Proximamente — requiere importacion de extracto bancario. Esta funcionalidad estara disponible en la siguiente version del dashboard."
        icono={Banknote}
      />
    </div>
  )
}
