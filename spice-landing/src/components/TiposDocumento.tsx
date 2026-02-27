import { useState } from 'react'
import { ChevronDown } from 'lucide-react'
import { useInView } from '../hooks/useInView'
import { tiposDocumento, type TipoDocumento } from '../data/tiposDocumento'

/** Formatea un numero como importe contable (2 decimales, punto de miles) */
function formatoImporte(valor?: number): string {
  if (valor === undefined) return ''
  return valor.toLocaleString('es-ES', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

/** Tarjeta individual de tipo de documento */
function TarjetaTipo({
  tipo,
  expandido,
  onClick,
  delay,
}: {
  tipo: TipoDocumento
  expandido: boolean
  onClick: () => void
  delay: number
}) {
  const esFactura = tipo.grupo === 'factura'

  const badgeClase = esFactura
    ? 'bg-spice-emerald/20 text-spice-emerald'
    : 'bg-spice-gold/20 text-spice-gold'

  return (
    <div
      className="glass-card p-4 cursor-pointer hover:bg-white/[0.08] transition-all duration-300 animate-fade-in-up"
      style={{ animationDelay: `${delay}ms` }}
      onClick={onClick}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-3 min-w-0">
          <span
            className={`shrink-0 text-xs font-bold px-2 py-1 rounded-md ${badgeClase}`}
          >
            {tipo.codigo}
          </span>
          <div className="min-w-0">
            <h3 className="text-spice-text font-semibold text-sm md:text-base truncate">
              {tipo.nombre}
            </h3>
            <p className="text-spice-text-muted text-xs mt-0.5">
              {tipo.asiento}
            </p>
          </div>
        </div>
        <ChevronDown
          size={18}
          className={`text-spice-text-muted shrink-0 transition-transform duration-300 ${
            expandido ? 'rotate-180' : ''
          }`}
        />
      </div>

      {/* Descripcion */}
      <p className="text-spice-text-muted text-sm mt-2">{tipo.descripcion}</p>

      {/* Panel expandible con ejemplo */}
      <div
        className={`overflow-hidden transition-all duration-300 ease-in-out ${
          expandido ? 'max-h-96 opacity-100 mt-4' : 'max-h-0 opacity-0 mt-0'
        }`}
      >
        <div className="border-t border-spice-border pt-4">
          {/* Concepto del ejemplo */}
          <p className="text-spice-text text-sm font-medium mb-3">
            {tipo.ejemplo.concepto}
          </p>

          {/* Tabla de partidas */}
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-spice-border">
                  <th className="text-left text-spice-text-muted font-normal py-1.5 pr-2">
                    Subcuenta
                  </th>
                  <th className="text-left text-spice-text-muted font-normal py-1.5 pr-2">
                    Concepto
                  </th>
                  <th className="text-right text-spice-text-muted font-normal py-1.5 pl-2 w-20">
                    Debe
                  </th>
                  <th className="text-right text-spice-text-muted font-normal py-1.5 pl-2 w-20">
                    Haber
                  </th>
                </tr>
              </thead>
              <tbody>
                {tipo.ejemplo.partidas.map((partida, idx) => (
                  <tr
                    key={idx}
                    className="border-b border-spice-border/50 last:border-b-0"
                  >
                    <td className="py-1.5 pr-2 text-spice-emerald font-mono text-xs">
                      {partida.subcuenta}
                    </td>
                    <td className="py-1.5 pr-2 text-spice-text">
                      {partida.nombre}
                    </td>
                    <td className="py-1.5 pl-2 text-right text-spice-text font-mono text-xs">
                      {partida.debe !== undefined
                        ? formatoImporte(partida.debe)
                        : ''}
                    </td>
                    <td className="py-1.5 pl-2 text-right text-spice-text font-mono text-xs">
                      {partida.haber !== undefined
                        ? formatoImporte(partida.haber)
                        : ''}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function TiposDocumento() {
  const { ref, visible } = useInView()
  const [expandido, setExpandido] = useState<string | null>(null)

  const facturas = tiposDocumento.filter((t) => t.grupo === 'factura')
  const otros = tiposDocumento.filter((t) => t.grupo === 'otro')

  function toggleExpand(codigo: string) {
    setExpandido((prev) => (prev === codigo ? null : codigo))
  }

  return (
    <section id="documentos" className="py-20 px-4" ref={ref}>
      <div className="max-w-5xl mx-auto">
        {/* Encabezado */}
        <div className="text-center mb-14">
          <h2
            className={`text-3xl md:text-4xl font-heading font-bold text-spice-text mb-4 transition-all duration-700 ${
              visible
                ? 'opacity-100 translate-y-0'
                : 'opacity-0 translate-y-6'
            }`}
          >
            10 tipos de documento que SPICE contabiliza
          </h2>
        </div>

        {visible && (
          <div className="space-y-12">
            {/* Grupo: Facturas */}
            <div>
              <div className="flex items-center gap-3 mb-6">
                <div className="h-px flex-1 bg-spice-emerald/30" />
                <span className="text-spice-emerald font-heading font-semibold text-sm uppercase tracking-wider">
                  Facturas
                </span>
                <div className="h-px flex-1 bg-spice-emerald/30" />
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {facturas.map((tipo, idx) => (
                  <TarjetaTipo
                    key={tipo.codigo}
                    tipo={tipo}
                    expandido={expandido === tipo.codigo}
                    onClick={() => toggleExpand(tipo.codigo)}
                    delay={idx * 80}
                  />
                ))}
              </div>
            </div>

            {/* Grupo: Otros documentos */}
            <div>
              <div className="flex items-center gap-3 mb-6">
                <div className="h-px flex-1 bg-spice-gold/30" />
                <span className="text-spice-gold font-heading font-semibold text-sm uppercase tracking-wider">
                  Otros documentos
                </span>
                <div className="h-px flex-1 bg-spice-gold/30" />
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {otros.map((tipo, idx) => (
                  <TarjetaTipo
                    key={tipo.codigo}
                    tipo={tipo}
                    expandido={expandido === tipo.codigo}
                    onClick={() => toggleExpand(tipo.codigo)}
                    delay={idx * 80}
                  />
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </section>
  )
}
