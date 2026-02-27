import { useMemo } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { UserCheck, UserX, Users, Briefcase } from 'lucide-react'
import { api } from '@/lib/api-client'
import { queryKeys } from '@/lib/query-keys'
import { formatearImporte, formatearNumero } from '@/lib/formatters'
import { KPICard } from '@/components/charts/kpi-card'
import { DataTable, type ColumnaTabla } from '@/components/data-table/data-table'
import { PageHeader } from '@/components/page-header'
import { EstadoVacio } from '@/components/estado-vacio'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import type { Trabajador } from '@/types'

const COLUMNAS: ColumnaTabla<Trabajador>[] = [
  {
    key: 'nombre',
    header: 'Nombre',
    render: (t) => <span className="font-medium">{t.nombre}</span>,
    sortable: true,
    sortFn: (a, b) => a.nombre.localeCompare(b.nombre),
  },
  {
    key: 'dni',
    header: 'DNI',
    render: (t) => <span className="font-mono text-sm">{t.dni}</span>,
  },
  {
    key: 'bruto_mensual',
    header: 'Bruto mensual',
    render: (t) => (
      <span className="text-right block">{formatearImporte(t.bruto_mensual)}</span>
    ),
    sortable: true,
    sortFn: (a, b) => (a.bruto_mensual ?? 0) - (b.bruto_mensual ?? 0),
    className: 'text-right',
  },
  {
    key: 'pagas',
    header: 'Pagas',
    render: (t) => (
      <span className="text-right block">{t.pagas != null ? formatearNumero(t.pagas, 0) : '-'}</span>
    ),
    className: 'text-right',
  },
  {
    key: 'activo',
    header: 'Estado',
    render: (t) =>
      t.activo ? (
        <Badge variant="secondary">Activo</Badge>
      ) : (
        <Badge variant="outline" className="text-red-600 border-red-400">
          Baja
        </Badge>
      ),
  },
]

export default function TrabajadoresPage() {
  const { id } = useParams<{ id: string }>()
  const empresaId = Number(id)

  const { data: trabajadores = [], isLoading } = useQuery({
    queryKey: queryKeys.empresas.trabajadores(empresaId),
    queryFn: () => api.get<Trabajador[]>(`/api/rrhh/${empresaId}/trabajadores`),
    enabled: !isNaN(empresaId),
  })

  const activos = useMemo(() => trabajadores.filter((t) => t.activo), [trabajadores])

  const brutoTotal = useMemo(
    () => activos.reduce((acc, t) => acc + (t.bruto_mensual ?? 0), 0),
    [activos]
  )

  const pagasMedia = useMemo(() => {
    const conPagas = trabajadores.filter((t) => t.pagas != null)
    if (conPagas.length === 0) return null
    return conPagas.reduce((acc, t) => acc + (t.pagas ?? 0), 0) / conPagas.length
  }, [trabajadores])

  return (
    <div className="space-y-6">
      <PageHeader
        titulo="Trabajadores"
        descripcion="Gestion del personal"
        acciones={
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <span>
                  <Button variant="outline" size="sm" disabled>
                    <Briefcase className="h-4 w-4 mr-1.5" />
                    Nuevo trabajador
                  </Button>
                </span>
              </TooltipTrigger>
              <TooltipContent>
                <p>En desarrollo</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        }
      />

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          titulo="Total trabajadores"
          valor={String(trabajadores.length)}
          icono={Users}
          cargando={isLoading}
        />
        <KPICard
          titulo="Activos"
          valor={String(activos.length)}
          icono={UserCheck}
          cargando={isLoading}
        />
        <KPICard
          titulo="Bruto mensual total"
          valor={formatearImporte(brutoTotal)}
          icono={Briefcase}
          cargando={isLoading}
        />
        <KPICard
          titulo="Pagas media"
          valor={pagasMedia != null ? formatearNumero(pagasMedia, 1) : '-'}
          icono={UserX}
          cargando={isLoading}
        />
      </div>

      {trabajadores.length === 0 && !isLoading ? (
        <EstadoVacio
          titulo="Sin trabajadores registrados"
          descripcion="No hay trabajadores dados de alta para esta empresa"
          icono={Users}
        />
      ) : (
        <DataTable
          datos={trabajadores}
          columnas={COLUMNAS}
          cargando={isLoading}
          busqueda
          filtroBusqueda={(t, termino) =>
            t.nombre.toLowerCase().includes(termino.toLowerCase()) ||
            t.dni.toLowerCase().includes(termino.toLowerCase())
          }
          vacio="No hay trabajadores registrados"
        />
      )}
    </div>
  )
}
