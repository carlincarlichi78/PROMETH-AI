import { useState } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'
import { useInView } from '../hooks/useInView'

const MESES = ['ENE', 'FEB', 'MAR', 'ABR', 'MAY', 'JUN', 'JUL', 'AGO', 'SEP', 'OCT', 'NOV', 'DIC']

/** Meses donde hay obligacion fiscal trimestral (1T=ABR, 2T=JUL, 3T=OCT, 4T=ENE siguiente) */
const MESES_FISCAL = new Set([3, 6, 9, 0]) // ABR=3, JUL=6, OCT=9, ENE=0

const PASOS_CIERRE = [
  'Contabilizar amortizaciones pendientes del ultimo mes',
  'Regularizacion de existencias (variacion de stock)',
  'Dotacion provision clientes de dudoso cobro',
  'Regularizacion de prorrata definitiva (si aplica)',
  'Regularizacion IVA de bienes de inversion',
  'Periodificaciones (gastos anticipados, ingresos anticipados)',
  'Contabilizacion del Impuesto de Sociedades (solo personas juridicas)',
  'Asiento de regularizacion: cierra cuentas 6xx y 7xx contra cuenta 129',
  'Asiento de cierre: todas las cuentas patrimoniales a saldo cero',
  'Asiento de apertura del nuevo ejercicio (1 de enero)',
]

export default function DiagramaCiclo() {
  const { ref, visible } = useInView()
  const [expandido, setExpandido] = useState(false)

  return (
    <section ref={ref} className="py-20 px-4">
      <div
        className={`max-w-6xl mx-auto transition-all duration-700 ${
          visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-6'
        }`}
      >
        {/* Titulo */}
        <h2 className="text-3xl md:text-4xl font-heading font-bold text-center text-spice-text mb-3">
          El ejercicio contable completo, mes a mes
        </h2>
        <p className="text-center text-spice-text-muted mb-12 max-w-2xl mx-auto">
          Todo lo que SPICE automatiza a lo largo del ano
        </p>

        {/* Timeline horizontal scrollable */}
        <div className="overflow-x-auto pb-4 -mx-4 px-4 snap-x snap-mandatory">
          <div className="min-w-[960px]">
            {/* Cabecera meses */}
            <div className="grid grid-cols-12 gap-1 mb-3">
              {MESES.map((mes, i) => (
                <div
                  key={mes}
                  className={`snap-start min-w-[120px] text-center text-sm font-heading font-semibold py-2 rounded-t-lg ${
                    i === 11
                      ? 'bg-spice-gold/20 text-spice-gold border border-spice-gold/40'
                      : 'text-spice-text-muted'
                  }`}
                >
                  {mes}
                </div>
              ))}
            </div>

            {/* Fila 1: Registro (continua) */}
            <div className="mb-2">
              <div className="text-xs text-spice-text-muted mb-1 font-heading uppercase tracking-wider pl-1">
                Registro
              </div>
              <div className="grid grid-cols-12 gap-1">
                {MESES.map((mes) => (
                  <div
                    key={`reg-${mes}`}
                    className="min-w-[120px] h-10 rounded-md bg-spice-emerald/20 border border-spice-emerald/30 flex items-center justify-center"
                  >
                    <span className="text-[10px] text-spice-emerald font-body leading-tight text-center px-1">
                      Facturas, nominas, suministros
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Fila 2: Operaciones recurrentes (continua) */}
            <div className="mb-2">
              <div className="text-xs text-spice-text-muted mb-1 font-heading uppercase tracking-wider pl-1">
                Operaciones recurrentes
              </div>
              <div className="grid grid-cols-12 gap-1">
                {MESES.map((mes) => (
                  <div
                    key={`ops-${mes}`}
                    className="min-w-[120px] h-10 rounded-md bg-spice-gold/15 border border-spice-gold/25 flex items-center justify-center"
                  >
                    <span className="text-[10px] text-spice-gold font-body leading-tight text-center px-1">
                      Amortizaciones, provisiones
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Fila 3: Obligaciones fiscales (solo trimestres) */}
            <div className="mb-2">
              <div className="text-xs text-spice-text-muted mb-1 font-heading uppercase tracking-wider pl-1">
                Obligaciones fiscales
              </div>
              <div className="grid grid-cols-12 gap-1">
                {MESES.map((mes, i) => {
                  const esFiscal = MESES_FISCAL.has(i)
                  return (
                    <div
                      key={`fis-${mes}`}
                      className={`min-w-[120px] h-10 rounded-md flex items-center justify-center ${
                        esFiscal
                          ? 'bg-spice-emerald/30 border border-spice-emerald/50'
                          : 'bg-white/[0.02] border border-white/[0.05]'
                      }`}
                    >
                      {esFiscal && (
                        <span className="text-[10px] text-spice-emerald-light font-body font-semibold text-center px-1">
                          303, 111, 130...
                        </span>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Bloque especial DIC */}
            <div className="grid grid-cols-12 gap-1 mt-4">
              {MESES.map((mes, i) => (
                <div key={`cierre-${mes}`} className="min-w-[120px]">
                  {i === 11 && (
                    <div className="glass-card border-spice-gold/50 border-2 p-3 text-center">
                      <div className="text-spice-gold font-heading font-bold text-sm mb-1">
                        CIERRE
                      </div>
                      <div className="text-[10px] text-spice-text-muted leading-tight">
                        Del ejercicio
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Seccion expandible: 10 pasos del cierre */}
        <div className="mt-12 max-w-3xl mx-auto">
          <button
            onClick={() => setExpandido(!expandido)}
            className="w-full glass-card px-6 py-4 flex items-center justify-between cursor-pointer hover:bg-white/[0.08] transition-colors"
          >
            <span className="font-heading font-semibold text-spice-text">
              Los 10 pasos del cierre de ejercicio
            </span>
            {expandido ? (
              <ChevronUp className="w-5 h-5 text-spice-gold" />
            ) : (
              <ChevronDown className="w-5 h-5 text-spice-gold" />
            )}
          </button>

          {expandido && (
            <div className="mt-4 space-y-3">
              {PASOS_CIERRE.map((paso, i) => (
                <div
                  key={i}
                  className="glass-card px-5 py-3 flex items-start gap-4"
                  style={{
                    animation: `fade-in-up 0.4s ease-out ${i * 0.05}s both`,
                  }}
                >
                  <span className="flex-shrink-0 w-8 h-8 rounded-lg bg-spice-gold/20 text-spice-gold font-heading font-bold text-sm flex items-center justify-center">
                    {i + 1}
                  </span>
                  <span className="text-sm text-spice-text/90 font-body leading-relaxed pt-1">
                    {paso}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
