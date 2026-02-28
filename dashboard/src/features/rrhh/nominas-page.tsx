import { useMemo } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { DollarSign, Users, TrendingUp, Calendar } from 'lucide-react'
import { api } from '@/lib/api-client'
import { queryKeys } from '@/lib/query-keys'
import { formatearImporte } from '@/lib/formatters'
import { KPICard } from '@/components/charts/kpi-card'
import { PageHeader } from '@/components/page-header'
import { EstadoVacio } from '@/components/estado-vacio'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import type { Trabajador } from '@/types'

export default function NominasPage() {
  const { id } = useParams<{ id: string }>()
  const empresaId = Number(id)

  const { data: trabajadores = [], isLoading } = useQuery({
    queryKey: queryKeys.empresas.trabajadores(empresaId),
    queryFn: () => api.get<Trabajador[]>(`/api/empresas/${empresaId}/trabajadores`),
    enabled: !isNaN(empresaId),
  })

  const activos = useMemo(() => trabajadores.filter((t) => t.activo), [trabajadores])

  const masaSalarial = useMemo(
    () => activos.reduce((acc, t) => acc + (t.bruto_mensual ?? 0), 0),
    [activos]
  )

  const costeEmpresa = useMemo(() => masaSalarial * 1.35, [masaSalarial])

  return (
    <div className="space-y-6">
      <PageHeader
        titulo="Nominas"
        descripcion="Gestion de nominas del personal"
      />

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          titulo="Trabajadores activos"
          valor={String(activos.length)}
          icono={Users}
          cargando={isLoading}
        />
        <KPICard
          titulo="Masa salarial mensual"
          valor={formatearImporte(masaSalarial)}
          icono={DollarSign}
          cargando={isLoading}
        />
        <KPICard
          titulo="Coste empresa estimado"
          valor={formatearImporte(costeEmpresa)}
          descripcion="+35% SS"
          icono={TrendingUp}
          cargando={isLoading}
        />
        <KPICard
          titulo="Nominas pendientes"
          valor="0"
          icono={Calendar}
          cargando={isLoading}
        />
      </div>

      <Card>
        <CardContent className="pt-4 pb-2">
          <p className="text-sm text-muted-foreground">
            La generacion de nominas se realiza a traves de FacturaScripts. Este modulo muestra un resumen de los datos del personal.
          </p>
        </CardContent>
      </Card>

      {activos.length === 0 && !isLoading ? (
        <EstadoVacio
          titulo="Sin trabajadores registrados"
          descripcion="No hay trabajadores activos para esta empresa"
          icono={Users}
        />
      ) : (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Trabajadores activos</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nombre</TableHead>
                  <TableHead className="text-right">Bruto mensual</TableHead>
                  <TableHead className="text-right">Pagas</TableHead>
                  <TableHead className="text-right">Coste empresa</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoading
                  ? Array.from({ length: 3 }).map((_, i) => (
                      <TableRow key={i}>
                        <TableCell colSpan={4} className="h-10 bg-muted/20 animate-pulse" />
                      </TableRow>
                    ))
                  : activos.map((t) => (
                      <TableRow key={t.id}>
                        <TableCell className="font-medium">{t.nombre}</TableCell>
                        <TableCell className="text-right">
                          {formatearImporte(t.bruto_mensual)}
                        </TableCell>
                        <TableCell className="text-right">
                          {t.pagas ?? '-'}
                        </TableCell>
                        <TableCell className="text-right text-muted-foreground">
                          {formatearImporte(t.bruto_mensual != null ? t.bruto_mensual * 1.35 : null)}
                        </TableCell>
                      </TableRow>
                    ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
