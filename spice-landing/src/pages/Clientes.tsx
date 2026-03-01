import PageLayout from '../components/layout/PageLayout'
import { Eye, Bell, FileText, MessageCircle, ArrowRight, Check } from 'lucide-react'

const features = [
  { icono: Eye,           titulo: 'Visibilidad de tu negocio',   desc: 'Ve cómo va tu empresa: ingresos, gastos, impuestos. Sin necesitar saber contabilidad.' },
  { icono: Bell,          titulo: 'Alertas de vencimientos',     desc: 'Recibe notificaciones antes de cada plazo fiscal. Nunca más una sanción por olvido.' },
  { icono: FileText,      titulo: 'Tus documentos centralizados',desc: 'Facturas, nóminas, modelos presentados. Todo organizado y accesible desde tu portal.' },
  { icono: MessageCircle, titulo: 'Habla con tu asesor',         desc: 'Canal directo con tu gestoría desde la misma plataforma. Sin emails perdidos.' },
]

const propuestas = [
  { nombre: 'Básico',    desc: 'Visibilidad y alertas fiscales',  items: ['Portal cliente', 'Alertas vencimientos', 'Documentos básicos'],                                    destacado: false },
  { nombre: 'Completo',  desc: 'Análisis + asesoría integrada',   items: ['Todo lo básico', 'Dashboard financiero', 'Chat con asesor', 'Informes mensuales'],                  destacado: true  },
  { nombre: 'Premium',   desc: 'Solución total a medida',         items: ['Todo lo completo', 'Asesor dedicado', 'Informes a medida', 'Integración ERP'],                      destacado: false },
]

export default function Clientes() {
  return (
    <PageLayout>
      <section className="pt-12 pb-20 px-4">
        <div className="max-w-5xl mx-auto text-center">
          <span className="inline-block text-xs font-bold bg-prometh-amber/15 text-prometh-amber px-3 py-1 rounded-full mb-6 uppercase tracking-widest">
            Para empresas y autónomos
          </span>
          <h1 className="text-4xl md:text-6xl font-heading font-bold text-prometh-text mb-6 leading-tight">
            Sabe exactamente<br />
            <span className="gradient-text">cómo va tu negocio.</span><br />
            Sin ser contable.
          </h1>
          <p className="text-lg text-prometh-muted max-w-2xl mx-auto mb-8">
            Tu gestoría usa PROMETH-AI para llevar tus cuentas. Tú tienes acceso en tiempo real
            a todo lo que importa de tu empresa.
          </p>
          <a href="mailto:hola@prometh-ai.es?subject=Informacion cliente"
            className="btn-primary inline-flex items-center gap-2">
            Hablar con un asesor <ArrowRight size={16} />
          </a>
        </div>
      </section>

      <section className="py-16 px-4 bg-prometh-surface/30">
        <div className="max-w-6xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-20">
            {features.map(f => {
              const Icono = f.icono
              return (
                <div key={f.titulo} className="glass-card p-6">
                  <Icono className="text-prometh-amber mb-3" size={24} strokeWidth={1.5} />
                  <h3 className="font-heading font-bold text-prometh-text mb-2 text-sm">{f.titulo}</h3>
                  <p className="text-prometh-muted text-xs leading-relaxed">{f.desc}</p>
                </div>
              )
            })}
          </div>

          <h2 className="text-2xl font-heading font-bold text-prometh-text text-center mb-8">
            Propuestas según tu necesidad
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {propuestas.map(p => (
              <div key={p.nombre}
                className={`glass-card p-6 ${p.destacado ? 'border-prometh-amber/50' : ''}`}>
                {p.destacado && (
                  <span className="text-xs font-bold bg-prometh-amber/20 text-prometh-amber px-2 py-1 rounded-full mb-3 inline-block">
                    Más elegido
                  </span>
                )}
                <h3 className="font-heading font-bold text-prometh-text text-xl mb-1">{p.nombre}</h3>
                <p className="text-prometh-muted text-sm mb-4">{p.desc}</p>
                <ul className="space-y-2 mb-6">
                  {p.items.map(item => (
                    <li key={item} className="flex items-center gap-2 text-sm text-prometh-muted">
                      <Check size={14} className="text-prometh-amber shrink-0" />
                      {item}
                    </li>
                  ))}
                </ul>
                <a href="mailto:hola@prometh-ai.es"
                  className={`block text-center py-2 rounded-lg text-sm font-semibold transition-colors ${
                    p.destacado
                      ? 'btn-primary'
                      : 'border border-prometh-border text-prometh-text hover:border-prometh-amber/50'
                  }`}>
                  Consultar
                </a>
              </div>
            ))}
          </div>
        </div>
      </section>
    </PageLayout>
  )
}
