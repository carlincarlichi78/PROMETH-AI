import { Link } from 'react-router-dom'
import LogoPrometh from '../shared/LogoPrometh'

const particulas = [
  { texto: 'PDF', top: '15%', left: '7%',  delay: '0s',   dur: '7s' },
  { texto: '303', top: '20%', right: '10%', delay: '1.2s', dur: '6s' },
  { texto: 'IVA', top: '55%', left: '5%',  delay: '2.4s', dur: '8s' },
  { texto: '347', top: '70%', right: '8%', delay: '0.8s', dur: '7s' },
  { texto: '130', top: '35%', left: '14%', delay: '3.1s', dur: '6.5s' },
  { texto: 'OCR', top: '42%', right: '17%',delay: '1.8s', dur: '7.5s' },
  { texto: '472', top: '80%', left: '20%', delay: '0.5s', dur: '6s' },
  { texto: '111', top: '25%', right: '25%',delay: '2.8s', dur: '8s' },
  { texto: 'XML', top: '62%', left: '28%', delay: '3.5s', dur: '7s' },
  { texto: '390', top: '85%', right: '15%',delay: '1.5s', dur: '6.5s' },
]

export default function Hero() {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden px-4">
      {/* Partículas flotantes */}
      {particulas.map(p => (
        <span key={p.texto + p.top}
          className="absolute font-heading font-bold text-prometh-amber/10 text-2xl md:text-4xl select-none pointer-events-none animate-float"
          style={{ top: p.top, left: p.left, right: p.right, animationDelay: p.delay, animationDuration: p.dur }}>
          {p.texto}
        </span>
      ))}

      {/* Glow radial central */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[700px] rounded-full pointer-events-none"
        style={{ background: 'radial-gradient(circle, rgba(245,158,11,0.07) 0%, transparent 70%)' }} />

      {/* Contenido */}
      <div className="relative z-10 text-center flex flex-col items-center gap-6 max-w-4xl animate-fade-in-up">
        <LogoPrometh size="lg" />

        <h1 className="text-5xl md:text-7xl font-heading font-bold text-prometh-text tracking-tight leading-tight">
          La plataforma contable<br />
          <span className="gradient-text">inteligente para gestorías</span>
        </h1>

        <p className="text-lg md:text-xl text-prometh-muted max-w-2xl leading-relaxed">
          PROMETH-AI lee facturas, nóminas y extractos, los contabiliza en FacturaScripts
          y genera los modelos fiscales. Sin intervención manual.
        </p>

        <p className="text-sm text-prometh-muted/70">
          Para gestorías · Asesores fiscales · Empresas
        </p>

        <div className="flex flex-col sm:flex-row gap-4 mt-2">
          <a href="mailto:hola@prometh-ai.es"
            className="btn-primary animate-pulse-amber text-center">
            Solicitar demo
          </a>
          <button
            onClick={() => document.getElementById('perfiles')?.scrollIntoView({ behavior: 'smooth' })}
            className="px-8 py-3.5 rounded-xl border border-prometh-border text-prometh-text font-semibold hover:border-prometh-amber/50 transition-colors">
            Ver mi perfil
          </button>
          <Link to="/tecnologia"
            className="px-8 py-3.5 rounded-xl border border-prometh-border text-prometh-text font-semibold hover:border-prometh-amber/50 transition-colors">
            Ver tecnología
          </Link>
        </div>
      </div>

      {/* Indicador scroll */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 opacity-50">
        <div className="w-0.5 h-8 bg-gradient-to-b from-prometh-amber to-transparent" />
      </div>
    </section>
  )
}
