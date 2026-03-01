// Configuracion: Usuarios de la empresa
import { useParams } from 'react-router-dom'
import { InvitarClienteDialog } from '@/features/empresa/invitar-cliente-dialog'

export default function UsuariosPage() {
  const { id } = useParams<{ id: string }>()
  const empresaId = Number(id) || 0

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Usuarios y Roles</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Gestión de accesos al portal cliente de esta empresa
          </p>
        </div>
        {empresaId > 0 && <InvitarClienteDialog empresaId={empresaId} />}
      </div>
      <p className="text-sm text-muted-foreground">
        Usa el botón <strong>Invitar cliente</strong> para enviar un enlace de acceso
        al portal a los clientes de esta empresa.
      </p>
    </div>
  )
}
