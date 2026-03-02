import { useInView } from '../../hooks/useInView'

const metricas = [
  { valor: '99%',   label: 'Precisión OCR',               color: 'text-prometh-amber' },
  { valor: '15 min', label: 'de supervisión al mes',      color: 'text-prometh-amber' },
  { valor: '28',    label: 'Modelos fiscales',             color: 'text-prometh-amber' },
  { valor: '2.413', label: 'Tests pasando',                color: 'text-prometh-green' },
  { valor: '3',     label: 'Motores IA en cascada',        color: 'text-prometh-amber' },
  { valor: '100%',  label: 'Balance cuadrado al céntimo',  color: 'text-prometh-green' },
]

export default function Metricas() {
  const { ref, visible } = useInView()
  return (
    <section className="py-16 px-4 border-y border-prometh-border bg-prometh-surface/50">
      <div className="max-w-6xl mx-auto">
        <p className="text-center text-prometh-muted text-sm mb-8 uppercase tracking-widest">
          Resultados reales con datos de producción
        </p>
        <div ref={ref}
          className={`grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-6 transition-all duration-700 ${
            visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-6'}`}>
          {metricas.map((m, i) => (
            <div key={i} className="text-center" style={{ transitionDelay: `${i * 80}ms` }}>
              <div className={`text-2xl md:text-3xl font-heading font-bold ${m.color}`}>{m.valor}</div>
              <div className="text-prometh-muted text-xs mt-1 leading-tight">{m.label}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
