import { useMemo } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { TrendingUp, TrendingDown, Scale } from 'lucide-react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'
import { api } from '@/lib/api-client'
import { queryKeys } from '@/lib/query-keys'
import { formatearImporte, formatearFecha } from '@/lib/formatters'
import { KPICard } from '@/components/charts/kpi-card'
import { ChartCard } from '@/components/charts/chart-card'
import { DataTable, type ColumnaTabla } from '@/components/data-table/data-table'
import { PageHeader } from '@/components/page-header'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import type { Factura } from '@/types'

const BUCKETS = ['0-30 dias', '31-60 dias', '61-90 dias', '+90 dias'] as const
type Bucket = (typeof BUCKETS)[number]

function calcularBucketAging(fechaFactura: string | null): Bucket {
  if (!fechaFactura) return '+90 dias'
  const dias = Math.floor(
    (Date.now() - new Date(fechaFactura).getTime()) / (1000 * 60 * 60 * 24)
  )
  if (dias <= 30) return '0-30 dias'
  if (dias <= 60) return '31-60 dias'
  if (dias <= 90) return '61-90 dias'
  return '+90 dias'
}

interface AgingFila {
  bucket: Bucket
  cobros: number
  pagos: number
}

const COLUMNAS_AGING: ColumnaTabla<Factura>[] = [
  {
    key: 'numero_factura',
    header: 'Numero',
    render: (f) => <span className="font-mono text-sm">{f.numero_factura ?? '-'}</span>,
  },
  {
    key: 'fecha_factura',
    header: 'Fecha',
    render: (f) => formatearFecha(f.fecha_factura),
  },
  {
    key: 'nombre_emisor',
    header: 'Nombre',
    render: (f) => <span className="font-medium">{f.nombre_emisor ?? '-'}</span>,
  },
  {
    key: 'tipo',
    header: 'Tipo',
    render: (f) => (
      <Badge variant="outline" className="text-xs font-mono">
        {f.tipo === 'emitida' ? 'Cobro' : 'Pago'}
      </Badge>
    ),
  },
  {
    key: 'total',
    header: 'Importe',
    render: (f) => (
      <span className="text-right block font-semibold">{formatearImporte(f.total)}</span>
    ),
    className: 'text-right',
  },
  {
    key: 'pagada',
    header: 'Estado',
    render: (f) => (
      <Badge
        variant="outline"
        className={f.tipo === 'emitida' ? 'text-amber-600 border-amber-400' : 'text-red-600 border-red-400'}
      >
        {f.tipo === 'emitida' ? 'Pendiente cobro' : 'Pendiente pago'}
      </Badge>
    ),
  },
]

function TooltipImporte({ active, payload, label }: {
  active?: boolean
  payload?: Array<{ name: string; value: number; color: string }>
  label?: string
}) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-popover border rounded-lg shadow-md p-3 text-sm space-y-1">
      <p className="font-medium mb-2">{label}</p>
      {payload.map((p) => (
        <div key={p.name} className="flex items-center gap-2">
          <span style={{ color: p.color }}>■</span>
          <span className="text-muted-foreground">{p.name}:</span>
          <span className="font-medium">{formatearImporte(p.value)}</span>
        </div>
      ))}
    </div>
  )
}

