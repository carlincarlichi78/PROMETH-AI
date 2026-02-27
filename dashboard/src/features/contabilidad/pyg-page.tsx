import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { TrendingUp, TrendingDown, DollarSign } from 'lucide-react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { api } from '@/lib/api-client'
import { queryKeys } from '@/lib/query-keys'
import { formatearImporte } from '@/lib/formatters'
import { PageHeader } from '@/components/page-header'
import { KPICard } from '@/components/charts/kpi-card'
import { ChartCard } from '@/components/charts/chart-card'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import type { PyG } from '@/types'

export default function PygPage() {
  const { id } = useParams<{ id: string }>()
  const empresaId = Number(id)

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.contabilidad.pyg(empresaId),
    queryFn: () => api.get<PyG>(`/api/contabilidad/${empresaId}/pyg`),
  })

  // Construir datos para el grafico comparativo (top 8 gastos)
  const datosGrafico = (() => {
    if (!data) return []
    const gastosOrdenados = Object.entries(data.detalle_gastos)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 8)
    return gastosOrdenados.map(([nombre, gastos]) => ({
      nombre: nombre.length > 20 ? nombre.slice(0, 20) + '...' : nombre,
      gastos,
      ingresos: data.detalle_ingresos[nombre] ?? 0,
    }))
  })()

  const esPositivo = (data?.resultado ?? 0) >= 0

  return (
    <div className="space-y-6">
      <PageHeader
        titulo="Cuenta de Resultados (PyG)"
        descripcion="Perdidas y ganancias del ejercicio — ingresos, gastos y resultado"
      />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <KPICard
          titulo="Ingresos totales"
          valor={formatearImporte(data?.ingresos)}
          icono={TrendingUp}
          descripcion="Total ventas y otros ingresos"
          cargando={isLoading}
        />
        <KPICard
          titulo="Gastos totales"
          valor={formatearImporte(data?.gastos)}
          icono={TrendingDown}
          descripcion="Total compras y gastos de explotacion"
          cargando={isLoading}
          invertirColor
        />
        <KPICard
          titulo="Resultado del ejercicio"
          valor={formatearImporte(data?.resultado)}
          icono={DollarSign}
          descripcion={esPositivo ? 'Beneficio' : 'Perdida'}
          cargando={isLoading}
        />
      </div>

      <ChartCard
        titulo="Comparativa gastos por subcuenta (top 8)"
        cargando={isLoading}
        altura={300}
      >
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={datosGrafico} margin={{ top: 4, right: 16, left: 0, bottom: 40 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="nombre"
              tick={{ fontSize: 11 }}
              angle={-35}
              textAnchor="end"
              interval={0}
            />
            <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => formatearImporte(v)} width={90} />
            <Tooltip formatter={(value: number | undefined) => formatearImporte(value)} />
            <Legend />
            <Bar dataKey="ingresos" name="Ingresos" fill="#22c55e" radius={[3, 3, 0, 0]} />
            <Bar dataKey="gastos" name="Gastos" fill="#ef4444" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Detalle de ingresos</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Subcuenta</TableHead>
                  <TableHead className="text-right">Importe</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data
                  ? Object.entries(data.detalle_ingresos)
                      .sort(([, a], [, b]) => b - a)
                      .map(([nombre, importe]) => (
                        <TableRow key={nombre}>
                          <TableCell className="text-sm">{nombre}</TableCell>
                          <TableCell className="text-right text-sm text-green-600 dark:text-green-400">
                            {formatearImporte(importe)}
                          </TableCell>
                        </TableRow>
                      ))
                  : null}
                {data && Object.keys(data.detalle_ingresos).length === 0 && (
                  <TableRow>
                    <TableCell colSpan={2} className="text-center text-sm text-muted-foreground py-6">
                      Sin datos de ingresos
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Detalle de gastos</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Subcuenta</TableHead>
                  <TableHead className="text-right">Importe</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data
                  ? Object.entries(data.detalle_gastos)
                      .sort(([, a], [, b]) => b - a)
                      .map(([nombre, importe]) => (
                        <TableRow key={nombre}>
                          <TableCell className="text-sm">{nombre}</TableCell>
                          <TableCell className="text-right text-sm text-red-600 dark:text-red-400">
                            {formatearImporte(importe)}
                          </TableCell>
                        </TableRow>
                      ))
                  : null}
                {data && Object.keys(data.detalle_gastos).length === 0 && (
                  <TableRow>
                    <TableCell colSpan={2} className="text-center text-sm text-muted-foreground py-6">
                      Sin datos de gastos
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
