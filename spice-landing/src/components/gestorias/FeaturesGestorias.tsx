import { Brain, FileText, Building2, Shield, RefreshCw, Zap } from 'lucide-react'

const features = [
  {
    icono: Brain,
    titulo: 'Triple motor OCR',
    desc: 'Mistral OCR (primario) → GPT-4o (fallback) → Gemini Flash (validación). 98% de precisión con cualquier formato de factura.',
  },
  {
    icono: Building2,
    titulo: 'Multi-empresa',
    desc: 'Gestiona todos tus clientes desde un único dashboard. Datos completamente aislados entre empresas.',
  },
  {
    icono: FileText,
    titulo: '28 modelos fiscales',
    desc: 'Modelo 303, 111, 130, 347, 390... generados automáticamente desde los datos contabilizados. Formato AEAT listo para presentar.',
  },
  {
    icono: RefreshCw,
    titulo: 'Motor de aprendizaje',
    desc: 'El sistema aprende de cada documento. Con el tiempo, reconoce los proveedores habituales de tu cliente sin necesidad de configuración.',
  },
  {
    icono: Zap,
    titulo: 'Integración FacturaScripts',
    desc: 'Asientos creados directamente vía API. Sin exportar, sin importar, sin re-introducir datos.',
  },
  {
    icono: Shield,
    titulo: 'Aislamiento multi-tenant',
    desc: 'Cada gestoría tiene su espacio completamente aislado. Los datos de un cliente nunca son visibles para otro.',
  },
]

export default function FeaturesGestorias() {
  return (
    <section className="py-20 px-4 bg-prometh-surface/30">
      <div className="max-w-6xl mx-auto">
        <h2 className="text-3xl font-heading font-bold text-prometh-text text-center mb-12">
          Todo lo que necesita tu despacho
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map(f => {
            const Icono = f.icono
            return (
              <div key={f.titulo} className="glass-card p-6">
                <Icono className="text-prometh-amber mb-4" size={28} strokeWidth={1.5} />
                <h3 className="font-heading font-bold text-prometh-text mb-2">{f.titulo}</h3>
                <p className="text-prometh-muted text-sm leading-relaxed">{f.desc}</p>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
