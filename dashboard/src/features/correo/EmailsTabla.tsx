import { useQuery } from '@tanstack/react-query'
import { listarEmails, EmailProcesado } from './api'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'

export function EmailsTabla({ empresaId }: { empresaId: number }) {
  const { data, isLoading } = useQuery({
    queryKey: ['correo-emails', empresaId],
    queryFn: () => listarEmails(empresaId),
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">
          Emails procesados
          {data?.total !== undefined && (
            <span className="ml-2 text-sm font-normal text-muted-foreground">
              ({data.total} total)
            </span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading && <p className="text-sm text-muted-foreground">Cargando...</p>}

        {data?.emails && data.emails.length > 0 ? (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Asunto</TableHead>
                <TableHead>Remitente</TableHead>
                <TableHead>Fecha</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead className="text-right">Documentos</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.emails.map((email: EmailProcesado) => (
                <TableRow key={email.id}>
                  <TableCell className="font-medium max-w-48 truncate">{email.asunto}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">{email.remitente}</TableCell>
                  <TableCell className="text-sm">
                    {new Date(email.fecha).toLocaleDateString('es-ES')}
                  </TableCell>
                  <TableCell>
                    <Badge variant={email.procesado ? 'default' : 'secondary'}>
                      {email.procesado ? 'Procesado' : 'Pendiente'}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right text-sm">{email.documentos_extraidos}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          !isLoading && (
            <p className="text-sm text-muted-foreground text-center py-6">
              No hay emails procesados aún.
            </p>
          )
        )}
      </CardContent>
    </Card>
  )
}
