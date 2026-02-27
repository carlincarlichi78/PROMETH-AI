import { useState, useMemo } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { FileDown, TrendingDown, CheckCircle, AlertCircle } from 'lucide-react'
import { api } from '@/lib/api-client'
import { queryKeys } from '@/lib/query-keys'
import { formatearImporte, formatearFecha } from '@/lib/formatters'
import { KPICard } from '@/components/charts/kpi-card'
import { DataTable, type ColumnaTabla } from '@/components/data-table/data-table'
import { PageHeader } from '@/components/page-header'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { Factura } from '@/types'

type FiltroEstado = 'todas' | 'pagadas' | 'pendientes'

const COLUMNAS: ColumnaTabla<Factura>[] = [
  {
    key: 'numero_factura',
    header: 'Numero',
    render: (f) => (
      <span className="font-mono text-sm">{f.numero_factura ?? '-'}</span>
    ),
    sortable: true,
    sortFn: (a, b) => (a.numero_factura ?? '').localeCompare(b.numero_factura ?? ''),
  },
  {
    key: 'fecha_factura',
    header: 'Fecha',
    render: (f) => formatearFecha(f.fecha_factura),
    sortable: true,
    sortFn: (a, b) => (a.fecha_factura ?? '').localeCompare(b.fecha_factura ?? ''),
  },
  {
    key: 'nombre_emisor',
    header: 'Proveedor',
    render: (f) => <span className="font-medium">{f.nombre_emisor ?? '-'}</span>,
    sortable: true,
    sortFn: (a, b) => (a.nombre_emisor ?? '').localeCompare(b.nombre_emisor ?? ''),
  },
  {
    key: 'tipo',
    header: 'Tipo',
    render: (f) => (
      <Badge variant="outline" className="text-xs font-mono">
        {f.tipo}
      </Badge>
    ),
  },
  {
    key: 'base_imponible',
    header: 'Base imponible',
    render: (f) => (
      <span className="text-right block">{formatearImporte(f.base_imponible)}</span>
    ),
    sortable: true,
    sortFn: (a, b) => (a.base_imponible ?? 0) - (b.base_imponible ?? 0),
    className: 'text-right',
  },
  {
    key: 'iva_importe',
    header: 'IVA',
    render: (f) => (
      <span className="text-right block text-muted-foreground">
        {formatearImporte(f.iva_importe)}
      </span>
    ),
    className: 'text-right',
  },
  {
    key: 'total',
    header: 'Total',
    render: (f) => (
      <span className="text-right block font-semibold">{formatearImporte(f.total)}</span>
    ),
    sortable: true,
    sortFn: (a, b) => (a.total ?? 0) - (b.total ?? 0),
    className: 'text-right',
  },
  {
    key: 'pagada',
    header: 'Estado',
    render: (f) =>
      f.pagada ? (
        <Badge variant="default" className="bg-green-600 hover:bg-green-700">
          Pagada
        </Badge>
      ) : (
        <Badge variant="outline" className="text-red-600 border-red-400">
          Pendiente pago
        </Badge>
      ),
  },
]

export default function RecibidasPage() {
  const { id } = useParams<{ id: string }>()
  const empresaId = Number(id)

  const [busqueda, setBusqueda] = useState('')
  const [filtroEstado, setFiltroEstado] = useState<FiltroEstado>('todas')

  const { data: todasFacturas = [], isLoading } = useQuery({
    queryKey: queryKeys.contabilidad.facturas(empresaId),
    queryFn: () => api.get<Factura[]>(`/api/contabilidad/${empresaId}/facturas`),
    enabled: !isNaN(empresaId),
  })

  const facturas = useMemo(
    () => todasFacturas.filter((f) => f.tipo !== 'FC'),
    [todasFacturas]
  )

  const facturasFiltradas = useMemo(() => {
    let resultado = facturas
    if (filtroEstado === 'pagadas') resultado = resultado.filter((f) => f.pagada)
    if (filtroEstado === 'pendientes') resultado = resultado.filter((f) => !f.pagada)
    return resultado
  }, [facturas, filtroEstado])

  const importeTotal = useMemo(
    () => facturas.reduce((acc, f) => acc + (f.total ?? 0), 0),
    [facturas]
  )
  const pagadas = useMemo(() => facturas.filter((f) => f.pagada), [facturas])
  const pendientesPago = useMemo(
    () => facturas.filter((f) => !f.pagada).reduce((acc, f) => acc + (f.total ?? 0), 0),
    [facturas]
  )

  return (
    <div className="space-y-6">
      <PageHeader
        titulo="Facturas Recibidas"
        descripcion="Facturas de compra recibidas de proveedores"
      />

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          titulo="Total recibidas"
          valor={String(facturas.length)}
          icono={FileDown}
          cargando={isLoading}
        />
        <KPICard
          titulo="Importe total"
          valor={formatearImporte(importeTotal)}
          icono={TrendingDown}
          cargando={isLoading}
          invertirColor
        />
        <KPICard
          titulo="Pagadas"
          valor={String(pagadas.length)}
          descripcion={`${formatearImporte(pagadas.reduce((a, f) => a + (f.total ?? 0), 0))}`}
          icono={CheckCircle}
          cargando={isLoading}
        />
        <KPICard
          titulo="Pendiente pago"
          valor={formatearImporte(pendientesPago)}
          icono={AlertCircle}
          cargando={isLoading}
          invertirColor
        />
      </div>

      <div className="flex items-center gap-3">
        <Input
          placeholder="Buscar por proveedor..."
          value={busqueda}
          onChange={(e) => setBusqueda(e.target.value)}
          className="max-w-xs h-9"
        />
        <Select
          value={filtroEstado}
          onValueChange={(v) => setFiltroEstado(v as FiltroEstado)}
        >
          <SelectTrigger className="w-40 h-9">
            <SelectValue placeholder="Estado" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="todas">Todas</SelectItem>
            <SelectItem value="pagadas">Pagadas</SelectItem>
            <SelectItem value="pendientes">Pendientes</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <DataTable
        datos={facturasFiltradas}
        columnas={COLUMNAS}
        cargando={isLoading}
        filtroBusqueda={(f, termino) =>
          (f.nombre_emisor ?? '').toLowerCase().includes(termino.toLowerCase()) ||
          (f.numero_factura ?? '').toLowerCase().includes(termino.toLowerCase())
        }
        busqueda={busqueda.length > 0}
        vacio="No hay facturas recibidas"
      />
    </div>
  )
}
