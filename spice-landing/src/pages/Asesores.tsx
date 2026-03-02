import PageLayout from '../components/layout/PageLayout'
import { BarChart3, PieChart, CreditCard, FileCheck, TrendingUp, Database, ArrowRight, Cpu, Star } from 'lucide-react'

const features = [
  { icono: BarChart3,  titulo: 'PyG automático',          desc: 'Cuenta de pérdidas y ganancias generada por período sin intervención manual.' },
  { icono: CreditCard, titulo: 'Conciliación bancaria',   desc: 'Importa extractos Norma 43 y CaixaBank XLS. Match automático con asientos.' },
  { icono: PieChart,   titulo: 'Ratios y análisis',       desc: 'Liquidez, solvencia, rentabilidad. Calculados automáticamente sobre datos reales.' },
  { icono: FileCheck,  titulo: 'Módulo fiscal completo',  desc: '303, 111, 130, 347, 390 y más. Datos pre-calculados, solo revisar y presentar.' },
  { icono: TrendingUp, titulo: 'Dashboard 16 módulos',    desc: 'Una pantalla con todo: económico, fiscal, bancario, documentos, RRHH.' },
  { icono: Database,   titulo: 'Historial completo',      desc: 'Acceso a todos los ejercicios. Comparativas interanuales en un clic.' },
]

const advisorItems = [
  'Benchmarking sectorial automático (P25 / P50 / P75) por código CNAE',
  'Briefings semanales generados por IA: alertas, tendencias y recomendaciones',
  'Dashboards de PyG, Tesorería, Ventas, Compras, RRHH y Ratios',
  'Star schema OLAP-lite + SectorEngine CNAE + BenchmarkEngine con percentiles',
  'CommandCenter — visión global de toda la cartera de clientes',
]

export default function Asesores() {
  return (
    <PageLayout>
      <section className="pt-12 pb-20 px-4">
        <div className="max-w-5xl mx-auto text-center">
          <span className="inline-block text-xs font-bold bg-prometh-amber/15 text-prometh-amber px-3 py-1 rounded-full mb-6 uppercase tracking-widest">
            Para asesores fiscales
          </span>
          <h1 className="text-4xl md:text-6xl font-heading font-bold text-prometh-text mb-6 leading-tight">
            Análisis económico-financiero<br />
            <span className="gradient-text">en tiempo real.</span><br />
            Sin exportar a Excel.
          </h1>
          <p className="text-lg text-prometh-muted max-w-2xl mx-auto mb-8">
            Toda la información contable, fiscal y financiera de tus clientes centralizada.
            PROMETH-AI la procesa; tú la interpretas y asesoras.
          </p>
          <a href="mailto:hola@prometh-ai.es?subject=Demo asesor fiscal"
            className="btn-primary inline-flex items-center gap-2">
            Ver demo de análisis financiero <ArrowRight size={16} />
          </a>
        </div>
      </section>

      <section className="py-20 px-4 bg-prometh-surface/30">
        <div className="max-w-6xl mx-auto">
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

      {/* Advisor Intelligence Platform */}
      <section className="py-20 px-4">
        <div className="max-w-4xl mx-auto">
          <div className="glass-card p-8 border-prometh-amber/40">
            <div className="flex items-start gap-4 mb-6">
              <div className="p-3 rounded-xl bg-prometh-amber/10 shrink-0">
                <Cpu className="text-prometh-amber" size={32} strokeWidth={1.5} />
              </div>
              <div>
                <div className="flex items-center gap-3 mb-2">
                  <h2 className="text-2xl font-heading font-bold text-prometh-text">
                    Advisor Intelligence Platform
                  </h2>
                  <span className="inline-flex items-center gap-1 text-xs font-bold bg-prometh-amber/20 text-prometh-amber px-2 py-1 rounded-full">
                    <Star size={10} />
                    Solo plan Premium
                  </span>
                </div>
                <p className="text-prometh-muted leading-relaxed">
                  Benchmarking sectorial automático. Compara cada empresa contra su sector (P25/P50/P75).
                  Briefings semanales generados por IA. Dashboards: PyG, Tesorería, Venta, Compras, RRHH, Ratios.
                </p>
              </div>
            </div>
            <ul className="space-y-3">
              {advisorItems.map(item => (
                <li key={item} className="flex items-start gap-3 text-sm text-prometh-muted">
                  <div className="w-1.5 h-1.5 rounded-full bg-prometh-amber mt-1.5 shrink-0" />
                  {item}
                </li>
              ))}
            </ul>
            <div className="mt-6">
              <a href="mailto:hola@prometh-ai.es?subject=Demo Advisor Intelligence Platform"
                className="btn-primary inline-flex items-center gap-2 text-sm">
                Ver demo Advisor <ArrowRight size={14} />
              </a>
            </div>
          </div>
        </div>
      </section>
    </PageLayout>
  )
}