export default function CobrosPagosPage() {
  const { id } = useParams<{ id: string }>()
  const empresaId = Number(id)

  const { data: facturas = [], isLoading } = useQuery({
    queryKey: queryKeys.contabilidad.facturas(empresaId),
    queryFn: () => api.get<Factura[]>(`/api/contabilidad/${empresaId}/facturas`),
    enabled: !isNaN(empresaId),
  })

  const pendientesCobro = useMemo(
    () => facturas.filter((f) => f.tipo === 'emitida' && !f.pagada),
    [facturas]
  )
  const pendientesPago = useMemo(
    () => facturas.filter((f) => f.tipo === 'recibida' && !f.pagada),
    [facturas]
  )

  const totalPendienteCobro = useMemo(
    () => pendientesCobro.reduce((a, f) => a + (f.total ?? 0), 0),
    [pendientesCobro]
  )
  const totalPendientePago = useMemo(
    () => pendientesPago.reduce((a, f) => a + (f.total ?? 0), 0),
    [pendientesPago]
  )
  const saldoNeto = totalPendienteCobro - totalPendientePago

  const datosAging: AgingFila[] = useMemo(() => {
    const mapa: Record<Bucket, { cobros: number; pagos: number }> = {
      '0-30 dias': { cobros: 0, pagos: 0 },
      '31-60 dias': { cobros: 0, pagos: 0 },
      '61-90 dias': { cobros: 0, pagos: 0 },
      '+90 dias': { cobros: 0, pagos: 0 },
    }
    for (const f of pendientesCobro) {
      const bucket = calcularBucketAging(f.fecha_factura)
      mapa[bucket].cobros += f.total ?? 0
    }
    for (const f of pendientesPago) {
      const bucket = calcularBucketAging(f.fecha_factura)
      mapa[bucket].pagos += f.total ?? 0
    }
    return BUCKETS.map((bucket) => ({ bucket, ...mapa[bucket] }))
  }, [pendientesCobro, pendientesPago])

  const todosLosPendientes = useMemo(
    () => [...pendientesCobro, ...pendientesPago],
    [pendientesCobro, pendientesPago]
  )

  return (
    <div className="space-y-6">
      <PageHeader
        titulo="Cobros y Pagos"
        descripcion="Analisis de vencimientos y aging de saldos pendientes"
      />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <KPICard
          titulo="Pendiente de cobro"
          valor={formatearImporte(totalPendienteCobro)}
          icono={TrendingUp}
          descripcion={`${pendientesCobro.length} factura${pendientesCobro.length !== 1 ? 's' : ''}`}
          cargando={isLoading}
        />
        <KPICard
          titulo="Pendiente de pago"
          valor={formatearImporte(totalPendientePago)}
          icono={TrendingDown}
          descripcion={`${pendientesPago.length} factura${pendientesPago.length !== 1 ? 's' : ''}`}
          cargando={isLoading}
          invertirColor
        />
        <KPICard
          titulo="Saldo neto"
          valor={formatearImporte(saldoNeto)}
          icono={Scale}
          descripcion={saldoNeto >= 0 ? 'Posicion favorable' : 'Posicion desfavorable'}
          cargando={isLoading}
        />
      </div>

      <ChartCard titulo="Aging — Distribucion por antiguedad" altura={280} cargando={isLoading}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={datosAging} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
            <XAxis
              dataKey="bucket"
              tick={{ fontSize: 12 }}
              className="text-muted-foreground"
            />
            <YAxis
              tickFormatter={(v: number) =>
                new Intl.NumberFormat('es-ES', {
                  notation: 'compact',
                  maximumFractionDigits: 1,
                }).format(v)
              }
              tick={{ fontSize: 12 }}
              className="text-muted-foreground"
            />
            <Tooltip content={<TooltipImporte />} />
            <Legend
              formatter={(value: string) =>
                value === 'cobros' ? 'Pendiente cobro' : 'Pendiente pago'
              }
            />
            <Bar dataKey="cobros" fill="#22c55e" radius={[4, 4, 0, 0]} name="cobros" />
            <Bar dataKey="pagos" fill="#ef4444" radius={[4, 4, 0, 0]} name="pagos" />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      <Tabs defaultValue="todos">
        <TabsList>
          <TabsTrigger value="todos">
            Todos ({todosLosPendientes.length})
          </TabsTrigger>
          <TabsTrigger value="cobros">
            Cobros pendientes ({pendientesCobro.length})
          </TabsTrigger>
          <TabsTrigger value="pagos">
            Pagos pendientes ({pendientesPago.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="todos" className="mt-4">
          <DataTable
            datos={todosLosPendientes}
            columnas={COLUMNAS_AGING}
            cargando={isLoading}
            vacio="No hay saldos pendientes"
          />
        </TabsContent>

        <TabsContent value="cobros" className="mt-4">
          <DataTable
            datos={pendientesCobro}
            columnas={COLUMNAS_AGING}
            cargando={isLoading}
            vacio="No hay cobros pendientes"
          />
        </TabsContent>

        <TabsContent value="pagos" className="mt-4">
          <DataTable
            datos={pendientesPago}
            columnas={COLUMNAS_AGING}
            cargando={isLoading}
            vacio="No hay pagos pendientes"
          />
        </TabsContent>
      </Tabs>
    </div>
  )
}
