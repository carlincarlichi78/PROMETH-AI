import { useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Archive, FileText, FolderOpen } from 'lucide-react'
import { api } from '@/lib/api-client'
import { queryKeys } from '@/lib/query-keys'
import { formatearFecha, formatearNumero } from '@/lib/formatters'
import { KPICard } from '@/components/charts/kpi-card'
import { DataTable, type ColumnaTabla } from '@/components/data-table/data-table'
import { PageHeader } from '@/components/page-header'
import { EstadoVacio } from '@/components/estado-vacio'
import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { Documento } from '@/types'

type FiltroTipo = 'todos' | 'FC' | 'FV' | 'SUM' | 'BAN' | 'NOM'

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
    header: 'Fecha proceso',
    render: (d) => formatearFecha(d.fecha_proceso),
    sortable: true,
    sortFn: (a, b) => (a.fecha_proceso ?? '').localeCompare(b.fecha_proceso ?? ''),
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
  {
    key: 'ruta_pdf',
    header: 'Ruta PDF',
    render: (d) => {
      const ruta = d.ruta_pdf ?? '-'
      return (
        <span
          className="font-mono text-xs text-muted-foreground"
          title={ruta}
        >
          {ruta.length > 45 ? `...${ruta.slice(-45)}` : ruta}
        </span>
      )
    },
  },
]

export default function ArchivoPage() {
  const { id } = useParams<{ id: string }>()
  const empresaId = Number(id)
  const [filtroTipo, setFiltroTipo] = useState<FiltroTipo>('todos')

  const { data: todosDocumentos = [], isLoading } = useQuery({
    queryKey: queryKeys.documentos.lista(empresaId),
    queryFn: () => api.get<Documento[]>(`/api/documentos/${empresaId}`),
    enabled: !isNaN(empresaId),
  })

  // Solo procesados
  const archivados = useMemo(
    () => todosDocumentos.filter((d) => d.estado === 'procesado'),
    [todosDocumentos]
  )

  const archivadosFiltrados = useMemo(() => {
    if (filtroTipo === 'todos') return archivados
    return archivados.filter((d) => d.tipo_doc === filtroTipo)
  }, [archivados, filtroTipo])

  // KPI: tipos unicos
  const tiposUnicos = useMemo(() => {
    const conteo = archivados.reduce<Record<string, number>>((acc, d) => {
      acc[d.tipo_doc] = (acc[d.tipo_doc] ?? 0) + 1
      return acc
    }, {})
    return Object.keys(conteo).length
  }, [archivados])

  // KPI: tier OCR promedio
  const tierPromedio = useMemo(() => {
    const conTier = archivados.filter((d) => d.ocr_tier != null)
    if (conTier.length === 0) return null
    const suma = conTier.reduce((acc, d) => acc + (d.ocr_tier ?? 0), 0)
    return suma / conTier.length
  }, [archivados])

  return (
    <div className="space-y-6">
      <PageHeader
        titulo="Archivo Digital"
        descripcion="Documentos procesados y archivados"
      />

      <div className="grid grid-cols-3 gap-4">
        <KPICard
          titulo="Total archivados"
          valor={String(archivados.length)}
          icono={Archive}
          cargando={isLoading}
        />
        <KPICard
          titulo="Tipos de documento"
          valor={String(tiposUnicos)}
          icono={FileText}
          cargando={isLoading}
        />
        <KPICard
          titulo="Tier OCR promedio"
          valor={tierPromedio != null ? `T${formatearNumero(tierPromedio, 1)}` : '-'}
          icono={FolderOpen}
          cargando={isLoading}
        />
      </div>

      <div className="flex items-center gap-3">
        <Select
          value={filtroTipo}
          onValueChange={(v) => setFiltroTipo(v as FiltroTipo)}
        >
          <SelectTrigger className="w-36 h-9">
            <SelectValue placeholder="Tipo" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="todos">Todos</SelectItem>
            <SelectItem value="FC">FC</SelectItem>
            <SelectItem value="FV">FV</SelectItem>
            <SelectItem value="SUM">SUM</SelectItem>
            <SelectItem value="BAN">BAN</SelectItem>
            <SelectItem value="NOM">NOM</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {archivados.length === 0 && !isLoading ? (
        <EstadoVacio
          titulo="Sin documentos archivados"
          descripcion="No hay documentos procesados aun para esta empresa"
          icono={Archive}
        />
      ) : (
        <DataTable
          datos={archivadosFiltrados}
          columnas={COLUMNAS}
          cargando={isLoading}
          busqueda
          filtroBusqueda={(d, t) =>
            d.tipo_doc.toLowerCase().includes(t.toLowerCase()) ||
            (d.ruta_pdf ?? '').toLowerCase().includes(t.toLowerCase())
          }
          vacio="No hay documentos con ese filtro"
        />
      )}
    </div>
  )
}
