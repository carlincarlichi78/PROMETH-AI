import { ArrowRight } from 'lucide-react'

export default function HeroGestorias() {
  return (
    <section className="pt-12 pb-20 px-4">
      <div className="max-w-5xl mx-auto text-center">
        <span className="inline-block text-xs font-bold bg-prometh-amber/15 text-prometh-amber px-3 py-1 rounded-full mb-6 uppercase tracking-widest">
          Para gestorías y despachos
        </span>
        <h1 className="text-4xl md:text-6xl font-heading font-bold text-prometh-text mb-6 leading-tight">
          Tu despacho procesa<br />
          <span className="gradient-text">500 facturas al mes.</span><br />
          PROMETH-AI las contabiliza solas.
        </h1>
        <p className="text-lg text-prometh-muted max-w-2xl mx-auto mb-8 leading-relaxed">
          Elimina el registro manual, reduce los errores a cero y cumple todos los plazos fiscales
          de forma automática. Tú supervisas; PROMETH-AI ejecuta.
        </p>

        {/* Comparativo */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 sm:gap-8 mb-10">
          <div className="glass-card px-6 py-4 text-center border-red-500/30">
            <p className="text-3xl font-heading font-bold text-red-400">10 h</p>
            <p className="text-sm text-prometh-muted mt-1">de registro manual al mes</p>
          </div>
          <ArrowRight className="text-prometh-amber rotate-90 sm:rotate-0" size={28} />
          <div className="glass-card px-6 py-4 text-center border-prometh-amber/40">
            <p className="text-3xl font-heading font-bold text-prometh-amber">15 min</p>
            <p className="text-sm text-prometh-muted mt-1">de supervisión al mes</p>
          </div>
        </div>

        <a href="mailto:hola@prometh-ai.es?subject=Demo gestoria"
          className="btn-primary inline-flex items-center gap-2">
          Solicitar demo para mi despacho <ArrowRight size={16} />
        </a>
      </div>
    </section>
  )
}
