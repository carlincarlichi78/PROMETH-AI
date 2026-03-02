import { Smartphone, BarChart2, Mail, Building2 } from 'lucide-react'
import { useInView } from '../../hooks/useInView'

const modulos = [
  {
    icono: Smartphone,
    titulo: 'App móvil nativa',
    descripcion:
      'Tus clientes suben documentos desde el móvil. Fotos de facturas, tickets, extractos. La IA los procesa automáticamente sin que el cliente toque nada más.',
    badge: 'iOS + Android',
  },
  {
    icono: BarChart2,
    titulo: 'Advisor Intelligence',
    descripcion:
      'Benchmarking sectorial automático. Compara el rendimiento de cada empresa contra su sector (P25, P50, P75). Briefings semanales generados por IA para cada gestor.',
    badge: 'Solo plan Premium',
  },
  {
    icono: Mail,
    titulo: 'Facturas por email',
    descripcion:
      'Conecta el buzón de la gestoría. Los proveedores envían facturas por email y PROMETH-AI las extrae, procesa y contabiliza automáticamente.',
    badge: 'Zoho Mail integrado',
  },
  {
    icono: Building2,
    titulo: 'Onboarding masivo',
    descripcion:
      'Da de alta decenas de empresas a la vez cargando sus escrituras y formularios 036/037. La IA extrae CIF, denominación, administradores y configura cada empresa.',
    badge: 'Parseo OCR 036/037',
  },
]

export default function NuevaGeneracion() {
  const { ref, visible } = useInView()

  return (
    <section className="py-20 px-4 bg-prometh-surface/30">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-12">
          <span className="text-xs uppercase tracking-widest text-prometh-amber font-bold mb-3 block">
            Plataforma completa
          </span>
          <h2 className="text-3xl md:text-4xl font-heading font-bold text-prometh-text mb-3">
            Una plataforma. Cuatro módulos de vanguardia.
          </h2>
          <p className="text-prometh-muted text-lg max-w-2xl mx-auto">
            Más allá de la contabilidad automática: herramientas que transforman cómo operas tu gestoría.
          </p>
        </div>

        <div
          ref={ref}
          className={`grid grid-cols-1 md:grid-cols-2 gap-6 transition-all duration-700 ${
            visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-6'
          }`}
        >
          {modulos.map((m, i) => {
            const Icono = m.icono
            return (
              <div
                key={m.titulo}
                className="glass-card p-8 flex flex-col gap-4 hover:border-prometh-amber/40 transition-all duration-300 hover:-translate-y-0.5"
                style={{ transitionDelay: `${i * 80}ms` }}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="w-12 h-12 rounded-xl bg-prometh-amber/10 flex items-center justify-center shrink-0">
                    <Icono className="text-prometh-amber" size={24} />
                  </div>
                  <span className="text-xs font-bold bg-prometh-amber/15 text-prometh-amber px-2.5 py-1 rounded-full whitespace-nowrap">
                    {m.badge}
                  </span>
                </div>
                <div>
                  <h3 className="text-xl font-heading font-bold text-prometh-text mb-2">
                    {m.titulo}
                  </h3>
                  <p className="text-prometh-muted text-sm leading-relaxed">
                    {m.descripcion}
                  </p>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
