// dashboard/src/features/advisor/advisor-gate.tsx
import { useTiene, TIER_PREMIUM } from '@/hooks/useTiene'
import { Lock } from 'lucide-react'

export function AdvisorGate({ children }: { children: React.ReactNode }) {
  const tieneAdvisor = useTiene('advisor_premium')

  if (!tieneAdvisor) {
    return (
      <div className="advisor-dark" style={{
        minHeight: '100vh', background: 'var(--adv-bg)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <div style={{ textAlign: 'center', padding: 40 }}>
          <div style={{
            width: 64, height: 64, borderRadius: '50%',
            background: 'var(--adv-surface)', border: '2px solid var(--adv-accent)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            margin: '0 auto 20px',
          }}>
            <Lock size={28} color="var(--adv-accent)" />
          </div>
          <h2 style={{ color: 'var(--adv-text)', fontSize: 20, fontWeight: 700, marginBottom: 8 }}>
            Advisor Intelligence Platform
          </h2>
          <p style={{ color: 'var(--adv-text-muted)', fontSize: 14, marginBottom: 20 }}>
            Disponible en tier {TIER_PREMIUM.charAt(0).toUpperCase() + TIER_PREMIUM.slice(1)}
          </p>
          <a href="/configuracion/plan" style={{
            background: 'var(--adv-accent)', color: '#000',
            padding: '10px 24px', borderRadius: 8, fontWeight: 600,
            fontSize: 14, textDecoration: 'none', display: 'inline-block',
          }}>
            Actualizar a Premium
          </a>
        </div>
      </div>
    )
  }

  return <>{children}</>
}
