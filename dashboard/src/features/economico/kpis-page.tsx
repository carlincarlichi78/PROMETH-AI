// Pagina: KPIs Sectoriales
import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import type { KPI } from '@/types/economico'
import { economicoApi } from './api'
import { StatCard } from '@/components/ui/stat-card'
import { PageTitle } from '@/components/ui/page-title'
import { EmptyState } from '@/components/ui/empty-state'
import { BarChart2 } from 'lucide-react'


function KPICard({ kpi }: { kpi: KPI }) {
  const progreso = kpi.objetivo ? Math.min((kpi.valor / kpi.objetivo) * 100, 100) : null
  const formatValor = () => kpi.unidad === 'euros'
    ? `${kpi.valor.toLocaleString('es-ES', { maximumFractionDigits: 0 })} €`
    : `${kpi.valor.toLocaleString('es-ES', { maximumFractionDigits: 2 })} ${kpi.unidad === 'porcentaje' ? '%' : kpi.unidad}`

  return (
    <div className="rounded-xl border border-border/50 bg-[var(--surface-1)] p-5">
      <div className="text-[13px] font-medium text-muted-foreground uppercase tracking-wide mb-2">
        {kpi.nombre}
      </div>
      <div className={`text-[28px] font-bold tabular-nums leading-none mb-2 ${
        kpi.semaforo === 'verde' ? 'text-[var(--state-success)]' :
        kpi.semaforo === 'amarillo' ? 'text-[var(--state-warning)]' :
        'text-[var(--state-danger)]'
      }`}>
        {formatValor()}
      </div>
      {kpi.objetivo !== null && progreso !== null && (
        <div>
          <div className="flex justify-between text-[11px] text-muted-foreground mb-1">
            <span>Objetivo: {kpi.objetivo} {kpi.unidad === 'porcentaje' ? '%' : kpi.unidad}</span>
            <span>{progreso.toFixed(0)}%</span>
          </div>
          <div className="h-1.5 bg-[var(--surface-3)] rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all"
              style={{
                width: `${progreso}%`,
                background: kpi.semaforo === 'verde' ? 'var(--state-success)' :
                            kpi.semaforo === 'amarillo' ? 'var(--state-warning)' : 'var(--state-danger)',
              }}
            />
          </div>
        </div>
      )}
    </div>
  )
}

export default function KPIsPage() {
  const { id } = useParams<{ id: string }>()
  const empresaId = Number(id)
  const [kpis, setKpis] = useState<KPI[]>([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setCargando(true)
    economicoApi.kpis(empresaId).then((d) => setKpis(d.kpis)).catch((e: Error) => setError(e.message)).finally(() => setCargando(false))
  }, [empresaId])

  if (cargando) {
    return (
      <div className="p-6 max-w-5xl">
        <PageTitle titulo="KPIs Sectoriales" subtitulo="Indicadores clave del ejercicio activo" />
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => <StatCard key={i} titulo="" valor="" cargando />)}
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 max-w-5xl">
      <PageTitle titulo="KPIs Sectoriales" subtitulo="Indicadores clave del ejercicio activo" />
      {error && <p className="text-[var(--state-danger)] text-sm mb-4">Error: {error}</p>}
      {kpis.length === 0 && !error ? (
        <EmptyState
          icono={<BarChart2 className="h-8 w-8" />}
          titulo="Sin KPIs disponibles"
          descripcion="No hay datos de KPIs en este ejercicio."
        />
      ) : (
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
          {kpis.map((kpi) => <KPICard key={kpi.nombre} kpi={kpi} />)}
        </div>
      )}
    </div>
  )
}
