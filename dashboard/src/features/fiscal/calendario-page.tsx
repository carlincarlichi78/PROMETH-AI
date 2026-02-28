import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Calendar, AlertTriangle, CheckCircle2 } from 'lucide-react'
import { PageHeader } from '@/components/page-header'
import { KPICard } from '@/components/charts/kpi-card'
import { DataTable, type ColumnaTabla } from '@/components/data-table/data-table'
import { EstadoVacio } from '@/components/estado-vacio'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { api } from '@/lib/api-client'
import { queryKeys } from '@/lib/query-keys'
import { formatearImporte, formatearFecha } from '@/lib/formatters'

interface EventoFiscal {
  modelo: string
  nombre: string
  periodo: string
  fecha_limite: string
  estado: 'pendiente' | 'presentado' | 'vencido'
  importe?: number
}

// DataTable requiere id opcional; añadimos idx como id sintetico
type EventoFiscalConId = EventoFiscal & { id: number }

function badgeEstado(estado: EventoFiscal['estado']) {
  if (estado === 'pendiente') return <Badge variant="outline">Pendiente</Badge>
  if (estado === 'presentado') return <Badge variant="secondary">Presentado</Badge>
  return <Badge variant="destructive">Vencido</Badge>
}

const COLUMNAS: ColumnaTabla<EventoFiscalConId>[] = [
  {
    key: 'modelo',
    header: 'Modelo',
    render: (e) => <span className="font-mono font-medium">{e.modelo}</span>,
  },
  {
    key: 'nombre',
    header: 'Nombre',
    render: (e) => e.nombre,
  },
  {
    key: 'periodo',
    header: 'Periodo',
    render: (e) => e.periodo,
  },
  {
    key: 'fecha_limite',
    header: 'Fecha Limite',
    render: (e) => formatearFecha(e.fecha_limite),
    sortable: true,
    sortFn: (a, b) => a.fecha_limite.localeCompare(b.fecha_limite),
  },
  {
    key: 'estado',
    header: 'Estado',
    render: (e) => badgeEstado(e.estado),
  },
  {
    key: 'importe',
    header: 'Importe',
    render: (e) => (e.importe != null ? formatearImporte(e.importe) : '-'),
    className: 'text-right',
    sortable: true,
    sortFn: (a, b) => (a.importe ?? 0) - (b.importe ?? 0),
  },
]

export default function CalendarioPage() {
  const { id } = useParams<{ id: string }>()
  const empresaId = Number(id)

  const { data: eventos, isLoading } = useQuery({
    queryKey: queryKeys.modelos.calendario(empresaId),
    queryFn: () => api.get<EventoFiscal[]>(`/api/modelos/calendario/${empresaId}/${new Date().getFullYear()}`),
    enabled: !isNaN(empresaId),
  })

  const eventosConId: EventoFiscalConId[] = (eventos ?? []).map((e, idx) => ({ ...e, id: idx }))

  const pendientes = eventosConId.filter((e) => e.estado === 'pendiente')
  const vencidos = eventosConId.filter((e) => e.estado === 'vencido')

  const importeTotal = pendientes.reduce((sum, e) => sum + (e.importe ?? 0), 0)

  const proximaPendiente = [...pendientes].sort((a, b) =>
    a.fecha_limite.localeCompare(b.fecha_limite)
  )[0]

  const valorProxima = proximaPendiente
    ? `${proximaPendiente.modelo} · ${formatearFecha(proximaPendiente.fecha_limite)}`
    : '-'

  if (!isLoading && (!eventos || eventos.length === 0)) {
    return (
      <div>
        <PageHeader titulo="Calendario Fiscal" />
        <EstadoVacio
          titulo="Calendario sin configurar"
          descripcion="No hay obligaciones fiscales configuradas para esta empresa."
          icono={Calendar}
        />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader titulo="Calendario Fiscal" />

      {vencidos.length > 0 && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            Hay {vencidos.length} modelo{vencidos.length !== 1 ? 's' : ''} vencido
            {vencidos.length !== 1 ? 's' : ''}. Revisa urgentemente.
          </AlertDescription>
        </Alert>
      )}

      <div className="grid gap-4 grid-cols-1 sm:grid-cols-3">
        <KPICard
          titulo="Obligaciones pendientes"
          valor={isLoading ? '...' : String(pendientes.length)}
          icono={Calendar}
          cargando={isLoading}
        />
        <KPICard
          titulo="Proxima fecha"
          valor={isLoading ? '...' : valorProxima}
          icono={CheckCircle2}
          cargando={isLoading}
        />
        <KPICard
          titulo="Importe total pendiente"
          valor={isLoading ? '...' : formatearImporte(importeTotal)}
          icono={AlertTriangle}
          cargando={isLoading}
        />
      </div>

      <DataTable
        datos={eventosConId}
        columnas={COLUMNAS}
        cargando={isLoading}
        busqueda
        filtroBusqueda={(e, t) =>
          e.modelo.toLowerCase().includes(t.toLowerCase()) ||
          e.nombre.toLowerCase().includes(t.toLowerCase()) ||
          e.periodo.toLowerCase().includes(t.toLowerCase())
        }
        vacio={
          <EstadoVacio
            titulo="Sin eventos fiscales"
            descripcion="No hay obligaciones registradas."
            icono={Calendar}
          />
        }
      />
    </div>
  )
}
