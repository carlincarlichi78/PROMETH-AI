// Home — Centro de Operaciones: vista panorámica de toda la cartera
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Plus } from 'lucide-react'
import { api } from '@/lib/api-client'
import { queryKeys } from '@/lib/query-keys'
import { StatCard } from '@/components/ui/stat-card'
import { PageTitle } from '@/components/ui/page-title'
import { EmpresaCard } from './empresa-card'
import { useEstadisticasGlobales } from './api'
import type { Empresa } from '@/types'

function BarraEstadoGlobal() {
  const { data, isLoading } = useEstadisticasGlobales()

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-px rounded-xl overflow-hidden border border-border/50 mb-6 animate-pulse">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="bg-[var(--surface-1)] h-16" />
        ))}
      </div>
    )
  }

  const stats = data ?? {
    total_clientes: 5,
    docs_pendientes_total: 0,
    alertas_urgentes: 0,
    proximo_deadline: null,
    volumen_gestionado: 0,
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-5 gap-px rounded-xl overflow-hidden border border-border/50 mb-6">
      {[
        { label: 'Clientes activos', valor: stats.total_clientes.toString(), icono: '🏢' },
        { label: 'Docs pendientes', valor: stats.docs_pendientes_total.toLocaleString('es'), icono: '📥' },
        {
          label: 'Alertas urgentes',
          valor: stats.alertas_urgentes.toString(),
          icono: '⚠️',
          clase: stats.alertas_urgentes > 0 ? 'text-[var(--state-danger)]' : '',
        },
        {
          label: stats.proximo_deadline
            ? `${stats.proximo_deadline.modelo} · ${stats.proximo_deadline.dias}d`
            : 'Sin deadline',
          valor: stats.proximo_deadline?.fecha ?? '—',
          icono: '📅',
        },
        {
          label: 'Volumen gestionado',
          valor: `${(stats.volumen_gestionado / 1_000_000).toFixed(1)}M€`,
          icono: '💰',
        },
      ].map((stat) => (
        <div key={stat.label} className="bg-[var(--surface-1)] px-4 py-3 flex flex-col justify-between">
          <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">
            {stat.icono} {stat.label}
          </span>
          <span className={`text-[18px] font-bold tabular-nums ${stat.clase ?? ''}`}>
            {stat.valor}
          </span>
        </div>
      ))}
    </div>
  )
}

export function SelectorEmpresa() {
  const navigate = useNavigate()

  const { data: empresas, isLoading } = useQuery({
    queryKey: queryKeys.empresas.todas,
    queryFn: () => api.get<Empresa[]>('/api/empresas'),
  })

  const empresasActivas = empresas?.filter((e) => e.activa) ?? []
  const empresasInactivas = empresas?.filter((e) => !e.activa) ?? []

  if (isLoading) {
    return (
      <div className="p-6 max-w-6xl">
        <PageTitle titulo="Panel Principal" subtitulo="Centro de operaciones" />
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-px rounded-xl overflow-hidden border border-border/50 mb-6 animate-pulse">
          {Array.from({ length: 5 }).map((_, i) => <div key={i} className="bg-[var(--surface-1)] h-16" />)}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <StatCard key={i} titulo="" valor="" cargando className="min-h-[280px]" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 max-w-6xl">
      <PageTitle titulo="Panel Principal" subtitulo="Centro de operaciones de tu cartera" />

      <BarraEstadoGlobal />

      <div className="flex items-center justify-between mb-4">
        <h2 className="text-[13px] font-medium text-muted-foreground uppercase tracking-wide">
          Empresas activas
        </h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {empresasActivas.map((empresa) => (
          <EmpresaCard key={empresa.id} empresa={empresa} />
        ))}

        <button
          type="button"
          onClick={() => navigate('/directorio')}
          className="rounded-xl border-2 border-dashed border-border/50
                     hover:border-[var(--primary)]/50 hover:bg-[var(--surface-1)]/50
                     transition-all duration-150 flex flex-col items-center justify-center
                     gap-2 p-8 text-muted-foreground hover:text-foreground min-h-[280px]"
        >
          <Plus className="h-8 w-8" />
          <span className="text-[14px] font-medium">Nuevo cliente</span>
        </button>
      </div>

      {empresasInactivas.length > 0 && (
        <div className="mt-8">
          <h2 className="text-[13px] font-medium text-muted-foreground uppercase tracking-wide mb-3">
            Inactivas
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 opacity-50">
            {empresasInactivas.map((empresa) => (
              <EmpresaCard key={empresa.id} empresa={empresa} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
