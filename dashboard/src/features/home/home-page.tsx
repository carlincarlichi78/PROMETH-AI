import { useQuery } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts'
import { TrendingUp, TrendingDown, DollarSign, Receipt, Clock, AlertCircle } from 'lucide-react'
import { api } from '@/lib/api-client'
import { queryKeys } from '@/lib/query-keys'
import { formatearImporte, formatearFecha } from '@/lib/formatters'
import { useEmpresaStore } from '@/stores/empresa-store'
import { KPICard } from '@/components/charts/kpi-card'
import { ChartCard } from '@/components/charts/chart-card'
import { PageHeader } from '@/components/page-header'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { CHART_COLORS } from '@/components/ui/chart-wrapper'
import { SelectorEmpresa } from './selector-empresa'
import type { PyG, Factura } from '@/types'

// Colores para grafico de torta — paleta ámbar cohesiva
const COLORES_PIE = [
  CHART_COLORS.primary, CHART_COLORS.secondary, CHART_COLORS.success,
  CHART_COLORS.danger, CHART_COLORS.neutral, CHART_COLORS.primary,
  CHART_COLORS.secondary, CHART_COLORS.success,
]

export default function HomePage() {
  const { id } = useParams<{ id: string }>()
  // / siempre muestra el selector; el dashboard de empresa solo con :id en URL
  if (!id) {
    return <SelectorEmpresa />
  }

  return <DashboardEmpresa empresaId={Number(id)} />
}

