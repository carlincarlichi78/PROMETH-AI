import PageLayout from '../components/layout/PageLayout'
import { Check, ArrowRight } from 'lucide-react'

const planes = [
  {
    perfil: 'Plan Básico',
    subtitulo: 'Para gestorías pequeñas',
    precio: 'Consultar',
    descripcion: '1 empresa gestionada',
    items: [
      'Pipeline automático (FC, FV, NC, SUM)',
      '28 modelos fiscales automáticos',
      'Portal cliente básico',
      'Soporte por email',
    ],
    cta: 'Solicitar demo',
    href: 'mailto:hola@prometh-ai.es?subject=Plan Basico',
    destacado: false,
  },
  {
    perfil: 'Plan Pro',
    subtitulo: 'Gestorías en crecimiento',
    precio: 'Consultar',
    descripcion: 'Hasta 10 empresas gestionadas',
    items: [
      'Todo del plan Básico',
      'App móvil para clientes',
      'Ingesta automática por email',
      'Onboarding hasta 10 empresas/mes',
      'Soporte prioritario',
    ],
    cta: 'Solicitar demo',
    href: 'mailto:hola@prometh-ai.es?subject=Plan Pro',
    destacado: true,
  },
  {
    perfil: 'Plan Premium',
    subtitulo: 'Gestorías y asesores avanzados',
    precio: 'Consultar',
    descripcion: 'Empresas ilimitadas',
    items: [
      'Todo del plan Pro',
      'Advisor Intelligence Platform',
      'Benchmarking sectorial (P25/P50/P75)',
      'Briefings semanales con IA',
      'Onboarding masivo ilimitado',
      'Acceso API + SLA 99.9%',
    ],
    cta: 'Hablar con ventas',
    href: 'mailto:hola@prometh-ai.es?subject=Plan Premium',
    destacado: false,
  },
]

export default function Precios() {
  return (
    <PageLayout>
      <section className="pt-12 pb-20 px-4">
        <div className="max-w-3xl mx-auto text-center mb-16">
          <h1 className="text-4xl md:text-5xl font-heading font-bold text-prometh-text mb-4">
            Planes y precios
          </h1>
          <p className="text-prometh-muted text-lg">
            Adaptados a cada perfil. Sin permanencia. Sin sorpresas.
          </p>
        </div>

        <div className="max-w-5xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-6">
          {planes.map(p => (
            <div key={p.perfil}
              className={`glass-card p-8 flex flex-col ${p.destacado ? 'border-prometh-amber/50' : ''}`}>
              {p.destacado && (
                <span className="text-xs font-bold bg-prometh-amber/20 text-prometh-amber px-2 py-1 rounded-full mb-4 self-start">
                  Más completo
                </span>
              )}
              <h2 className="text-xl font-heading font-bold text-prometh-text">{p.perfil}</h2>
              <p className="text-prometh-muted text-sm mb-4">{p.subtitulo}</p>
              <div className="mb-1">
                <span className="text-3xl font-heading font-bold gradient-text">{p.precio}</span>
              </div>
              <p className="text-prometh-muted text-xs mb-6">{p.descripcion}</p>
              <ul className="space-y-2 flex-1 mb-8">
                {p.items.map(item => (
                  <li key={item} className="flex items-center gap-2 text-sm text-prometh-muted">
                    <Check size={14} className="text-prometh-amber shrink-0" />
                    {item}
                  </li>
                ))}
              </ul>
              <a href={p.href}
                className={`flex items-center justify-center gap-2 py-3 rounded-xl font-semibold text-sm transition-colors ${
                  p.destacado ? 'btn-primary' : 'border border-prometh-border text-prometh-text hover:border-prometh-amber/50'
                }`}>
                {p.cta} <ArrowRight size={14} />
              </a>
            </div>
          ))}
        </div>

        <p className="text-center text-prometh-muted text-sm mt-8">
          ¿Necesitas algo específico?{' '}
          <a href="mailto:hola@prometh-ai.es" className="text-prometh-amber hover:text-prometh-amber-light">
            Escríbenos
          </a>{' '}
          y lo diseñamos juntos.
        </p>
      </section>
    </PageLayout>
  )
}
