// dashboard/src/features/advisor/command-center-page.tsx
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { AlertTriangle, TrendingUp, TrendingDown, Plus } from 'lucide-react'
import { advisorApi } from './api'
import type { EmpresaPortfolio } from './types'

function HealthBar({ score }: { score: number }) {
  const color = score >= 70 ? 'var(--adv-verde)' : score >= 40 ? 'var(--adv-accent)' : 'var(--adv-rojo)'
  return (
    <div style={{ height: 6, borderRadius: 3, background: 'var(--adv-surface-2)', overflow: 'hidden' }}>
      <div style={{ width: `${score}%`, height: '100%', background: color, transition: 'width 0.6s ease' }} />
    </div>
  )
}

function VariacionBadge({ pct }: { pct: number }) {
  if (Math.abs(pct) < 0.5) return <span style={{ color: 'var(--adv-text-muted)', fontSize: 11 }}>─</span>
  const color = pct > 0 ? 'var(--adv-verde)' : 'var(--adv-rojo)'
  const Icon = pct > 0 ? TrendingUp : TrendingDown
  return (
    <span style={{ color, fontSize: 11, display: 'flex', alignItems: 'center', gap: 2 }}>
      <Icon size={10} />
      {Math.abs(pct).toFixed(1)}%
    </span>
  )
}

function EmpresaCard({ empresa, onClick }: { empresa: EmpresaPortfolio; onClick: () => void }) {
  return (
    <div
      onClick={onClick}
      style={{
        background: 'var(--adv-surface)',
        border: '1px solid var(--adv-border)',
        borderRadius: 12,
        padding: '16px',
        cursor: 'pointer',
        transition: 'border-color 0.2s, transform 0.15s',
        minWidth: 200,
      }}
      onMouseEnter={e => {
        (e.currentTarget as HTMLDivElement).style.borderColor = 'var(--adv-accent)'
        ;(e.currentTarget as HTMLDivElement).style.transform = 'translateY(-2px)'
      }}
      onMouseLeave={e => {
        (e.currentTarget as HTMLDivElement).style.borderColor = 'var(--adv-border)'
        ;(e.currentTarget as HTMLDivElement).style.transform = 'translateY(0)'
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
        <span style={{ fontWeight: 700, color: 'var(--adv-text)', fontSize: 13, lineHeight: 1.3 }}>
          {empresa.nombre}
        </span>
        <span style={{
          fontSize: 10, padding: '2px 6px', borderRadius: 4,
          background: 'var(--adv-surface-2)', color: 'var(--adv-text-muted)',
        }}>
          {empresa.sector?.split('_')[0] || 'general'}
        </span>
      </div>

      <HealthBar score={empresa.health_score} />
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4, marginBottom: 12 }}>
        <span style={{ fontSize: 10, color: 'var(--adv-text-muted)' }}>Health {empresa.health_score}</span>
      </div>

      <div style={{ marginBottom: 8 }}>
        <div style={{ fontFamily: 'var(--adv-font-data)', fontSize: 22, fontWeight: 700, color: 'var(--adv-text)' }}>
          €{empresa.ventas_hoy.toLocaleString('es-ES', { maximumFractionDigits: 0 })}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 2 }}>
          <span style={{ fontSize: 10, color: 'var(--adv-text-muted)' }}>hoy</span>
          <VariacionBadge pct={empresa.variacion_hoy_pct} />
        </div>
      </div>

      {empresa.alerta_critica && (
        <div style={{
          display: 'flex', alignItems: 'flex-start', gap: 6,
          background: empresa.alerta_critica.severidad === 'alta' ? 'rgba(239,68,68,0.1)' : 'rgba(245,158,11,0.1)',
          borderRadius: 6, padding: '6px 8px',
          borderLeft: `2px solid ${empresa.alerta_critica.severidad === 'alta' ? 'var(--adv-rojo)' : 'var(--adv-accent)'}`,
        }}>
          <AlertTriangle size={11} style={{ color: empresa.alerta_critica.severidad === 'alta' ? 'var(--adv-rojo)' : 'var(--adv-accent)', flexShrink: 0, marginTop: 1 }} />
          <span style={{ fontSize: 10, color: 'var(--adv-text-muted)', lineHeight: 1.4 }}>
            {empresa.alerta_critica.mensaje.substring(0, 60)}...
          </span>
        </div>
      )}
    </div>
  )
}

export default function CommandCenterPage() {
  const navigate = useNavigate()
  const { data, isLoading } = useQuery({
    queryKey: ['advisor-portfolio'],
    queryFn: advisorApi.portfolio,
    refetchInterval: 60_000,
  })

  return (
    <div className="advisor-dark" style={{ minHeight: '100vh', background: 'var(--adv-bg)', padding: '24px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 28 }}>
        <div>
          <h1 style={{ color: 'var(--adv-text)', fontSize: 22, fontWeight: 700, margin: 0 }}>
            Advisor Command Center
          </h1>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
            <div style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--adv-verde)', animation: 'pulse 2s infinite' }} />
            <span style={{ color: 'var(--adv-text-muted)', fontSize: 12 }}>
              LIVE · {new Date().toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}
            </span>
          </div>
        </div>
        <button
          style={{
            background: 'var(--adv-accent)', color: '#000', border: 'none',
            borderRadius: 8, padding: '8px 16px', fontWeight: 600, fontSize: 13, cursor: 'pointer',
            display: 'flex', alignItems: 'center', gap: 6,
          }}
          onClick={() => navigate('/empresa/nueva')}
        >
          <Plus size={14} /> Empresa
        </button>
      </div>

      {/* Portfolio grid */}
      {isLoading ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 16 }}>
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} style={{ height: 180, borderRadius: 12, background: 'var(--adv-surface)', animation: 'pulse 1.5s infinite' }} />
          ))}
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 16 }}>
          {(data?.empresas ?? []).map(emp => (
            <EmpresaCard
              key={emp.id}
              empresa={emp}
              onClick={() => navigate(`/empresa/${emp.id}/advisor`)}
            />
          ))}
        </div>
      )}
    </div>
  )
}
