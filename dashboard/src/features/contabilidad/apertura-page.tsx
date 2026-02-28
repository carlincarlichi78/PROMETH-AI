import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { BookOpen, Info } from 'lucide-react'
import { api } from '@/lib/api-client'
import { ApiError } from '@/lib/api-client'
import { formatearFecha, formatearImporte } from '@/lib/formatters'
import { PageHeader } from '@/components/page-header'
import { EstadoVacio } from '@/components/estado-vacio'
import { Card, CardContent } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Skeleton } from '@/components/ui/skeleton'
import type { Asiento } from '@/types'

export default function AperturaPage() {
  const { id } = useParams<{ id: string }>()
  const empresaId = Number(id)

  const { data, isLoading } = useQuery({
    queryKey: ['contabilidad', empresaId, 'asientos-apertura'],
    queryFn: async () => {
      try {
        const todos = await api.get<Asiento[]>(`/api/contabilidad/${empresaId}/diario`)
        return todos.filter(
          (a) =>
            a.concepto?.toLowerCase().includes('apertura') ||
            a.origen?.toLowerCase().includes('apertura')
        )
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) return []
        throw err
      }
    },
  })

  const asientosApertura = data ?? []

  return (
    <div className="space-y-6">
      <PageHeader
        titulo="Apertura de Ejercicio"
        descripcion="Asientos de apertura — inicio del nuevo periodo contable"
      />

      <div className="rounded-lg border bg-blue-50 dark:bg-blue-950/20 border-blue-200 dark:border-blue-800 p-4">
        <div className="flex gap-3">
          <Info className="h-4 w-4 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0" />
          <p className="text-sm text-blue-800 dark:text-blue-300">
            Los asientos de apertura se generan automaticamente tras el cierre del ejercicio
            anterior. Reflejan los saldos iniciales de las cuentas de balance (grupos 1 a 5)
            al comienzo del ejercicio.
          </p>
        </div>
      </div>

      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-6 space-y-3">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : asientosApertura.length === 0 ? (
            <div className="py-4">
              <EstadoVacio
                titulo="Sin asientos de apertura"
                descripcion="Cuando realices el cierre del ejercicio anterior, los asientos de apertura se generaran automaticamente y apareceran aqui."
                icono={BookOpen}
              />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Num.</TableHead>
                  <TableHead>Fecha</TableHead>
                  <TableHead>Concepto</TableHead>
                  <TableHead className="text-right">Debe total</TableHead>
                  <TableHead className="text-right">Haber total</TableHead>
                  <TableHead className="text-right">Partidas</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {asientosApertura.map((asiento) => {
                  const debe = asiento.partidas.reduce((acc, p) => acc + p.debe, 0)
                  const haber = asiento.partidas.reduce((acc, p) => acc + p.haber, 0)
                  return (
                    <TableRow key={asiento.id}>
                      <TableCell className="font-mono text-sm">
                        {asiento.numero ?? '-'}
                      </TableCell>
                      <TableCell className="text-sm">
                        {formatearFecha(asiento.fecha)}
                      </TableCell>
                      <TableCell className="text-sm">
                        {asiento.concepto ?? '-'}
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm">
                        {formatearImporte(debe)}
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm">
                        {formatearImporte(haber)}
                      </TableCell>
                      <TableCell className="text-right text-sm text-muted-foreground">
                        {asiento.partidas.length}
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
