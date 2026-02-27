import { useState, useMemo } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { FileText } from 'lucide-react'
import { PageHeader } from '@/components/page-header'
import { KPICard } from '@/components/charts/kpi-card'
import { DataTable, type ColumnaTabla } from '@/components/data-table/data-table'
import { EstadoVacio } from '@/components/estado-vacio'
import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { api } from '@/lib/api-client'
import { queryKeys } from '@/lib/query-keys'
import { formatearImporte, formatearFecha } from '@/lib/formatters'

interface ModeloPresentado {
  id: number
  modelo: string
  periodo: string
  ejercicio: string
  fecha_generacion: string
  resultado_total: number
  estado: 'generado' | 'presentado'
}

function badgeEstado(estado: ModeloPresentado['estado']) {
  if (estado === 'presentado') return <Badge variant="secondary">Presentado</Badge>
  return <Badge variant="outline">Generado</Badge>
}

const COLUMNAS: ColumnaTabla<ModeloPresentado>[] = [
  {
    key: 'modelo',
    header: 'Modelo',
    render: (m) => <span className="font-mono font-medium">{m.modelo}</span>,
  },
  {
    key: 'periodo',
    header: 'Periodo',
    render: (m) => m.periodo,
  },
  {
    key: 'ejercicio',
    header: 'Ejercicio',
    render: (m) => m.ejercicio,
  },
  {
    key: 'fecha_generacion',
    header: 'Fecha generacion',
    render: (m) => formatearFecha(m.fecha_generacion),
    sortable: true,
    sortFn: (a, b) => a.fecha_generacion.localeCompare(b.fecha_generacion),
  },
  {
    key: 'resultado_total',
    header: 'Resultado',
    render: (m) => formatearImporte(m.resultado_total),
    className: 'text-right',
    sortable: true,
    sortFn: (a, b) => a.resultado_total - b.resultado_total,
  },
  {
    key: 'estado',
    header: 'Estado',
    render: (m) => badgeEstado(m.estado),
  },
]

export default function HistoricoPage() {
  const { id } = useParams<{ id: string }>()
  const empresaId = Number(id)

  const [filtroModelo, setFiltroModelo] = useState('todos')
  const [filtroEjercicio, setFiltroEjercicio] = useState('todos')

  const { data: modelos, isLoading } = useQuery({
    queryKey: queryKeys.modelos.historico(empresaId),
    queryFn: () => api.get<ModeloPresentado[]>(`/api/modelos/${empresaId}/historico`),
    enabled: !isNaN(empresaId),
  })

  const lista = modelos ?? []

  // Opciones dinamicas de filtros
  const opcionesModelo = useMemo(() => {
    const unicos = [...new Set(lista.map((m) => m.modelo))].sort()
    return unicos
  }, [lista])

  const opcionesEjercicio = useMemo(() => {
    const unicos = [...new Set(lista.map((m) => m.ejercicio))].sort().reverse()
    return unicos
  }, [lista])

  // Datos filtrados
  const datosFiltrados = useMemo(() => {
    return lista.filter((m) => {
      const pasaModelo = filtroModelo === 'todos' || m.modelo === filtroModelo
      const pasaEjercicio = filtroEjercicio === 'todos' || m.ejercicio === filtroEjercicio
      return pasaModelo && pasaEjercicio
    })
  }, [lista, filtroModelo, filtroEjercicio])

  // KPIs
  const totalGenerados = lista.length
  const presentados = lista.filter((m) => m.estado === 'presentado').length
  const pendientesPresentar = lista.filter((m) => m.estado === 'generado').length
  const importeTotal = lista.reduce((sum, m) => sum + m.resultado_total, 0)

  if (!isLoading && lista.length === 0) {
    return (
      <div>
        <PageHeader titulo="Historico de Modelos" />
        <EstadoVacio
          titulo="Sin modelos generados"
          descripcion="Todavia no se han generado modelos fiscales para esta empresa."
          icono={FileText}
        />
      </div>
    )
  }

  const acciones = (
    <div className="flex gap-2">
      <Select value={filtroModelo} onValueChange={setFiltroModelo}>
        <SelectTrigger className="h-8 w-36 text-sm">
          <SelectValue placeholder="Modelo" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="todos">Todos los modelos</SelectItem>
          {opcionesModelo.map((m) => (
            <SelectItem key={m} value={m}>
              Modelo {m}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select value={filtroEjercicio} onValueChange={setFiltroEjercicio}>
        <SelectTrigger className="h-8 w-36 text-sm">
          <SelectValue placeholder="Ejercicio" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="todos">Todos los ejercicios</SelectItem>
          {opcionesEjercicio.map((e) => (
            <SelectItem key={e} value={e}>
              {e}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )

  return (
    <div className="space-y-6">
      <PageHeader titulo="Historico de Modelos" />

      <div className="grid gap-4 grid-cols-2 lg:grid-cols-4">
        <KPICard
          titulo="Total generados"
          valor={isLoading ? '...' : String(totalGenerados)}
          icono={FileText}
          cargando={isLoading}
        />
        <KPICard
          titulo="Presentados"
          valor={isLoading ? '...' : String(presentados)}
          cargando={isLoading}
        />
        <KPICard
          titulo="Pendientes presentar"
          valor={isLoading ? '...' : String(pendientesPresentar)}
          cargando={isLoading}
        />
        <KPICard
          titulo="Importe total"
          valor={isLoading ? '...' : formatearImporte(importeTotal)}
          cargando={isLoading}
        />
      </div>

      <DataTable
        datos={datosFiltrados}
        columnas={COLUMNAS}
        cargando={isLoading}
        acciones={acciones}
        vacio={
          <EstadoVacio
            titulo="Sin resultados"
            descripcion="No hay modelos que coincidan con los filtros aplicados."
            icono={FileText}
          />
        }
      />
    </div>
  )
}
