// Pagina: Credit Scoring
import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import type { ScoringEmpresa } from '@/types/economico'
import { economicoApi } from './api'
import { PageTitle } from '@/components/ui/page-title'
import { EmptyState } from '@/components/ui/empty-state'
import { Shield } from 'lucide-react'

function ScoreBadge({ puntuacion }: { puntuacion: number }) {
  const cls = puntuacion >= 70
    ? 'bg-[var(--state-success)]/20 border-[var(--state-success)] text-[var(--state-success)]'
    : puntuacion >= 40
    ? 'bg-[var(--state-warning)]/20 border-[var(--state-warning)] text-[var(--state-warning)]'
    : 'bg-[var(--state-danger)]/20 border-[var(--state-danger)] text-[var(--state-danger)]'
  return (
    <div className={`w-10 h-10 rounded-full border-2 flex items-center justify-center font-bold text-[13px] flex-shrink-0 ${cls}`}>
      {puntuacion}
    </div>
  )
}

export default function ScoringPage() {
  const { id } = useParams<{ id: string }>()
  const empresaId = Number(id)
  const [tipo, setTipo] = useState<'proveedor' | 'cliente'>('proveedor')
  const [datos, setDatos] = useState<ScoringEmpresa | null>(null)
  const [cargando, setCargando] = useState(true)

  useEffect(() => {
    setCargando(true)
    economicoApi.scoring(empresaId, tipo).then(setDatos).catch(() => {}).finally(() => setCargando(false))
  }, [empresaId, tipo])

  return (
    <div className="p-6 max-w-3xl">
      <PageTitle titulo="Credit Scoring" subtitulo="Puntuación de solvencia de clientes y proveedores" />

      <div className="flex gap-2 mb-6">
        {(['proveedor', 'cliente'] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTipo(t)}
            className={`px-4 py-1.5 rounded-full text-sm border transition-all ${
              tipo === t
                ? 'bg-primary text-primary-foreground border-primary font-semibold'
                : 'border-border text-muted-foreground hover:border-primary/50'
            }`}
          >
            {t === 'proveedor' ? 'Proveedores' : 'Clientes'}
          </button>
        ))}
      </div>

      {cargando && (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-14 rounded-lg bg-[var(--surface-1)] animate-pulse" />
          ))}
        </div>
      )}

      {!cargando && datos?.scoring.length === 0 && (
        <EmptyState
          icono={<Shield className="h-8 w-8" />}
          titulo="Sin datos de scoring"
          descripcion="Los scores se calculan con historial de pagos. Registra más operaciones para ver puntuaciones."
        />
      )}

      {!cargando && datos && datos.scoring.length > 0 && (
        <div className="space-y-2">
          {datos.scoring.map((s) => (
            <div key={s.entidad_id} className="bg-[var(--surface-1)] border border-border/50 rounded-lg px-4 py-3 flex items-center gap-4">
              <ScoreBadge puntuacion={s.puntuacion} />
              <div className="flex-1 min-w-0">
                <span className="font-semibold text-sm">Entidad #{s.entidad_id}</span>
                {s.fecha && (
                  <span className="text-[12px] text-muted-foreground ml-2">
                    {new Date(s.fecha).toLocaleDateString('es-ES')}
                  </span>
                )}
              </div>
              <div className="text-[12px] text-muted-foreground text-right">
                {Object.entries(s.factores).map(([k, v]) => `${k}: ${v}`).join(' · ') || 'Sin factores'}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
