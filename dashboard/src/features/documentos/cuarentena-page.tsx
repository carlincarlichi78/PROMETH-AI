import { useMemo } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ShieldAlert, CheckCircle2, Clock } from 'lucide-react'
import { api } from '@/lib/api-client'
import { queryKeys } from '@/lib/query-keys'
import { KPICard } from '@/components/charts/kpi-card'
import { DataTable, type ColumnaTabla } from '@/components/data-table/data-table'
import { PageHeader } from '@/components/page-header'
import { EstadoVacio } from '@/components/estado-vacio'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import type { Cuarentena } from '@/types'

const COLUMNAS: ColumnaTabla<Cuarentena>[] = [
  {
    key: 'documento_id',
    header: 'Doc. ID',
    render: (c) => (
      <span className="font-mono text-sm">{c.documento_id}</span>
    ),
  },
  {
    key: 'tipo_pregunta',
    header: 'Tipo',
    render: (c) => (
      <Badge variant="outline" className="font-mono text-xs">
        {c.tipo_pregunta}
      </Badge>
    ),
  },
  {
    key: 'pregunta',
    header: 'Pregunta',
    render: (c) => (
      <span className="text-sm text-muted-foreground">
        {c.pregunta.length > 60 ? `${c.pregunta.slice(0, 60)}...` : c.pregunta}
      </span>
    ),
  },
  {
    key: 'resuelta',
    header: 'Estado',
    render: (c) =>
      c.resuelta ? (
        <Badge variant="secondary">Resuelta</Badge>
      ) : (
        <Badge variant="outline" className="text-amber-600 border-amber-400">
          Pendiente
        </Badge>
      ),
  },
  {
    key: 'respuesta',
    header: 'Respuesta',
    render: (c) => (
      <span className="text-sm">{c.respuesta ?? '—'}</span>
    ),
  },
]

export default function CuarentenaPage() {
  const { id } = useParams<{ id: string }>()
  const empresaId = Number(id)

  const { data: items = [], isLoading } = useQuery({
    queryKey: queryKeys.documentos.cuarentena(empresaId),
    queryFn: () => api.get<Cuarentena[]>(`/api/documentos/${empresaId}/cuarentena`),
    enabled: !isNaN(empresaId),
  })

  const resueltas = useMemo(() => items.filter((c) => c.resuelta), [items])
  const pendientes = useMemo(() => items.filter((c) => !c.resuelta), [items])

  return (
    <div className="space-y-6">
      <PageHeader
        titulo="Cuarentena"
        descripcion="Documentos que requieren intervencion manual"
      />

      <div className="grid grid-cols-3 gap-4">
        <KPICard
          titulo="Total en cuarentena"
          valor={String(items.length)}
          icono={ShieldAlert}
          cargando={isLoading}
        />
        <KPICard
          titulo="Resueltas"
          valor={String(resueltas.length)}
          icono={CheckCircle2}
          cargando={isLoading}
        />
        <KPICard
          titulo="Pendientes resolver"
          valor={String(pendientes.length)}
          icono={Clock}
          cargando={isLoading}
          invertirColor
        />
      </div>

      {pendientes.length > 0 && (
        <Alert variant="destructive">
          <ShieldAlert className="h-4 w-4" />
          <AlertDescription>
            Hay {pendientes.length} documento{pendientes.length !== 1 ? 's' : ''} esperando resolucion manual.
          </AlertDescription>
        </Alert>
      )}

      {items.length === 0 && !isLoading ? (
        <EstadoVacio
          titulo="Sin documentos en cuarentena"
          descripcion="Todos los documentos se han procesado correctamente. No hay items pendientes de resolucion."
          icono={CheckCircle2}
        />
      ) : (
        <DataTable
          datos={items}
          columnas={COLUMNAS}
          cargando={isLoading}
          busqueda
          filtroBusqueda={(c, t) =>
            c.tipo_pregunta.toLowerCase().includes(t.toLowerCase()) ||
            c.pregunta.toLowerCase().includes(t.toLowerCase())
          }
          vacio="No hay documentos en cuarentena"
        />
      )}
    </div>
  )
}
