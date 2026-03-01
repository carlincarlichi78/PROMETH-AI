import { useParams } from 'react-router-dom'
import { CuentasCorreo } from './CuentasCorreo'
import { EmailsTabla } from './EmailsTabla'
import { ReglasClasificacion } from './ReglasClasificacion'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

export default function CorreoPage() {
  const { id } = useParams<{ id: string }>()
  const empresaId = Number(id)

  if (!empresaId) return null

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Módulo Correo</h1>
        <p className="text-sm text-muted-foreground">
          Gestiona cuentas IMAP y emails con facturas.
        </p>
      </div>

      <Tabs defaultValue="cuentas">
        <TabsList>
          <TabsTrigger value="cuentas">Cuentas IMAP</TabsTrigger>
          <TabsTrigger value="emails">Emails procesados</TabsTrigger>
          <TabsTrigger value="reglas">Reglas de clasificación</TabsTrigger>
        </TabsList>

        <TabsContent value="cuentas" className="mt-4">
          <CuentasCorreo empresaId={empresaId} />
        </TabsContent>

        <TabsContent value="emails" className="mt-4">
          <EmailsTabla empresaId={empresaId} />
        </TabsContent>

        <TabsContent value="reglas" className="mt-4">
          <ReglasClasificacion empresaId={empresaId} />
        </TabsContent>
      </Tabs>
    </div>
  )
}
