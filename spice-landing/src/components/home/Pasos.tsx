import { Link } from 'react-router-dom'
import { Upload, Cpu, CheckCircle, ArrowRight } from 'lucide-react'
import { useInView } from '../../hooks/useInView'

const pasos = [
  {
    num: '01',
    icono: Upload,
    titulo: 'Recibes el documento',
    descripcion: 'Por email, drag & drop, escáner o carpeta vigilada. PROMETH-AI acepta facturas, nóminas, extractos bancarios y más.',
  },
  {
    num: '02',
    icono: Cpu,
    titulo: 'La IA lo procesa',
    descripcion: 'Triple motor OCR (Mistral + GPT-4o + Gemini) lee, clasifica, extrae datos y valida con 6 capas de confianza.',
  },
  {
    num: '03',
    icono: CheckCircle,
    titulo: 'Aparece en FacturaScripts',
    descripcion: 'Asiento contable creado, IVA aplicado, modelo fiscal actualizado. Todo en menos de 30 segundos por documento.',
  },
]

export default function Pasos() {
  const { ref, visible } = useInView()
  return (
    <section className="py-20 px-4">
      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-12">
          <h2 className="text-3xl md:text-4xl font-heading font-bold text-prometh-text mb-3">
            Así de simple
          </h2>
          <p className="text-prometh-muted text-lg">De documento a asiento contable en 3 pasos</p>
        </div>

        <div ref={ref} className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {pasos.map((paso, i) => {
            const Icono = paso.icono
            return (
              <div key={i}
                className={`relative transition-all duration-700 ${visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}
                style={{ transitionDelay: `${i * 150}ms` }}>
                {i < pasos.length - 1 && (
                  <ArrowRight className="hidden md:block absolute -right-4 top-8 text-prometh-border" size={24} />
                )}
                <div className="glass-card p-6 h-full">
                  <div className="flex items-center gap-3 mb-4">
                    <span className="text-3xl font-heading font-bold text-prometh-amber/30">{paso.num}</span>
                    <div className="w-10 h-10 rounded-lg bg-prometh-amber/10 flex items-center justify-center">
                      <Icono className="text-prometh-amber" size={20} />
                    </div>
                  </div>
                  <h3 className="font-heading font-bold text-prometh-text mb-2">{paso.titulo}</h3>
                  <p className="text-prometh-muted text-sm leading-relaxed">{paso.descripcion}</p>
                </div>
              </div>
            )
          })}
        </div>

        <div className="text-center mt-10">
          <Link to="/como-funciona"
            className="inline-flex items-center gap-2 text-prometh-amber hover:text-prometh-amber-light transition-colors font-semibold">
            Ver el proceso completo <ArrowRight size={16} />
          </Link>
        </div>
      </div>
    </section>
  )
}
