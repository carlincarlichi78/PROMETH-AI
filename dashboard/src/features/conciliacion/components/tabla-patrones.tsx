/**
 * Tabla CRUD de patrones de conciliación aprendidos.
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Trash2, Loader2 } from 'lucide-react'
import { conciliacionApi } from '../api'

interface TablaPatronesProps {
  empresaId: number
}

function badgeExito(frecuencia: number): string {
  if (frecuencia >= 5) return 'bg-green-100 text-green-800'
  if (frecuencia >= 2) return 'bg-yellow-100 text-yellow-800'
  return 'bg-gray-100 text-gray-800'
}

export function TablaPatrones({ empresaId }: TablaPatronesProps) {
  const qc = useQueryClient()

  const { data: patrones = [], isLoading } = useQuery({
    queryKey: ['patrones', empresaId],
    queryFn: () => conciliacionApi.listarPatrones(empresaId),
    enabled: empresaId > 0,
  })

  const eliminar = useMutation({
    mutationFn: (patronId: number) => conciliacionApi.eliminarPatron(empresaId, patronId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['patrones', empresaId] })
    },
  })

  if (isLoading) {
    return (
      <div className="flex justify-center p-8">
        <Loader2 className="animate-spin" />
      </div>
    )
  }

  if (patrones.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        No hay patrones aprendidos todavía.
        <br />
        Confirmando matches manualmente se irán creando automáticamente.
      </div>
    )
  }

  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Patrón texto</TableHead>
            <TableHead>NIF proveedor</TableHead>
            <TableHead>Rango importe</TableHead>
            <TableHead className="text-center">Confirmaciones</TableHead>
            <TableHead>Última confirmación</TableHead>
            <TableHead className="w-16" />
          </TableRow>
        </TableHeader>
        <TableBody>
          {patrones.map(p => (
            <TableRow key={p.id}>
              <TableCell className="font-mono text-xs max-w-xs truncate">
                {p.patron_limpio ?? p.patron_texto}
              </TableCell>
              <TableCell>
                {p.nif_proveedor ? (
                  <Badge variant="outline">{p.nif_proveedor}</Badge>
                ) : (
                  <span className="text-muted-foreground">—</span>
                )}
              </TableCell>
              <TableCell>
                <Badge variant="secondary">{p.rango_importe_aprox}</Badge>
              </TableCell>
              <TableCell className="text-center">
                <Badge className={badgeExito(p.frecuencia_exito)}>{p.frecuencia_exito}</Badge>
              </TableCell>
              <TableCell className="text-sm text-muted-foreground">
                {p.ultima_confirmacion ?? '—'}
              </TableCell>
              <TableCell>
                <Button
                  size="sm"
                  variant="ghost"
                  className="text-red-500 hover:text-red-700 hover:bg-red-50"
                  disabled={eliminar.isPending}
                  onClick={() => eliminar.mutate(p.id)}
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
