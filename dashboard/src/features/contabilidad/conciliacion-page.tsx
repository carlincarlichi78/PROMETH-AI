import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { RefreshCw } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { PageHeader } from '@/components/page-header'

import {
  useMovimientos,
  useEstadoConciliacion,
  useConciliar,
} from '@/features/conciliacion/api'
import { SubirExtracto } from '@/features/conciliacion/components/subir-extracto'
import { TablaMovimientos } from '@/features/conciliacion/components/tabla-movimientos'

type FiltroEstado = 'todos' | 'pendiente' | 'conciliado' | 'revision'

const FILTROS: { valor: FiltroEstado; etiqueta: string }[] = [
  { valor: 'todos', etiqueta: 'Todos' },
  { valor: 'pendiente', etiqueta: 'Pendientes' },
  { valor: 'conciliado', etiqueta: 'Conciliados' },
  { valor: 'revision', etiqueta: 'Revisión' },
]

export default function ConciliacionPage() {
  const { id } = useParams<{ id: string }>()
  const empresaId = Number(id)
  const [filtro, setFiltro] = useState<FiltroEstado>('todos')

  const estadoQuery = useMovimientos(
    empresaId,
    filtro === 'todos' ? undefined : filtro
  )
  const { data: kpis } = useEstadoConciliacion(empresaId)
  const conciliar = useConciliar(empresaId)

  const kpiItems = kpis
    ? [
        { label: 'Total', valor: kpis.total, color: '' },
        { label: 'Conciliados', valor: kpis.conciliados, color: 'text-green-600' },
        { label: 'Pendientes', valor: kpis.pendientes, color: 'text-yellow-600' },
        { label: '% Conciliado', valor: `${kpis.pct_conciliado}%`, color: 'text-blue-600' },
      ]
    : []

  return (
    <div className="space-y-6">
      <PageHeader
        titulo="Conciliación Bancaria"
        descripcion="Empareja movimientos del extracto bancario con asientos contables"
      />

      {/* Subir extracto */}
      <SubirExtracto empresaId={empresaId} />

      {/* KPIs */}
      {kpis && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {kpiItems.map(({ label, valor, color }) => (
            <Card key={label}>
              <CardHeader className="pb-1 pt-4 px-4">
                <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  {label}
                </CardTitle>
              </CardHeader>
              <CardContent className="pb-4 px-4">
                <p className={`text-2xl font-bold tabular-nums ${color}`}>{valor}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Barra de acciones */}
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="flex gap-1">
          {FILTROS.map(f => (
            <Button
              key={f.valor}
              size="sm"
              variant={filtro === f.valor ? 'default' : 'outline'}
              onClick={() => setFiltro(f.valor)}
            >
              {f.etiqueta}
            </Button>
          ))}
        </div>

        <Button
          size="sm"
          variant="outline"
          disabled={conciliar.isPending}
          onClick={() => conciliar.mutate()}
        >
          <RefreshCw className={`w-4 h-4 mr-2 ${conciliar.isPending ? 'animate-spin' : ''}`} />
          {conciliar.isPending ? 'Conciliando...' : 'Ejecutar conciliación'}
        </Button>
      </div>

      {/* Resultado de última conciliación */}
      {conciliar.isSuccess && (
        <p className="text-sm text-muted-foreground">
          Última ejecución:{' '}
          <span className="font-medium text-foreground">
            {conciliar.data.matches_exactos} exactos
          </span>
          {' + '}
          <span className="font-medium text-foreground">
            {conciliar.data.matches_aproximados} aproximados
          </span>
        </p>
      )}

      {/* Tabla */}
      <TablaMovimientos
        movimientos={estadoQuery.data ?? []}
        isLoading={estadoQuery.isLoading}
      />
    </div>
  )
}
