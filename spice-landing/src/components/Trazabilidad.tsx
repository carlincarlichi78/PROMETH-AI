import { FileText, CheckCircle } from 'lucide-react'
import { useInView } from '../hooks/useInView'

/** Lineas del razonamiento paso a paso */
const pasosRazonamiento = [
  'El CIF B99999999 esta dado de alta como proveedor de servicios',
  'Regimen IVA: general (peninsula)',
  'Tipo de IVA aplicable: 21% segun normativa vigente 2025',
  'Sin retencion IRPF (no es profesional)',
  'IVA 100% deducible (no es vehiculo ni representacion)',
]

/** Filas del asiento generado */
const filasAsiento = [
  { subcuenta: '629', concepto: 'Otros servicios', debe: '1.000,00', haber: '' },
  { subcuenta: '472', concepto: 'H.P. IVA soportado', debe: '210,00', haber: '' },
  { subcuenta: '400', concepto: 'Proveedor ACME', debe: '', haber: '1.210,00' },
]

/** Badges de verificacion */
const verificaciones = [
  'Cuadre aritmetico',
  'Subcuenta valida',
  'No duplicado',
  'Coherencia fiscal',
]

/** Porcentaje de fiabilidad */
const FIABILIDAD = 95

export default function Trazabilidad() {
  const { ref, visible } = useInView()

  return (
    <section id="trazabilidad" className="py-20 px-4">
      <div className="max-w-5xl mx-auto">
        {/* Titulo y subtitulo */}
        <h2 className="text-3xl md:text-4xl font-heading font-bold text-center text-spice-text mb-4">
          Trazabilidad: por que cada asiento esta donde esta
        </h2>
        <p className="text-center text-spice-text-muted mb-12 max-w-2xl mx-auto">
          El gestor puede ver EXACTAMENTE por que SPICE contabilizo asi
        </p>

        {/* Tarjeta principal */}
        <div
          ref={ref}
          className={`max-w-2xl mx-auto glass-card border-spice-gold/50 p-6 md:p-8 transition-all duration-700 ${
            visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'
          }`}
        >
          {/* Header factura */}
          <div className="flex items-center gap-3 mb-4">
            <FileText className="text-spice-gold shrink-0" size={28} strokeWidth={1.5} />
            <div className="flex-1">
              <p className="font-heading font-bold text-spice-text">Factura de ACME S.L.</p>
              <p className="text-sm text-spice-text-muted">15/06/2025</p>
            </div>
            <span className="text-spice-gold font-heading font-bold text-lg">
              1.210,00 EUR
            </span>
          </div>

          <hr className="border-spice-border mb-5" />

          {/* Razonamiento paso a paso */}
          <p className="font-heading font-bold text-spice-text mb-3">
            Razonamiento paso a paso:
          </p>
          <ul className="space-y-2 mb-5">
            {pasosRazonamiento.map((paso, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-spice-text/90">
                <CheckCircle
                  className="text-spice-emerald shrink-0 mt-0.5"
                  size={18}
                  strokeWidth={2}
                />
                <span>{paso}</span>
              </li>
            ))}
          </ul>

          <hr className="border-spice-border mb-5" />

          {/* Asiento generado */}
          <p className="font-heading font-bold text-spice-text mb-3">
            Asiento generado:
          </p>
          <div className="overflow-x-auto mb-5">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs uppercase text-spice-text-muted">
                  <th className="text-left pb-2 font-medium">Subcuenta</th>
                  <th className="text-left pb-2 font-medium">Concepto</th>
                  <th className="text-right pb-2 font-medium">Debe</th>
                  <th className="text-right pb-2 font-medium">Haber</th>
                </tr>
              </thead>
              <tbody>
                {filasAsiento.map((fila) => (
                  <tr key={fila.subcuenta} className="border-t border-spice-border/50">
                    <td className="py-2 font-mono text-spice-emerald">{fila.subcuenta}</td>
                    <td className="py-2 text-spice-text/90">{fila.concepto}</td>
                    <td className="py-2 text-right text-spice-text/90">
                      {fila.debe || '\u2014'}
                    </td>
                    <td className="py-2 text-right text-spice-text/90">
                      {fila.haber || '\u2014'}
                    </td>
                  </tr>
                ))}
                {/* Fila total */}
                <tr className="border-t-2 border-spice-border">
                  <td className="py-2" />
                  <td className="py-2" />
                  <td className="py-2 text-right font-bold text-spice-text">1.210,00</td>
                  <td className="py-2 text-right font-bold text-spice-text">1.210,00</td>
                </tr>
              </tbody>
            </table>
          </div>

          <hr className="border-spice-border mb-5" />

          {/* Verificaciones superadas */}
          <p className="font-heading font-bold text-spice-text mb-3">
            Verificaciones superadas:
          </p>
          <div className="flex flex-wrap gap-2 mb-5">
            {verificaciones.map((v) => (
              <span
                key={v}
                className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium bg-spice-emerald/15 text-spice-emerald border border-spice-emerald/30"
              >
                <CheckCircle size={12} strokeWidth={2.5} />
                {v}
              </span>
            ))}
          </div>

          {/* Barra de fiabilidad */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-heading font-bold text-spice-text">
                Fiabilidad de la decision
              </span>
              <span className="text-sm font-heading font-bold text-spice-emerald">
                {FIABILIDAD}%
              </span>
            </div>
            <div className="w-full h-2.5 rounded-full bg-spice-card overflow-hidden">
              <div
                className="h-full rounded-full bg-spice-emerald transition-all duration-1000 ease-out"
                style={{ width: visible ? `${FIABILIDAD}%` : '0%' }}
              />
            </div>
          </div>
        </div>

        {/* Texto explicativo */}
        <p className="text-center text-spice-text-muted mt-8 max-w-2xl mx-auto text-sm leading-relaxed">
          Cada asiento incluye la justificacion completa de por que se contabilizo asi.
          Si el gestor lo corrige, SPICE aprende automaticamente para la proxima vez.
        </p>
      </div>
    </section>
  )
}
