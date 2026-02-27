import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { BookOpen } from 'lucide-react'
import { api } from '@/lib/api-client'
import { ApiError } from '@/lib/api-client'
import { formatearImporte } from '@/lib/formatters'
import { PageHeader } from '@/components/page-header'
import { EstadoVacio } from '@/components/estado-vacio'
import { DataTable } from '@/components/data-table/data-table'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { ColumnaTabla } from '@/components/data-table/data-table'

interface Subcuenta {
  id: number
  codigo: string
  nombre: string
  saldo_deudor: number
  saldo_acreedor: number
  saldo_neto: number
}

const GRUPOS = [
  { value: 'todos', label: 'Todos los grupos' },
  { value: '1', label: 'Grupo 1 — Financiacion basica' },
  { value: '2', label: 'Grupo 2 — Activo no corriente' },
  { value: '3', label: 'Grupo 3 — Existencias' },
  { value: '4', label: 'Grupo 4 — Acreedores y deudores' },
  { value: '5', label: 'Grupo 5 — Cuentas financieras' },
  { value: '6', label: 'Grupo 6 — Compras y gastos' },
  { value: '7', label: 'Grupo 7 — Ventas e ingresos' },
]

const columnas: ColumnaTabla<Subcuenta>[] = [
  {
    key: 'codigo',
    header: 'Codigo',
    render: (item) => (
      <span className="font-mono text-xs">{item.codigo}</span>
    ),
    sortable: true,
    sortFn: (a, b) => a.codigo.localeCompare(b.codigo),
  },
  {
    key: 'nombre',
    header: 'Nombre',
    render: (item) => <span className="text-sm">{item.nombre}</span>,
  },
  {
    key: 'grupo',
    header: 'Grupo',
    render: (item) => (
      <Badge variant="outline" className="text-xs">
        {item.codigo.charAt(0)}
      </Badge>
    ),
  },
  {
    key: 'saldo_deudor',
    header: 'Saldo deudor',
    render: (item) => (
      <span className="text-right font-mono text-sm">
        {item.saldo_deudor !== 0 ? formatearImporte(item.saldo_deudor) : '-'}
      </span>
    ),
    className: 'text-right',
    sortable: true,
    sortFn: (a, b) => a.saldo_deudor - b.saldo_deudor,
  },
  {
    key: 'saldo_acreedor',
    header: 'Saldo acreedor',
    render: (item) => (
      <span className="text-right font-mono text-sm">
        {item.saldo_acreedor !== 0 ? formatearImporte(item.saldo_acreedor) : '-'}
      </span>
    ),
    className: 'text-right',
    sortable: true,
    sortFn: (a, b) => a.saldo_acreedor - b.saldo_acreedor,
  },
  {
    key: 'saldo_neto',
    header: 'Saldo neto',
    render: (item) => {
      const positivo = item.saldo_neto >= 0
      return (
        <span
          className={`text-right font-mono text-sm font-medium ${
            positivo ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
          }`}
        >
          {formatearImporte(item.saldo_neto)}
        </span>
      )
    },
    className: 'text-right',
    sortable: true,
    sortFn: (a, b) => a.saldo_neto - b.saldo_neto,
  },
]

export default function PlanCuentasPage() {
  const { id } = useParams<{ id: string }>()
  const empresaId = Number(id)
  const [grupo, setGrupo] = useState('todos')

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['contabilidad', empresaId, 'subcuentas'],
    queryFn: () => api.get<Subcuenta[]>(`/api/contabilidad/${empresaId}/subcuentas`),
    retry: (failCount, err) => {
      if (err instanceof ApiError && err.status === 404) return false
      return failCount < 2
    },
  })

  const noDisponible =
    isError && error instanceof ApiError && error.status === 404

  const datosFiltrados = (data ?? []).filter(
    (s) => grupo === 'todos' || s.codigo.charAt(0) === grupo
  )

  return (
    <div className="space-y-6">
      <PageHeader
        titulo="Plan de Cuentas"
        descripcion="Subcuentas del ejercicio con saldos deudor, acreedor y neto"
      />

      {noDisponible ? (
        <EstadoVacio
          titulo="Plan de cuentas no disponible"
          descripcion="Configuralo en FacturaScripts o importa el PGC desde el panel de ejercicios"
          icono={BookOpen}
        />
      ) : (
        <>
          <div className="flex items-center gap-3">
            <Select value={grupo} onValueChange={setGrupo}>
              <SelectTrigger className="w-64 h-8 text-sm">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {GRUPOS.map((g) => (
                  <SelectItem key={g.value} value={g.value} className="text-sm">
                    {g.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {!isLoading && (
              <span className="text-sm text-muted-foreground">
                {datosFiltrados.length} subcuenta{datosFiltrados.length !== 1 ? 's' : ''}
              </span>
            )}
          </div>

          <Card>
            <CardContent className="p-0">
              <DataTable
                datos={datosFiltrados}
                columnas={columnas}
                cargando={isLoading}
                busqueda
                filtroBusqueda={(item, termino) =>
                  item.codigo.includes(termino) ||
                  item.nombre.toLowerCase().includes(termino.toLowerCase())
                }
                filasPorPagina={50}
                vacio="Sin subcuentas para el filtro seleccionado"
              />
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
