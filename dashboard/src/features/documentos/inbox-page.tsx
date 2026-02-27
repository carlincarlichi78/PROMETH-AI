import { useMemo } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Inbox, CheckCircle, XCircle, Clock } from 'lucide-react'
import { api } from '@/lib/api-client'
import { queryKeys } from '@/lib/query-keys'
import { formatearFecha, formatearNumero } from '@/lib/formatters'
import { KPICard } from '@/components/charts/kpi-card'
import { DataTable, type ColumnaTabla } from '@/components/data-table/data-table'
import { PageHeader } from '@/components/page-header'
import { EstadoVacio } from '@/components/estado-vacio'
import { Badge } from '@/components/ui/badge'
import type { Documento } from '@/types'

function badgeEstado(estado: string) {
  if (estado === 'procesado') return <Badge variant="secondary">Procesado</Badge>
  if (estado === 'error') return <Badge variant="destructive">Error</Badge>
  return <Badge variant="outline">Pendiente</Badge>
}

const COLUMNAS: ColumnaTabla<Documento>[] = [
  {
    key: 'tipo_doc',
    header: 'Tipo',
    render: (d) => (
      <Badge variant="outline" className="font-mono text-xs">
        {d.tipo_doc}
      </Badge>
    ),
  },
  {
    key: 'fecha_proceso',
    header: 'Fecha',
    render: (d) => formatearFecha(d.fecha_proceso),
    sortable: true,
    sortFn: (a, b) => (a.fecha_proceso ?? '').localeCompare(b.fecha_proceso ?? ''),
  },
  {
    key: 'estado',
    header: 'Estado',
    render: (d) => badgeEstado(d.estado),
  },
  {
    key: 'confianza',
    header: 'Confianza',
    render: (d) =>
      d.confianza != null ? (
        <span className="font-mono text-sm">{formatearNumero(d.confianza, 1)}%</span>
      ) : (
        <span className="text-muted-foreground">-</span>
      ),
    sortable: true,
    sortFn: (a, b) => (a.confianza ?? 0) - (b.confianza ?? 0),
    className: 'text-right',
  },
  {
    key: 'ocr_tier',
    header: 'OCR Tier',
    render: (d) =>
      d.ocr_tier != null ? (
        <span className="font-mono text-sm text-muted-foreground">T{d.ocr_tier}</span>
      ) : (
        <span className="text-muted-foreground">-</span>
      ),
  },
]

export default function InboxPage() {
  const { id } = useParams<{ id: string }>()
  const empresaId = Number(id)

  const { data: documentos = [], isLoading } = useQuery({
    queryKey: queryKeys.documentos.lista(empresaId),
    queryFn: () => api.get<Documento[]>(`/api/documentos/${empresaId}`),
    enabled: !isNaN(empresaId),
  })

  const procesados = useMemo(() => documentos.filter((d) => d.estado === 'procesado'), [documentos])
  const conErrores = useMemo(() => documentos.filter((d) => d.estado === 'error'), [documentos])
  const enCola = useMemo(() => documentos.filter((d) => d.estado === 'pendiente'), [documentos])

  return (
    <div className="space-y-6">
      <PageHeader
        titulo="Bandeja de Entrada"
        descripcion="Documentos pendientes de procesar"
      />

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          titulo="Total documentos"
          valor={String(documentos.length)}
          icono={Inbox}
          cargando={isLoading}
        />
        <KPICard
          titulo="Procesados"
          valor={String(procesados.length)}
          icono={CheckCircle}
          cargando={isLoading}
        />
        <KPICard
          titulo="Con errores"
          valor={String(conErrores.length)}
          icono={XCircle}
          cargando={isLoading}
          invertirColor
        />
        <KPICard
          titulo="En cola"
          valor={String(enCola.length)}
          icono={Clock}
          cargando={isLoading}
        />
      </div>

      <DataTable
        datos={documentos}
        columnas={COLUMNAS}
        cargando={isLoading}
        busqueda
        filtroBusqueda={(d, t) =>
          d.tipo_doc.toLowerCase().includes(t.toLowerCase()) ||
          d.estado.toLowerCase().includes(t.toLowerCase())
        }
        vacio={
          <EstadoVacio
            titulo="Sin documentos en bandeja"
            descripcion="No hay documentos pendientes de procesar"
            icono={Inbox}
          />
        }
      />
    </div>
  )
}
