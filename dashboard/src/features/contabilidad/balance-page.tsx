import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Scale, Building, PiggyBank } from 'lucide-react'
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { api } from '@/lib/api-client'
import { queryKeys } from '@/lib/query-keys'
import { formatearImporte } from '@/lib/formatters'
import { PageHeader } from '@/components/page-header'
import { KPICard } from '@/components/charts/kpi-card'
import { ChartCard } from '@/components/charts/chart-card'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { Balance } from '@/types'

const COLORES = ['#ef4444', '#22c55e']

export default function BalancePage() {
  const { id } = useParams<{ id: string }>()
  const empresaId = Number(id)

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.contabilidad.balance(empresaId),
    queryFn: () => api.get<Balance>(`/api/contabilidad/${empresaId}/balance`),
  })

  const datosPie = data
    ? [
        { name: 'Pasivo', value: Math.abs(data.pasivo) },
        { name: 'Patrimonio Neto', value: Math.abs(data.patrimonio_neto) },
      ]
    : []

  return (
    <div className="space-y-6">
      <PageHeader
        titulo="Balance de Situacion"
        descripcion="Situacion patrimonial — activo, pasivo y patrimonio neto"
      />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <KPICard
          titulo="Activo total"
          valor={formatearImporte(data?.activo)}
          icono={Building}
          descripcion="Bienes y derechos de la empresa"
          cargando={isLoading}
        />
        <KPICard
          titulo="Pasivo total"
          valor={formatearImporte(data?.pasivo)}
          icono={Scale}
          descripcion="Obligaciones y deudas"
          cargando={isLoading}
        />
        <KPICard
          titulo="Patrimonio neto"
          valor={formatearImporte(data?.patrimonio_neto)}
          icono={PiggyBank}
          descripcion="Capital propio"
          cargando={isLoading}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ChartCard
          titulo="Estructura de financiacion (Pasivo vs PN)"
          cargando={isLoading}
          altura={280}
        >
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={datosPie}
                cx="50%"
                cy="50%"
                innerRadius={70}
                outerRadius={110}
                paddingAngle={3}
                dataKey="value"
              >
                {datosPie.map((_, index) => (
                  <Cell key={index} fill={COLORES[index % COLORES.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(value: number | undefined) => formatearImporte(value)} />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>

        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Activo</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Total activo</span>
                  <span className="font-semibold">{formatearImporte(data?.activo)}</span>
                </div>
                <div className="h-2 bg-muted rounded-full overflow-hidden">
                  <div className="h-full bg-blue-500 rounded-full w-full" />
                </div>
                <p className="text-xs text-muted-foreground">
                  Suma de activo corriente y no corriente
                </p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Pasivo y Patrimonio Neto</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {data ? (
                  <>
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">Pasivo</span>
                      <span className="font-medium text-red-600 dark:text-red-400">
                        {formatearImporte(data.pasivo)}
                      </span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">Patrimonio neto</span>
                      <span className="font-medium text-green-600 dark:text-green-400">
                        {formatearImporte(data.patrimonio_neto)}
                      </span>
                    </div>
                    <div className="border-t pt-2 flex justify-between text-sm font-semibold">
                      <span>Total P+PN</span>
                      <span>{formatearImporte(data.pasivo + data.patrimonio_neto)}</span>
                    </div>
                  </>
                ) : (
                  <p className="text-sm text-muted-foreground">Sin datos disponibles</p>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
