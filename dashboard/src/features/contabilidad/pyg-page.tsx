import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  ComposedChart, Bar, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, Treemap,
} from 'recharts'
import { TrendingUp, TrendingDown } from 'lucide-react'
import { api } from '@/lib/api-client'
import { formatearImporte, formatearPorcentaje } from '@/lib/formatters'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { WaterfallChart } from '@/components/charts/waterfall-chart'
import { CHART_COLORS } from '@/components/ui/chart-wrapper'
import type { PyG2, PyGLinea } from '@/types'

function KpiCard({ titulo, valor, pct }: { titulo: string; valor: number; pct?: number }) {
  const positivo = valor >= 0
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm text-muted-foreground font-normal">{titulo}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-2xl font-bold tabular-nums">{formatearImporte(valor)}</p>
        <div className="flex items-center gap-2 mt-1">
          {pct != null && (
            <Badge variant="outline" className="text-xs">
              {formatearPorcentaje(pct / 100)} s/ventas
            </Badge>
          )}
          {positivo
            ? <TrendingUp className="h-4 w-4 text-emerald-500" />
            : <TrendingDown className="h-4 w-4 text-rose-500" />
          }
        </div>
      </CardContent>
    </Card>
  )
}

function TablaFormal({ lineas }: { lineas: PyGLinea[] }) {
  const [expandidas, setExpandidas] = useState<Set<string>>(new Set())

  const toggle = (id: string) => {
    const s = new Set(expandidas)
    s.has(id) ? s.delete(id) : s.add(id)
    setExpandidas(s)
  }

  return (
    <div className="rounded-md border overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-muted/50">
          <tr>
            <th className="text-left px-4 py-2 font-medium">Descripción</th>
            <th className="text-right px-4 py-2 font-medium w-36">Importe</th>
            <th className="text-right px-4 py-2 font-medium w-24">% Ventas</th>
          </tr>
        </thead>
        <tbody>
          {lineas.map((linea) => {
            const esSubtotal = ['subtotal_positivo', 'subtotal_destacado', 'resultado_final'].includes(linea.tipo)
            const tieneDetalle = linea.detalle.length > 0
            const expandida = expandidas.has(linea.id)

            return (
              <>
                <tr
                  key={linea.id}
                  className={[
                    'border-t cursor-pointer hover:bg-muted/30 transition-colors',
                    esSubtotal ? 'bg-slate-50 dark:bg-slate-900 font-semibold' : '',
                    linea.tipo === 'resultado_final' ? 'bg-violet-50 dark:bg-violet-950' : '',
                  ].join(' ')}
                  onClick={() => tieneDetalle && toggle(linea.id)}
                >
                  <td className="px-4 py-2">
                    <span className="flex items-center gap-2">
                      {tieneDetalle && (
                        <span className="text-muted-foreground">{expandida ? '▼' : '▶'}</span>
                      )}
                      {!tieneDetalle && esSubtotal && <span className="w-4" />}
                      {linea.descripcion}
                    </span>
                  </td>
                  <td className={[
                    'px-4 py-2 text-right tabular-nums',
                    linea.tipo === 'gasto' ? 'text-rose-600' : 'text-foreground',
                  ].join(' ')}>
                    {formatearImporte(linea.importe)}
                  </td>
                  <td className="px-4 py-2 text-right tabular-nums text-muted-foreground">
                    {linea.pct_ventas != null ? `${linea.pct_ventas.toFixed(1)}%` : '—'}
                  </td>
                </tr>
                {expandida && linea.detalle.map((d) => (
                  <tr key={d.subcuenta} className="bg-muted/20 border-t">
                    <td className="px-4 py-1.5 pl-10 text-muted-foreground text-xs">
                      {d.subcuenta.replace(/0+$/, '')} · {d.nombre}
                    </td>
                    <td className="px-4 py-1.5 text-right text-xs tabular-nums text-muted-foreground">
                      {formatearImporte(d.importe)}
                    </td>
                    <td />
                  </tr>
                ))}
              </>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

export default function PyGPage() {
  const { id } = useParams<{ id: string }>()
  const empresaId = Number(id)

  const { data, isLoading, error } = useQuery<PyG2>({
    queryKey: ['contabilidad', empresaId, 'pyg2'],
    queryFn: () => api.get<PyG2>(`/api/contabilidad/${empresaId}/pyg2`),
    enabled: !!empresaId,
  })

  if (isLoading) {
    return (
      <div className="p-6 space-y-4">
        {[1, 2, 3, 4].map(i => <Skeleton key={i} className="h-24" />)}
      </div>
    )
  }
  if (error || !data) {
    return <div className="p-6 text-destructive">Error cargando la Cuenta de Pérdidas y Ganancias</div>
  }

  const { resumen, lineas, waterfall, evolucion_mensual } = data

  const gastosDetalle = lineas
    .flatMap(l => l.tipo === 'gasto' ? l.detalle : [])
    .sort((a, b) => b.importe - a.importe)
    .slice(0, 10)

  const treemapData = lineas
    .filter(l => l.tipo === 'gasto' && l.importe > 0)
    .map(l => ({
      name: l.descripcion,
      size: l.importe,
      children: l.detalle.map(d => ({ name: d.nombre, size: d.importe })),
    }))

  const sinEvolucion = evolucion_mensual.length === 0

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Cuenta de Pérdidas y Ganancias</h1>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard titulo="Ventas netas" valor={resumen.ventas_netas} />
        <KpiCard titulo="Margen Bruto" valor={resumen.margen_bruto} pct={resumen.margen_bruto_pct} />
        <KpiCard titulo="EBITDA" valor={resumen.ebitda} pct={resumen.ebitda_pct} />
        <KpiCard titulo="Resultado neto" valor={resumen.resultado} pct={resumen.resultado_pct} />
      </div>

      {/* Tabs */}
      <Tabs defaultValue="waterfall">
        <TabsList>
          <TabsTrigger value="waterfall">Cascada de valor</TabsTrigger>
          <TabsTrigger value="formal">Cuenta formal</TabsTrigger>
          <TabsTrigger value="evolucion">Evolución mensual</TabsTrigger>
          <TabsTrigger value="costes">Composición costes</TabsTrigger>
        </TabsList>

        <TabsContent value="waterfall" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Cascada de valor — de ventas a resultado</CardTitle>
            </CardHeader>
            <CardContent>
              <WaterfallChart datos={waterfall} altura={360} />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="formal" className="mt-4">
          <TablaFormal lineas={lineas} />
        </TabsContent>

        <TabsContent value="evolucion" className="mt-4">
          {sinEvolucion ? (
            <Card>
              <CardContent className="pt-6">
                <p className="text-muted-foreground text-sm text-center py-8">
                  Evolución no disponible — fechas pendientes de rectificación.
                </p>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Ingresos vs Gastos por mes</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={320}>
                  <ComposedChart data={evolucion_mensual}>
                    <XAxis dataKey="mes" tick={{ fontSize: 11 }} />
                    <YAxis tickFormatter={v => `${((v as number) / 1000).toFixed(0)}k`} />
                    <Tooltip formatter={(v) => formatearImporte(v as number)} />
                    <Bar dataKey="ingresos" fill={CHART_COLORS.success} name="Ingresos" />
                    <Bar dataKey="gastos" fill={CHART_COLORS.danger} name="Gastos" />
                    <Line type="monotone" dataKey="resultado" stroke={CHART_COLORS.primary} strokeWidth={2} dot={false} name="Resultado" />
                  </ComposedChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="costes" className="mt-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Mapa de costes</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={280}>
                  <Treemap data={treemapData} dataKey="size" nameKey="name" fill={CHART_COLORS.primary} aspectRatio={4 / 3} />
                </ResponsiveContainer>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Top 10 partidas de gasto</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {gastosDetalle.map((g, i) => (
                    <div key={g.subcuenta} className="flex items-center gap-2 text-sm">
                      <span className="text-muted-foreground w-4 text-right">{i + 1}</span>
                      <span className="flex-1 truncate">{g.nombre}</span>
                      <span className="tabular-nums font-medium">{formatearImporte(g.importe)}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
