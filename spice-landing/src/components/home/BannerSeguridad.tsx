import { Link } from 'react-router-dom'
import { Shield, Lock, Server, ArrowRight } from 'lucide-react'

const items = [
  { icono: Shield, texto: 'Multi-tenant con aislamiento total' },
  { icono: Lock,   texto: '2FA + cifrado en tránsito y reposo' },
  { icono: Server, texto: 'Backups diarios · Hetzner Alemania · GDPR' },
]

export default function BannerSeguridad() {
  return (
    <section className="py-12 px-4 bg-prometh-surface/50 border-y border-prometh-border">
      <div className="max-w-5xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
        <div className="flex flex-wrap justify-center md:justify-start gap-6">
          {items.map(({ icono: Icono, texto }) => (
            <div key={texto} className="flex items-center gap-2 text-sm text-prometh-muted">
              <Icono size={16} className="text-prometh-amber shrink-0" />
              {texto}
            </div>
          ))}
        </div>
        <Link to="/seguridad"
          className="whitespace-nowrap flex items-center gap-2 text-prometh-amber text-sm font-semibold hover:text-prometh-amber-light transition-colors">
          Ver arquitectura de seguridad <ArrowRight size={14} />
        </Link>
      </div>
    </section>
  )
}
