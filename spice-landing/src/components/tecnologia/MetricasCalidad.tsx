import { useInView } from '../../hooks/useInView'

interface Metrica {
  valor: string
  sufijo?: string
  etiqueta: string
  descripcion: string
}

const metricas: Metrica[] = [
  {
    valor: '2.413',
    etiqueta: 'Tests automatizados PASS',
    descripcion: 'pytest — 0 fallos, 0 errores',
  },
  {
    valor: '75',
    sufijo: '+',
    etiqueta: 'Endpoints API REST',
    descripcion: 'Documentados y probados',
  },
  {
    valor: '39',
    etiqueta: 'Tablas en base de datos',
    descripcion: 'Esquema normalizado PostgreSQL',
  },
  {
    valor: '7',
    etiqueta: 'Fases del pipeline',
    descripcion: 'Gate 0 → Intake → OCR → Validacion → Registro → Correccion → Informe',
  },
  {
    valor: '3',
    etiqueta: 'Motores OCR en cascada',
    descripcion: 'Mistral T0 → GPT-4o T1 → Gemini T2',
  },
  {
    valor: '6',
    etiqueta: 'Niveles motor de reglas',
    descripcion: 'Normativa > PGC > Fiscal > Negocio > Cliente > Aprendizaje',
  },
  {
    valor: '50',
    etiqueta: 'Categorias fiscales MCF',
    descripcion: 'LIVA + LIRPF 2025 — cobertura multisectorial',
  },
  {
    valor: '28',
    etiqueta: 'Modelos fiscales BOE',
    descripcion: 'Generados y validados automaticamente',
  },
]

function TarjetaMetrica({ metrica, indice }: { metrica: Metrica; indice: number }) {
  const { ref, visible } = useInView()

  return (
    <div
      ref={ref}
      className="glass-card p-6 text-center transition-all duration-600 group hover:border-prometh-amber/30"
      style={{
        opacity: visible ? 1 : 0,
        transform: visible ? 'translateY(0)' : 'translateY(28px)',
        transitionDelay: `${indice * 80}ms`,
      }}
    >
      {/* Numero grande */}
      <div className="mb-2">
        <span className="text-4xl md:text-5xl font-heading font-bold gradient-text leading-none">
          {metrica.valor}
        </span>
        {metrica.sufijo && (
          <span className="text-3xl md:text-4xl font-heading font-bold text-prometh-amber leading-none">
            {metrica.sufijo}
          </span>
        )}
      </div>

      {/* Etiqueta */}
      <p className="text-prometh-text font-semibold text-sm md:text-base mb-1">
        {metrica.etiqueta}
      </p>

      {/* Descripcion */}
      <p className="text-prometh-muted text-xs leading-relaxed">
        {metrica.descripcion}
      </p>
    </div>
  )
}

export default function MetricasCalidad() {
  const { ref, visible } = useInView()

  return (
    <section className="py-20 px-4" style={{ background: 'rgba(245,158,11,0.02)' }}>
      <div className="max-w-6xl mx-auto">
        {/* Titulo */}
        <div
          ref={ref}
          className="text-center mb-12 transition-all duration-600"
          style={{
            opacity: visible ? 1 : 0,
            transform: visible ? 'translateY(0)' : 'translateY(24px)',
          }}
        >
          <span className="inline-block text-xs font-bold bg-prometh-amber/15 text-prometh-amber px-3 py-1 rounded-full mb-4 uppercase tracking-widest">
            Metricas tecnicas
          </span>
          <h2 className="text-3xl md:text-4xl font-heading font-bold text-prometh-text mb-3">
            Numeros que hablan por si solos
          </h2>
          <p className="text-prometh-muted text-base md:text-lg max-w-2xl mx-auto">
            Cada cifra es verificable en el repositorio. Sin estimaciones, sin marketing.
          </p>
        </div>

        {/* Grid de metricas */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 md:gap-6">
          {metricas.map((m, i) => (
            <TarjetaMetrica key={m.etiqueta} metrica={m} indice={i} />
          ))}
        </div>
      </div>
    </section>
  )
}
