import { useState, useMemo } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { api } from '@/lib/api-client'
import { queryKeys } from '@/lib/query-keys'
import { formatearImporte, formatearFecha } from '@/lib/formatters'
import { PageHeader } from '@/components/page-header'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
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

const MESES = [
  { value: 'todos', label: 'Todos los meses' },
  { value: '01', label: 'Enero' },
  { value: '02', label: 'Febrero' },
  { value: '03', label: 'Marzo' },
  { value: '04', label: 'Abril' },
  { value: '05', label: 'Mayo' },
  { value: '06', label: 'Junio' },
  { value: '07', label: 'Julio' },
  { value: '08', label: 'Agosto' },
  { value: '09', label: 'Septiembre' },
  { value: '10', label: 'Octubre' },
  { value: '11', label: 'Noviembre' },
  { value: '12', label: 'Diciembre' },
]

export default function DiarioPage() {
  const { id } = useParams<{ id: string }>()
  const empresaId = Number(id)
  const [busqueda, setBusqueda] = useState('')
  const [mes, setMes] = useState('todos')
  const [expandidos, setExpandidos] = useState<Set<number>>(new Set())

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.contabilidad.diario(empresaId),
    queryFn: () => api.get<Asiento[]>(`/api/contabilidad/${empresaId}/asientos`),
  })

  const asientosFiltrados = useMemo(() => {
    if (!data) return []
    return data.filter((asiento) => {
      const coincideConcepto =
        !busqueda ||
        asiento.concepto?.toLowerCase().includes(busqueda.toLowerCase())
      const coincideMes =
        mes === 'todos' || (asiento.fecha && asiento.fecha.slice(5, 7) === mes)
      return coincideConcepto && coincideMes
    })
  }, [data, busqueda, mes])

  function toggleExpandido(id: number) {
    setExpandidos((prev) => {
      const nuevo = new Set(prev)
      if (nuevo.has(id)) {
        nuevo.delete(id)
      } else {
        nuevo.add(id)
      }
      return nuevo
    })
  }

  function sumDebe(asiento: Asiento) {
    return asiento.partidas.reduce((acc, p) => acc + p.debe, 0)
  }

  function sumHaber(asiento: Asiento) {
    return asiento.partidas.reduce((acc, p) => acc + p.haber, 0)
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader titulo="Libro Diario" descripcion="Cargando asientos..." />
        <div className="space-y-3">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        titulo="Libro Diario"
        descripcion={`${data?.length ?? 0} asientos registrados`}
      />

      <div className="flex gap-3 flex-wrap">
        <Input
          placeholder="Buscar por concepto..."
          value={busqueda}
          onChange={(e) => setBusqueda(e.target.value)}
          className="max-w-xs h-8 text-sm"
        />
        <Select value={mes} onValueChange={setMes}>
          <SelectTrigger className="w-44 h-8 text-sm">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {MESES.map((m) => (
              <SelectItem key={m.value} value={m.value} className="text-sm">
                {m.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <span className="text-sm text-muted-foreground self-center">
          {asientosFiltrados.length} resultado{asientosFiltrados.length !== 1 ? 's' : ''}
        </span>
      </div>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-8" />
                <TableHead>Num.</TableHead>
                <TableHead>Fecha</TableHead>
                <TableHead>Concepto</TableHead>
                <TableHead className="text-right">Debe</TableHead>
                <TableHead className="text-right">Haber</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {asientosFiltrados.length === 0 ? (
                <TableRow>
                  <TableCell
                    colSpan={6}
                    className="h-24 text-center text-sm text-muted-foreground"
                  >
                    Sin asientos para los filtros seleccionados
                  </TableCell>
                </TableRow>
              ) : (
                asientosFiltrados.map((asiento) => {
                  const estaExpandido = expandidos.has(asiento.id)
                  return (
                    <>
                      <TableRow
                        key={asiento.id}
                        className="cursor-pointer hover:bg-muted/50"
                        onClick={() => toggleExpandido(asiento.id)}
                      >
                        <TableCell className="w-8">
                          {estaExpandido ? (
                            <ChevronDown className="h-4 w-4 text-muted-foreground" />
                          ) : (
                            <ChevronRight className="h-4 w-4 text-muted-foreground" />
                          )}
                        </TableCell>
                        <TableCell className="text-sm font-mono">
                          {asiento.numero ?? '-'}
                        </TableCell>
                        <TableCell className="text-sm">
                          {formatearFecha(asiento.fecha)}
                        </TableCell>
                        <TableCell className="text-sm">
                          {asiento.concepto ?? '-'}
                        </TableCell>
                        <TableCell className="text-right text-sm font-mono">
                          {formatearImporte(sumDebe(asiento))}
                        </TableCell>
                        <TableCell className="text-right text-sm font-mono">
                          {formatearImporte(sumHaber(asiento))}
                        </TableCell>
                      </TableRow>
                      {estaExpandido && (
                        <TableRow key={`${asiento.id}-detalle`} className="bg-muted/30">
                          <TableCell colSpan={6} className="py-2 px-6">
                            <Table>
                              <TableHeader>
                                <TableRow>
                                  <TableHead className="h-8 text-xs">Subcuenta</TableHead>
                                  <TableHead className="h-8 text-xs">Concepto</TableHead>
                                  <TableHead className="h-8 text-xs text-right">Debe</TableHead>
                                  <TableHead className="h-8 text-xs text-right">Haber</TableHead>
                                </TableRow>
                              </TableHeader>
                              <TableBody>
                                {asiento.partidas.map((partida) => (
                                  <TableRow key={partida.id}>
                                    <TableCell className="text-xs font-mono py-1.5">
                                      {partida.subcuenta}
                                    </TableCell>
                                    <TableCell className="text-xs py-1.5">
                                      {partida.concepto ?? '-'}
                                    </TableCell>
                                    <TableCell className="text-xs text-right font-mono py-1.5">
                                      {partida.debe > 0 ? formatearImporte(partida.debe) : '-'}
                                    </TableCell>
                                    <TableCell className="text-xs text-right font-mono py-1.5">
                                      {partida.haber > 0 ? formatearImporte(partida.haber) : '-'}
                                    </TableCell>
                                  </TableRow>
                                ))}
                              </TableBody>
                            </Table>
                          </TableCell>
                        </TableRow>
                      )}
                    </>
                  )
                })
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
