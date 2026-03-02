import { Github, CheckCircle2 } from 'lucide-react'
import { useInView } from '../../hooks/useInView'

const badges = [
  'FastAPI',
  'PostgreSQL 16',
  'Docker',
  'GitHub Actions',
  '2413 PASS',
]

export default function HeroTecnologia() {
  const { ref, visible } = useInView()

  return (
    <section className="relative py-24 px-4 overflow-hidden">
      {/* Fondo decorativo */}
      <div
        className="absolute inset-0 pointer-events-none"
        aria-hidden="true"
      >
        <div
          className="absolute top-1/4 left-1/4 w-96 h-96 rounded-full animate-float"
          style={{
            background: 'radial-gradient(circle, rgba(245,158,11,0.07) 0%, transparent 70%)',
          }}
        />
        <div
          className="absolute bottom-1/4 right-1/4 w-72 h-72 rounded-full animate-float"
          style={{
            background: 'radial-gradient(circle, rgba(234,88,12,0.06) 0%, transparent 70%)',
            animationDelay: '2.5s',
          }}
        />
      </div>

      <div
        ref={ref}
        className="relative max-w-4xl mx-auto text-center transition-all duration-700"
        style={{
          opacity: visible ? 1 : 0,
          transform: visible ? 'translateY(0)' : 'translateY(32px)',
        }}
      >
        {/* Etiqueta superior */}
        <span className="inline-block text-xs font-bold bg-prometh-amber/15 text-prometh-amber px-3 py-1 rounded-full mb-8 uppercase tracking-widest">
          Arquitectura tecnica
        </span>

        {/* Titulo principal */}
        <h1 className="text-4xl md:text-6xl font-heading font-bold text-prometh-text mb-6 leading-tight">
          Arquitectura diseñada para{' '}
          <span className="gradient-text">fiabilidad contable</span>
        </h1>

        {/* Subtitulo con metrica */}
        <p className="text-xl md:text-2xl font-heading font-semibold text-prometh-amber mb-4">
          2.413 tests automatizados. 0 fallos. En produccion desde marzo 2026.
        </p>

        {/* Descripcion */}
        <p className="text-prometh-muted text-base md:text-lg leading-relaxed mb-10 max-w-2xl mx-auto">
          Una plataforma SaaS construida con FastAPI, PostgreSQL 16, React 18 y tres motores de IA.
          Cada documento pasa por 7 fases de verificacion antes de registrarse en contabilidad.
        </p>

        {/* CTA */}
        <div className="flex flex-wrap justify-center gap-4 mb-12">
          <a
            href="https://github.com/carlincarlichi78/SPICE"
            target="_blank"
            rel="noopener noreferrer"
            className="btn-primary inline-flex items-center gap-2"
          >
            <Github size={18} />
            Ver en GitHub
          </a>
          <a
            href="#stack"
            className="inline-flex items-center gap-2 px-8 py-3.5 rounded-xl border text-prometh-text font-semibold transition-all hover:border-prometh-amber/50 hover:text-prometh-amber"
            style={{ borderColor: 'rgba(245,158,11,0.25)' }}
          >
            Explorar la arquitectura
          </a>
        </div>

        {/* Badges tecnologicos */}
        <div className="flex flex-wrap justify-center gap-3">
          {badges.map((badge, i) => (
            <span
              key={badge}
              className="inline-flex items-center gap-1.5 glass-card px-4 py-2 text-sm font-medium text-prometh-text transition-all duration-500"
              style={{
                opacity: visible ? 1 : 0,
                transform: visible ? 'translateY(0)' : 'translateY(12px)',
                transitionDelay: `${200 + i * 80}ms`,
              }}
            >
              <CheckCircle2 size={14} className="text-prometh-amber" />
              {badge}
            </span>
          ))}
        </div>
      </div>
    </section>
  )
}