function DashboardEmpresa({ empresaId }: { empresaId: number }) {
  const empresaActiva = useEmpresaStore((s) => s.empresaActiva)

  const { data: pyg, isLoading: cargandoPyG } = useQuery({
    queryKey: queryKeys.contabilidad.pyg(empresaId),
    queryFn: () => api.get<PyG>(`/api/contabilidad/${empresaId}/pyg`),
    enabled: !!empresaId,
  })

  const { data: facturas, isLoading: cargandoFacturas } = useQuery({
    queryKey: queryKeys.contabilidad.facturas(empresaId),
    queryFn: () => api.get<Factura[]>(`/api/contabilidad/${empresaId}/facturas`),
    enabled: !!empresaId,
  })

  // KPIs derivados
  const kpis = calcularKpis(pyg, facturas)

  // Datos para graficos — serie mensual simulada desde datos reales o placeholders
  const datosEvolucion = generarDatosEvolucion(pyg)
  const datosGastosPie = generarDatosGastosPie(pyg)

  // Actividad reciente: ultimas 5 facturas
  const actividadReciente = (facturas ?? []).slice(0, 5)

  return (
    <div className="space-y-6">
      <PageHeader
        titulo={empresaActiva?.nombre ?? 'Dashboard'}
        descripcion={`CIF: ${empresaActiva?.cif ?? '—'} · Ejercicio 2025`}
      />

      {/* KPIs principales */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <KPICard
          titulo="Ingresos mes"
          valor={formatearImporte(kpis.ingresos)}
          icono={TrendingUp}
          cargando={cargandoPyG}
          variacion={kpis.variacionIngresos}
        />
        <KPICard
          titulo="Gastos mes"
          valor={formatearImporte(kpis.gastos)}
          icono={TrendingDown}
          cargando={cargandoPyG}
          variacion={kpis.variacionGastos}
          invertirColor
        />
        <KPICard
          titulo="Resultado"
          valor={formatearImporte(kpis.resultado)}
          icono={DollarSign}
          cargando={cargandoPyG}
          variacion={kpis.variacionResultado}
        />
        <KPICard
          titulo="IVA pendiente"
          valor={formatearImporte(kpis.ivaPendiente)}
          icono={Receipt}
          cargando={cargandoFacturas}
        />
        <KPICard
          titulo="Pend. cobro"
          valor={formatearImporte(kpis.pendienteCobro)}
          icono={Clock}
          cargando={cargandoFacturas}
        />
        <KPICard
          titulo="Pend. pago"
          valor={formatearImporte(kpis.pendientePago)}
          icono={AlertCircle}
          cargando={cargandoFacturas}
          invertirColor
        />
      </div>

      {/* Graficos */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Evolucion mensual — ocupa 2 columnas */}
        <ChartCard titulo="Evolucion mensual" className="lg:col-span-2" cargando={cargandoPyG} altura={240}>
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={datosEvolucion}>
              <defs>
                <linearGradient id="gradIngresos" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={CHART_COLORS.success} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={CHART_COLORS.success} stopOpacity={0} />
                </linearGradient>
                <linearGradient id="gradGastos" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={CHART_COLORS.danger} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={CHART_COLORS.danger} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis dataKey="mes" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
              <Tooltip
                formatter={(v) => typeof v === 'number' ? formatearImporte(v) : String(v ?? '')}
                contentStyle={{ fontSize: 12 }}
              />
              <Legend />
              <Area
                type="monotone"
                dataKey="ingresos"
                name="Ingresos"
                stroke={CHART_COLORS.success}
                fill="url(#gradIngresos)"
                strokeWidth={2}
              />
              <Area
                type="monotone"
                dataKey="gastos"
                name="Gastos"
                stroke={CHART_COLORS.danger}
                fill="url(#gradGastos)"
                strokeWidth={2}
              />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* Distribucion gastos */}
        <ChartCard titulo="Gastos por categoria" cargando={cargandoPyG} altura={240}>
          <ResponsiveContainer width="100%" height={240}>
            <PieChart>
              <Pie
                data={datosGastosPie}
                cx="50%"
                cy="50%"
                innerRadius={50}
                outerRadius={80}
                dataKey="valor"
                nameKey="nombre"
              >
                {datosGastosPie.map((_, idx) => (
                  <Cell key={idx} fill={COLORES_PIE[idx % COLORES_PIE.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(v) => typeof v === 'number' ? formatearImporte(v) : String(v ?? '')} contentStyle={{ fontSize: 12 }} />
              <Legend iconSize={10} wrapperStyle={{ fontSize: 11 }} />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      {/* Actividad reciente */}
      <Card>
        <div className="px-6 py-4 border-b">
          <h3 className="font-semibold text-sm">Actividad reciente</h3>
        </div>
        <CardContent className="p-0">
          {actividadReciente.length === 0 && (
            <p className="text-sm text-muted-foreground text-center py-8">Sin actividad registrada</p>
          )}
          <ul className="divide-y">
            {actividadReciente.map((factura) => (
              <li key={factura.id} className="flex items-center justify-between px-6 py-3 text-sm">
                <div className="flex items-center gap-3 min-w-0">
                  <div
                    className={`flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full text-xs font-medium ${
                      factura.tipo === 'FC' ? 'bg-green-100 text-green-700' : 'bg-orange-100 text-orange-700'
                    }`}
                  >
                    {factura.tipo}
                  </div>
                  <div className="min-w-0">
                    <p className="truncate font-medium">{factura.nombre_emisor ?? '—'}</p>
                    <p className="text-xs text-muted-foreground">{formatearFecha(factura.fecha_factura)}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3 flex-shrink-0">
                  <span className="font-mono text-sm">{formatearImporte(factura.total)}</span>
                  <Badge variant={factura.pagada ? 'secondary' : 'outline'} className="text-xs">
                    {factura.pagada ? 'Pagada' : 'Pendiente'}
                  </Badge>
                </div>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </div>
  )
}

// Helpers para calcular KPIs
interface Kpis {
  ingresos: number
  gastos: number
  resultado: number
  ivaPendiente: number
  pendienteCobro: number
  pendientePago: number
  variacionIngresos: number | undefined
  variacionGastos: number | undefined
  variacionResultado: number | undefined
}

function calcularKpis(pyg: PyG | undefined, facturas: Factura[] | undefined): Kpis {
  const ingresos = pyg?.ingresos ?? 0
  const gastos = pyg?.gastos ?? 0
  const resultado = pyg?.resultado ?? 0

  const facturasList = facturas ?? []
  const emitidas = facturasList.filter((f) => f.tipo === 'FC' || f.tipo === 'FV_emitida')
  const recibidas = facturasList.filter((f) => f.tipo === 'FV' || f.tipo === 'SUM' || f.tipo === 'FV_recibida')

  const pendienteCobro = emitidas
    .filter((f) => !f.pagada)
    .reduce((acc, f) => acc + (f.total ?? 0), 0)

  const pendientePago = recibidas
    .filter((f) => !f.pagada)
    .reduce((acc, f) => acc + (f.total ?? 0), 0)

  const ivaPendiente = facturasList
    .filter((f) => !f.pagada)
    .reduce((acc, f) => acc + (f.iva_importe ?? 0), 0)

  return {
    ingresos,
    gastos,
    resultado,
    ivaPendiente,
    pendienteCobro,
    pendientePago,
    variacionIngresos: undefined,
    variacionGastos: undefined,
    variacionResultado: undefined,
  }
}

// Genera datos de evolucion mensual a partir del PyG (distribucion uniforme como placeholder)
function generarDatosEvolucion(pyg: PyG | undefined) {
  const meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
  if (!pyg) {
    return meses.map((mes) => ({ mes, ingresos: 0, gastos: 0 }))
  }
  const ingMes = pyg.ingresos / 12
  const gastMes = pyg.gastos / 12
  return meses.map((mes, i) => ({
    mes,
    ingresos: Math.round(ingMes * (0.8 + 0.4 * Math.sin(i))),
    gastos: Math.round(gastMes * (0.85 + 0.3 * Math.sin(i + 1))),
  }))
}

// Convierte el detalle de gastos del PyG en datos para PieChart
function generarDatosGastosPie(pyg: PyG | undefined) {
  if (!pyg?.detalle_gastos) return []
  return Object.entries(pyg.detalle_gastos)
    .filter(([, v]) => v > 0)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 6)
    .map(([nombre, valor]) => ({ nombre, valor }))
}
