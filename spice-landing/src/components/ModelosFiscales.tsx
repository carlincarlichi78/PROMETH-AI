import { useState } from 'react'
import { useInView } from '../hooks/useInView'
import { modelosFiscales } from '../data/modelosFiscales'
import type { ModeloFiscal } from '../data/modelosFiscales'

type Tab = 'automatico' | 'semi' | 'asistido'

const TABS: { id: Tab; label: string; count: number }[] = [
  { id: 'automatico', label: 'Automaticos', count: modelosFiscales.filter((m) => m.categoria === 'automatico').length },
  { id: 'semi', label: 'Semi-automaticos', count: modelosFiscales.filter((m) => m.categoria === 'semi').length },
  { id: 'asistido', label: 'Asistidos', count: modelosFiscales.filter((m) => m.categoria === 'asistido').length },
]

/** Badge con el numero de modelo */
function BadgeModelo({ modelo }: { modelo: string }) {
  return (
    <span className="inline-flex items-center px-2.5 py-0.5 rounded-md bg-spice-emerald/20 text-spice-emerald font-heading font-bold text-sm border border-spice-emerald/30">
      {modelo}
    </span>
  )
}

/** Tabla responsive para modelos automaticos: tabla en desktop, cards en mobile */
function TablaAutomaticos({ modelos }: { modelos: ModeloFiscal[] }) {
  return (
    <>
      {/* Desktop: tabla */}
      <div className="hidden md:block overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-spice-border text-spice-text-muted text-left">
              <th className="py-3 px-4 font-heading font-semibold">Modelo</th>
              <th className="py-3 px-4 font-heading font-semibold">Nombre</th>
              <th className="py-3 px-4 font-heading font-semibold">Periodicidad</th>
              <th className="py-3 px-4 font-heading font-semibold">Quien</th>
              <th className="py-3 px-4 font-heading font-semibold">Descripcion</th>
            </tr>
          </thead>
          <tbody>
            {modelos.map((m) => (
              <tr
                key={m.modelo}
                className="border-b border-white/[0.05] hover:bg-white/[0.03] transition-colors"
              >
                <td className="py-3 px-4">
                  <BadgeModelo modelo={m.modelo} />
                </td>
                <td className="py-3 px-4 text-spice-text font-body">{m.nombre}</td>
                <td className="py-3 px-4 text-spice-text-muted font-body">{m.periodicidad}</td>
                <td className="py-3 px-4 text-spice-text-muted font-body">{m.quien}</td>
                <td className="py-3 px-4 text-spice-text/80 font-body">{m.descripcionCorta}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile: cards */}
      <div className="md:hidden space-y-3">
        {modelos.map((m) => (
          <div key={m.modelo} className="glass-card p-4">
            <div className="flex items-center gap-3 mb-2">
              <BadgeModelo modelo={m.modelo} />
              <span className="font-heading font-semibold text-spice-text">{m.nombre}</span>
            </div>
            <div className="text-xs text-spice-text-muted font-body mb-1">
              {m.periodicidad} · {m.quien}
            </div>
            <p className="text-sm text-spice-text/80 font-body">{m.descripcionCorta}</p>
          </div>
        ))}
      </div>
    </>
  )
}

/** Cards grandes para modelos semi-automaticos: que hace SPICE vs que completa el gestor */
function CardsSemi({ modelos }: { modelos: ModeloFiscal[] }) {
  return (
    <div className="space-y-4">
      {modelos.map((m) => {
        // Separar la descripcion en dos partes por el punto
        const partes = m.descripcionCorta.split('. ')
        const spiceHace = partes[0] || m.descripcionCorta
        const gestorCompleta = partes[1] || ''

        return (
          <div key={m.modelo} className="glass-card p-6">
            <div className="flex items-center gap-3 mb-4">
              <BadgeModelo modelo={m.modelo} />
              <div>
                <span className="font-heading font-semibold text-spice-text">{m.nombre}</span>
                <span className="text-spice-text-muted text-sm ml-2">· {m.periodicidad} · {m.quien}</span>
              </div>
            </div>
            <div className="grid md:grid-cols-2 gap-4">
              <div className="p-4 rounded-lg bg-spice-emerald/10 border border-spice-emerald/20">
                <div className="text-xs text-spice-emerald font-heading font-semibold uppercase tracking-wider mb-2">
                  SPICE automatiza
                </div>
                <p className="text-sm text-spice-text/90 font-body">{spiceHace}</p>
              </div>
              <div className="p-4 rounded-lg bg-spice-gold/10 border border-spice-gold/20">
                <div className="text-xs text-spice-gold font-heading font-semibold uppercase tracking-wider mb-2">
                  El gestor completa
                </div>
                <p className="text-sm text-spice-text/90 font-body">
                  {gestorCompleta || 'Revision y validacion final'}
                </p>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}

/** Card especial para el modelo 100 (asistido) */
function CardAsistido({ modelo }: { modelo: ModeloFiscal }) {
  return (
    <div className="glass-card p-8 border-spice-gold/30 border-2 max-w-2xl mx-auto">
      <div className="flex items-center gap-4 mb-6">
        <span className="inline-flex items-center px-4 py-1.5 rounded-lg bg-spice-gold/20 text-spice-gold font-heading font-bold text-lg border border-spice-gold/40">
          {modelo.modelo}
        </span>
        <div>
          <h4 className="font-heading font-bold text-spice-text text-lg">{modelo.nombre}</h4>
          <p className="text-sm text-spice-text-muted">{modelo.periodicidad} · {modelo.quien}</p>
        </div>
      </div>

      <div className="space-y-4">
        <div className="p-4 rounded-lg bg-spice-emerald/10 border border-spice-emerald/20">
          <div className="text-xs text-spice-emerald font-heading font-semibold uppercase tracking-wider mb-2">
            Lo que SPICE aporta
          </div>
          <p className="text-sm text-spice-text/90 font-body">
            Rendimientos de la actividad economica calculados automaticamente desde la contabilidad:
            ingresos, gastos deducibles, amortizaciones y resultado neto. Datos exportables para
            importar en Renta Web.
          </p>
        </div>

        <div className="p-4 rounded-lg bg-spice-gold/10 border border-spice-gold/20">
          <div className="text-xs text-spice-gold font-heading font-semibold uppercase tracking-wider mb-2">
            Lo que completa el gestor en Renta Web
          </div>
          <p className="text-sm text-spice-text/90 font-body">
            Rendimientos del trabajo, capital mobiliario e inmobiliario, ganancias patrimoniales,
            deducciones personales y familiares, situacion personal del contribuyente.
          </p>
        </div>
      </div>
    </div>
  )
}

export default function ModelosFiscales() {
  const { ref, visible } = useInView()
  const [tabActivo, setTabActivo] = useState<Tab>('automatico')

  const modelosFiltrados = modelosFiscales.filter((m) => m.categoria === tabActivo)
  const modeloAsistido = modelosFiscales.find((m) => m.categoria === 'asistido')

  return (
    <section ref={ref} id="modelos" className="py-20 px-4">
      <div
        className={`max-w-6xl mx-auto transition-all duration-700 ${
          visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-6'
        }`}
      >
        {/* Titulo */}
        <h2 className="text-3xl md:text-4xl font-heading font-bold text-center text-spice-text mb-3">
          Modelos fiscales: 3 niveles de automatizacion
        </h2>
        <p className="text-center text-spice-text-muted mb-10 max-w-2xl mx-auto">
          Desde la generacion completa hasta la asistencia al gestor
        </p>

        {/* Tabs */}
        <div className="flex flex-wrap justify-center gap-2 mb-10">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setTabActivo(tab.id)}
              className={`glass-card px-5 py-2.5 font-heading font-semibold text-sm cursor-pointer transition-all ${
                tabActivo === tab.id
                  ? 'bg-spice-emerald/20 border-spice-emerald text-spice-emerald'
                  : 'text-spice-text-muted hover:text-spice-text hover:bg-white/[0.08]'
              }`}
            >
              {tab.label} ({tab.count})
            </button>
          ))}
        </div>

        {/* Contenido segun tab */}
        <div
          key={tabActivo}
          className="animate-fade-in-up"
          style={{ animationDuration: '0.3s' }}
        >
          {tabActivo === 'automatico' && <TablaAutomaticos modelos={modelosFiltrados} />}
          {tabActivo === 'semi' && <CardsSemi modelos={modelosFiltrados} />}
          {tabActivo === 'asistido' && modeloAsistido && <CardAsistido modelo={modeloAsistido} />}
        </div>
      </div>
    </section>
  )
}
