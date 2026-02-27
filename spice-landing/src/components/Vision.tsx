import { useInView } from '../hooks/useInView'
import { useCountUp } from '../hooks/useCountUp'
import { metricas } from '../data/metricas'

function MetricaCard({ valor, sufijo, etiqueta, delay }: {
  valor: number
  sufijo: string
  etiqueta: string
  delay: number
}) {
  const { ref, visible } = useInView()
  const animado = useCountUp(valor, visible)

  return (
    <div
      ref={ref}
      className="glass-card p-6 text-center transition-all duration-500"
      style={{
        opacity: visible ? 1 : 0,
        transform: visible ? 'translateY(0)' : 'translateY(24px)',
        transitionDelay: `${delay}ms`,
      }}
    >
      <p className="text-4xl font-heading text-spice-emerald font-bold">
        {animado}
        {sufijo && <span>{sufijo}</span>}
      </p>
      <p className="mt-2 text-spice-text-muted text-sm">{etiqueta}</p>
    </div>
  )
}

export default function Vision() {
  const { ref: seccionRef, visible: seccionVisible } = useInView()

  return (
    <section id="vision" className="py-20 px-4">
      {/* Frase destacada */}
      <div
        ref={seccionRef}
        className="max-w-3xl mx-auto text-center mb-16 transition-all duration-700"
        style={{
          opacity: seccionVisible ? 1 : 0,
          transform: seccionVisible ? 'translateY(0)' : 'translateY(24px)',
        }}
      >
        <p className="text-spice-gold text-xl md:text-2xl italic font-body leading-relaxed">
          &ldquo;Recibes los documentos. SPICE los contabiliza. Tu supervisas y presentas.&rdquo;
        </p>
      </div>

      {/* Grid de metricas: 2 columnas en mobile, 3 en desktop */}
      <div className="max-w-4xl mx-auto grid grid-cols-2 md:grid-cols-3 gap-4 md:gap-6">
        {metricas.map((metrica, i) => (
          <MetricaCard
            key={metrica.etiqueta}
            valor={metrica.valor}
            sufijo={metrica.sufijo}
            etiqueta={metrica.etiqueta}
            delay={i * 100}
          />
        ))}
      </div>
    </section>
  )
}
