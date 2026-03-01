import { Link } from 'react-router-dom'
import LogoPrometh from '../shared/LogoPrometh'

export default function Hero() {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden px-4">

      {/* ─── Orbe 1 — ámbar grande, top-right ─── */}
      <div aria-hidden="true" className="hero-orb orb-amber" />

      {/* ─── Orbe 2 — violeta, bottom-left ─── */}
      <div aria-hidden="true" className="hero-orb orb-violet" />

      {/* ─── Orbe 3 — naranja, center-left ─── */}
      <div aria-hidden="true" className="hero-orb orb-orange" />

      {/* ─── Orbe 4 — cyan, top-left ─── */}
      <div aria-hidden="true" className="hero-orb orb-cyan" />

      {/* ─── Grid de puntos ─── */}
      <div aria-hidden="true" className="hero-dot-grid" />

      {/* ─── Wrapper con shimmer border ─── */}
      <div className="hero-shimmer-wrap animate-fade-in-up max-w-4xl w-full mx-auto">
        {/* Borde giratorio */}
        <div aria-hidden="true" className="hero-border-glow" />

        {/* Panel glassmorphism */}
        <div className="hero-panel text-center flex flex-col items-center gap-6 py-16 px-8 md:px-16">

          <LogoPrometh size="lg" />

          <h1 className="text-5xl md:text-7xl font-heading font-bold text-prometh-text tracking-tight leading-tight">
            Tu contabilidad,<br />
            <span className="gradient-text">en piloto automático</span>
          </h1>

          <p className="text-lg md:text-xl text-prometh-muted max-w-2xl leading-relaxed">
            IA que lee facturas, nóminas y extractos, los contabiliza en FacturaScripts
            y genera los modelos fiscales. Sin intervención manual.
          </p>

          <p className="text-xs text-prometh-muted/60 tracking-widest uppercase font-medium">
            Gestorías · Asesores fiscales · Empresas
          </p>

          <div className="flex flex-col sm:flex-row gap-4 mt-2">
            <button
              type="button"
              onClick={() => document.getElementById('perfiles')?.scrollIntoView({ behavior: 'smooth' })}
              className="btn-primary animate-pulse-amber">
              Ver mi perfil
            </button>
            <Link to="/como-funciona"
              className="px-8 py-3.5 rounded-xl border border-prometh-border text-prometh-text font-semibold hover:border-prometh-amber/50 hover:bg-prometh-amber/5 transition-all duration-300">
              Ver cómo funciona
            </Link>
          </div>

        </div>
      </div>

      {/* ─── Indicador scroll ─── */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2">
        <div className="hero-scroll-line" />
        <div className="hero-scroll-dot" />
      </div>

    </section>
  )
}
