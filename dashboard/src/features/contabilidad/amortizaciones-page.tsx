import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Package, TrendingDown, BarChart2, DollarSign } from 'lucide-react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { api } from '@/lib/api-client'
import { queryKeys } from '@/lib/query-keys'
import { formatearImporte, formatearFecha } from '@/lib/formatters'
import { PageHeader } from '@/components/page-header'
import { KPICard } from '@/components/charts/kpi-card'
import { ChartCard } from '@/components/charts/chart-card'
import { DataTable } from '@/components/data-table/data-table'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import type { ColumnaTabla } from '@/components/data-table/data-table'
import type { ActivoFijo } from '@/types'

const columnas: ColumnaTabla<ActivoFijo>[] = [
  {
    key: 'descripcion',
    header: 'Descripcion',
    render: (item) => <span className="text-sm font-medium">{item.descripcion}</span>,
  },
  {
    key: 'tipo_bien',
    header: 'Tipo',
    render: (item) => (
      <Badge variant="outline" className="text-xs">
        {item.tipo_bien ?? 'General'}
      </Badge>
    ),
  },
  {
    key: 'valor_adquisicion',
    header: 'Valor adquisicion',
    render: (item) => (
      <span className="font-mono text-sm">{formatearImporte(item.valor_adquisicion)}</span>
    ),
    className: 'text-right',
    sortable: true,
    sortFn: (a, b) => a.valor_adquisicion - b.valor_adquisicion,
  },
  {
    key: 'amortizacion_acumulada',
    header: 'Amort. acumulada',
    render: (item) => (
      <span className="font-mono text-sm text-red-600 dark:text-red-400">
        {formatearImporte(item.amortizacion_acumulada)}
      </span>
    ),
    className: 'text-right',
    sortable: true,
    sortFn: (a, b) => a.amortizacion_acumulada - b.amortizacion_acumulada,
  },
  {
    key: 'valor_neto',
    header: 'Valor neto',
    render: (item) => {
      const neto = item.valor_adquisicion - item.amortizacion_acumulada
      return (
        <span className="font-mono text-sm font-semibold text-green-600 dark:text-green-400">
          {formatearImporte(neto)}
        </span>
      )
    },
    className: 'text-right',
    sortable: true,
    sortFn: (a, b) =>
      a.valor_adquisicion -
      a.amortizacion_acumulada -
      (b.valor_adquisicion - b.amortizacion_acumulada),
  },
  {
    key: 'fecha_adquisicion',
    header: 'Fecha adquisicion',
    render: (item) => (
      <span className="text-sm">{formatearFecha(item.fecha_adquisicion)}</span>
    ),
  },
  {
    key: 'activo',
    header: 'Estado',
    render: (item) => (
      <Badge variant={item.activo ? 'default' : 'secondary'} className="text-xs">
        {item.activo ? 'Activo' : 'Baja'}
      </Badge>
    ),
  },
]

export default function AmortizacionesPage() {
  const { id } = useParams<{ id: string }>()
  const empresaId = Number(id)

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.contabilidad.activos(empresaId),
    queryFn: () => api.get<ActivoFijo[]>(`/api/contabilidad/${empresaId}/activos`),
  })

  const activos = data ?? []
  const totalActivos = activos.length
  const valorBruto = activos.reduce((acc, a) => acc + a.valor_adquisicion, 0)
  const amortAcumulada = activos.reduce((acc, a) => acc + a.amortizacion_acumulada, 0)
  const valorNeto = valorBruto - amortAcumulada

  // Top 10 por valor neto para el grafico
  const datosGrafico = activos
    .map((a) => ({
      nombre:
        a.descripcion.length > 18 ? a.descripcion.slice(0, 18) + '...' : a.descripcion,
      valor_neto: a.valor_adquisicion - a.amortizacion_acumulada,
    }))
    .sort((a, b) => b.valor_neto - a.valor_neto)
    .slice(0, 10)

  return (
    <div className="space-y-6">
      <PageHeader
        titulo="Activos Fijos y Amortizaciones"
        descripcion="Inventario de bienes y dotacion por amortizacion del ejercicio"
      />

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          titulo="Total activos"
          valor={String(totalActivos)}
          icono={Package}
          descripcion="Bienes en inventario"
          cargando={isLoading}
        />
        <KPICard
          titulo="Valor bruto"
          valor={formatearImporte(valorBruto)}
          icono={BarChart2}
          descripcion="Precio de adquisicion total"
          cargando={isLoading}
        />
        <KPICard
          titulo="Amort. acumulada"
          valor={formatearImporte(amortAcumulada)}
          icono={TrendingDown}
          descripcion="Depreciacion total registrada"
          cargando={isLoading}
          invertirColor
        />
        <KPICard
          titulo="Valor neto contable"
          valor={formatearImporte(valorNeto)}
          icono={DollarSign}
          descripcion="Valor bruto menos amortizacion"
          cargando={isLoading}
        />
      </div>

      <ChartCard
        titulo="Top 10 activos por valor neto"
        cargando={isLoading}
        altura={280}
      >
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            layout="vertical"
            data={datosGrafico}
            margin={{ top: 4, right: 16, left: 0, bottom: 4 }}
          >
            <CartesianGrid strokeDasharray="3 3" horizontal={false} />
            <XAxis
              type="number"
              tick={{ fontSize: 11 }}
              tickFormatter={(v) => formatearImporte(v)}
            />
            <YAxis type="category" dataKey="nombre" tick={{ fontSize: 11 }} width={140} />
            <Tooltip formatter={(value: number | undefined) => formatearImporte(value)} />
            <Bar dataKey="valor_neto" name="Valor neto" fill="#3b82f6" radius={[0, 3, 3, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      <Card>
        <CardContent className="p-0">
          <DataTable
            datos={activos}
            columnas={columnas}
            cargando={isLoading}
            busqueda
            filtroBusqueda={(item, termino) =>
              item.descripcion.toLowerCase().includes(termino.toLowerCase()) ||
              (item.tipo_bien ?? '').toLowerCase().includes(termino.toLowerCase())
            }
            filasPorPagina={20}
            vacio="Sin activos fijos registrados"
          />
        </CardContent>
      </Card>
    </div>
  )
}
