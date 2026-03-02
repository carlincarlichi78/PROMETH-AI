import { Link } from 'react-router-dom'
import { Building2, BarChart3, User, ArrowRight } from 'lucide-react'

const perfiles = [
  {
    href: '/gestorias',
    icono: Building2,
    titulo: 'Soy Gestoría',
    subtitulo: 'Automatiza tu despacho',
    descripcion: 'Contabiliza las facturas de todos tus clientes sin intervención manual. Pipeline OCR + 28 modelos fiscales.',
    items: [
      'Multi-empresa con aislamiento',
      'Triple IA: Mistral + GPT-4o + Gemini',
      '28 modelos fiscales automatizados',
      'App móvil para clientes',
      'Onboarding masivo de empresas',
    ],
    color: 'hover:border-prometh-amber/50',
    badge: 'Más popular',
  },
  {
    href: '/asesores',
    icono: BarChart3,
    titulo: 'Soy Asesor Fiscal',
    subtitulo: 'Análisis 360°',
    descripcion: 'Visión económico-financiera y fiscal completa en tiempo real. Sin exportar a Excel.',
    items: [
      'PyG y ratios automáticos',
      'Conciliación bancaria',
      'Dashboard con 16 módulos',
      'Advisor Intelligence Platform',
      'Benchmarking sectorial automático',
    ],
    color: 'hover:border-orange-500/50',
    badge: null,
  },
  {
    href: '/clientes',
    icono: User,
    titulo: 'Soy Cliente/Empresa',
    subtitulo: 'Conoce tu negocio',
    descripcion: 'Visibilidad total de tu empresa sin ser experto contable. Alertas, documentos y estado en tiempo real.',
    items: [
      'Portal web + App móvil',
      'Alertas de vencimientos',
      'Propuestas adaptadas a tu necesidad',
      'Visibilidad en tiempo real',
    ],
    color: 'hover:border-prometh-amber/30',
    badge: null,
  },
]

export default function SelectorPerfil() {
  return (
    <section id="perfiles" className="py-20 px-4">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-12">
          <h2 className="text-3xl md:text-4xl font-heading font-bold text-prometh-text mb-3">
            ¿Cuál es tu perfil?
          </h2>
          <p className="text-prometh-muted text-lg">
            PROMETH-AI se adapta a tu rol y necesidades específicas
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {perfiles.map(p => {
            const Icono = p.icono
            return (
              <Link key={p.href} to={p.href}
                className={`glass-card p-8 flex flex-col gap-4 transition-all duration-300 group ${p.color} hover:-translate-y-1`}>
                {p.badge && (
                  <span className="self-start text-xs font-bold bg-prometh-amber/20 text-prometh-amber px-2 py-1 rounded-full">
                    {p.badge}
                  </span>
                )}
                <div className="w-12 h-12 rounded-xl bg-prometh-amber/10 flex items-center justify-center group-hover:bg-prometh-amber/20 transition-colors">
                  <Icono className="text-prometh-amber" size={24} />
                </div>
                <div>
                  <p className="text-prometh-muted text-sm mb-1">{p.subtitulo}</p>
                  <h3 className="text-xl font-heading font-bold text-prometh-text">{p.titulo}</h3>
                </div>
                <p className="text-prometh-muted text-sm leading-relaxed flex-1">{p.descripcion}</p>
                <ul className="space-y-2">
                  {p.items.map(item => (
                    <li key={item} className="flex items-center gap-2 text-xs text-prometh-muted">
                      <div className="w-1.5 h-1.5 rounded-full bg-prometh-amber shrink-0" />
                      {item}
                    </li>
                  ))}
                </ul>
                <div className="flex items-center gap-2 text-prometh-amber text-sm font-semibold mt-2">
                  Ver propuesta <ArrowRight size={16} className="group-hover:translate-x-1 transition-transform" />
                </div>
              </Link>
            )
          })}
        </div>
      </div>
    </section>
  )
}
