/** Particulas decorativas con numeros de subcuentas contables */
const particulas = [
  { texto: '472', top: '12%', left: '8%', delay: '0s', duracion: '7s' },
  { texto: '629', top: '18%', right: '12%', delay: '1.2s', duracion: '6s' },
  { texto: '303', top: '55%', left: '5%', delay: '2.4s', duracion: '8s' },
  { texto: '477', top: '70%', right: '8%', delay: '0.8s', duracion: '7s' },
  { texto: '130', top: '30%', left: '15%', delay: '3.1s', duracion: '6.5s' },
  { texto: '640', top: '40%', right: '18%', delay: '1.8s', duracion: '7.5s' },
  { texto: '572', top: '80%', left: '20%', delay: '0.5s', duracion: '6s' },
  { texto: '111', top: '25%', right: '25%', delay: '2.8s', duracion: '8s' },
  { texto: '600', top: '65%', left: '30%', delay: '3.5s', duracion: '7s' },
  { texto: '347', top: '85%', right: '15%', delay: '1.5s', duracion: '6.5s' },
]

/** SVG llama grande esmeralda + dorado */
function LlamaGrande() {
  return (
    <svg
      viewBox="0 0 40 60"
      fill="none"
      className="w-10 h-15 md:w-14 md:h-20"
      aria-hidden="true"
    >
      {/* Llama exterior esmeralda */}
      <path
        d="M20 3C20 3 8 18 8 34c0 10 5.5 18 12 22 6.5-4 12-12 12-22 0-16-12-31-12-31z"
        fill="#10b981"
      />
      {/* Llama interior dorada */}
      <path
        d="M20 14c0 0-6 10-6 22 0 6 3 11 6 14 3-3 6-8 6-14 0-12-6-22-6-22z"
        fill="#d4a017"
        opacity="0.8"
      />
      {/* Nucleo brillante */}
      <path
        d="M20 26c0 0-3 5-3 12 0 3.5 1.5 6 3 7.5 1.5-1.5 3-4 3-7.5 0-7-3-12-3-12z"
        fill="#f0c040"
        opacity="0.6"
      />
    </svg>
  )
}

function scrollA(href: string) {
  const id = href.replace('#', '')
  const el = document.getElementById(id)
  if (el) {
    el.scrollIntoView({ behavior: 'smooth' })
  }
}

export default function Hero() {
  return (
    <section
      id="inicio"
      className="relative min-h-screen flex items-center justify-center overflow-hidden px-4"
    >
      {/* Particulas flotantes */}
      {particulas.map((p) => (
        <span
          key={p.texto + p.top}
          className="absolute font-heading font-bold text-spice-emerald/15 text-2xl md:text-4xl select-none pointer-events-none animate-float"
          style={{
            top: p.top,
            left: p.left,
            right: p.right,
            animationDelay: p.delay,
            animationDuration: p.duracion,
          }}
        >
          {p.texto}
        </span>
      ))}

      {/* Gradiente radial decorativo */}
      <div
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full pointer-events-none"
        style={{
          background:
            'radial-gradient(circle, rgba(16,185,129,0.08) 0%, transparent 70%)',
        }}
      />

      {/* Contenido centrado */}
      <div className="relative z-10 text-center flex flex-col items-center gap-6 max-w-3xl">
        {/* Logo llama */}
        <LlamaGrande />

        {/* Nombre */}
        <h1 className="text-5xl md:text-7xl font-heading font-bold text-spice-emerald tracking-tight">
          SPICE
        </h1>

        {/* Subtitulo */}
        <p className="text-lg md:text-xl text-spice-text-muted font-body -mt-2">
          Sistema Profesional Inteligente de Contabilidad Evolutiva
        </p>

        {/* Descripcion */}
        <p className="text-base md:text-lg text-spice-text/80 font-body max-w-2xl leading-relaxed">
          Tu despacho recibe facturas, nominas y extractos. SPICE los lee, los
          contabiliza y genera los modelos fiscales. Sin intervencion manual.
        </p>

        {/* CTA */}
        <button
          onClick={() => scrollA('#proceso')}
          className="mt-4 bg-spice-emerald hover:bg-spice-emerald-dark text-white font-body font-semibold px-8 py-4 rounded-xl transition-colors animate-pulse-glow cursor-pointer"
        >
          Ver como funciona
        </button>
      </div>
    </section>
  )
}
