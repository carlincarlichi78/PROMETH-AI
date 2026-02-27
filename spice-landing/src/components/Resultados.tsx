import { CheckCircle, Shield } from 'lucide-react'
import { useInView } from '../hooks/useInView'
import { resultados } from '../data/metricas'

const casoReal = [
  '46 facturas procesadas',
  '11 proveedores distintos',
  '3 divisas (EUR, USD, GBP)',
  'IVA identico al calculo manual',
  'Balance cuadrado al centimo',
]

const capasConfianza = [
  { nombre: 'Lectura del documento', peso: 15 },
  { nombre: 'Cuadre aritmetico y PGC', peso: 25 },
  { nombre: 'Cruce por proveedor', peso: 20 },
  { nombre: 'Comparacion historica', peso: 10 },
  { nombre: 'Revision por IA', peso: 10 },
  { nombre: 'Comprobaciones globales', peso: 20 },
]

const niveles = [
  { rango: '95%+', etiqueta: 'FIABLE', color: 'bg-spice-emerald', texto: 'text-spice-emerald' },
  { rango: '85-94%', etiqueta: 'ACEPTABLE', color: 'bg-yellow-500', texto: 'text-yellow-500' },
  { rango: '70-84%', etiqueta: 'REVISION', color: 'bg-orange-500', texto: 'text-orange-500' },
  { rango: '<70%', etiqueta: 'CRITICO', color: 'bg-spice-red', texto: 'text-spice-red' },
]

export default function Resultados() {
  const { ref, visible } = useInView()
  const { ref: refConfianza, visible: visibleConfianza } = useInView()

  return (
    <section id="resultados" className="py-20 px-4" ref={ref}>
      <div className="max-w-6xl mx-auto">
        {/* Titulo */}
        <div className="text-center mb-12">
          <h2 className="text-3xl font-heading font-bold text-spice-text mb-3">
            Resultados reales
          </h2>
          <p className="text-spice-text-muted text-lg">
            Numeros obtenidos en pruebas con datos reales de una empresa
          </p>
        </div>

        {/* Grid de metricas */}
        <div
          className={`grid grid-cols-2 lg:grid-cols-3 gap-4 mb-12 transition-all duration-700 ${
            visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-6'
          }`}
        >
          {resultados.map((metrica, i) => (
            <div
              key={i}
              className="glass-card p-6 text-center"
              style={{ transitionDelay: `${i * 100}ms` }}
            >
              <div className="text-2xl md:text-3xl font-heading font-bold text-spice-emerald mb-2">
                {metrica.valor}
              </div>
              <p className="text-spice-text-muted text-sm">{metrica.etiqueta}</p>
            </div>
          ))}
        </div>

        {/* Caso real destacado */}
        <div
          className={`glass-card max-w-2xl mx-auto border-spice-emerald/50 p-6 mb-16 transition-all duration-700 delay-300 ${
            visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-6'
          }`}
        >
          <h3 className="text-xl font-heading font-bold text-spice-text mb-4 flex items-center gap-2">
            <CheckCircle className="w-5 h-5 text-spice-emerald shrink-0" />
            Caso real: Pastorino Costa del Sol S.L.
          </h3>
          <ul className="space-y-2">
            {casoReal.map((item, i) => (
              <li key={i} className="flex items-center gap-2 text-sm text-spice-text-muted">
                <div className="w-1.5 h-1.5 rounded-full bg-spice-emerald shrink-0" />
                {item}
              </li>
            ))}
          </ul>
        </div>

        {/* Indice de fiabilidad */}
        <div ref={refConfianza}>
          <div className="text-center mb-8">
            <h3 className="text-2xl font-heading font-bold text-spice-text flex items-center justify-center gap-2">
              <Shield className="w-6 h-6 text-spice-emerald" />
              Indice de fiabilidad
            </h3>
          </div>

          <div
            className={`max-w-2xl mx-auto space-y-4 transition-all duration-700 ${
              visibleConfianza ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-6'
            }`}
          >
            {capasConfianza.map((capa, i) => (
              <div
                key={i}
                className="flex items-center gap-4"
                style={{ transitionDelay: `${i * 100}ms` }}
              >
                <span className="text-sm text-spice-text-muted w-52 shrink-0 text-right">
                  {capa.nombre}
                </span>
                <div className="flex-1 h-6 bg-spice-emerald/10 rounded-full overflow-hidden relative">
                  <div
                    className={`h-full bg-spice-emerald rounded-full transition-all duration-1000 ease-out ${
                      visibleConfianza ? '' : 'w-0'
                    }`}
                    style={{
                      width: visibleConfianza ? `${capa.peso * 4}%` : '0%',
                      transitionDelay: `${i * 150}ms`,
                    }}
                  />
                  <span className="absolute inset-0 flex items-center justify-end pr-3 text-xs font-heading font-bold text-spice-text">
                    {capa.peso}%
                  </span>
                </div>
              </div>
            ))}
          </div>

          {/* Niveles */}
          <div className="flex flex-wrap justify-center gap-4 mt-8">
            {niveles.map((nivel) => (
              <div key={nivel.etiqueta} className="flex items-center gap-2">
                <div className={`w-3 h-3 rounded-full ${nivel.color}`} />
                <span className={`text-xs font-heading font-bold ${nivel.texto}`}>
                  {nivel.rango}
                </span>
                <span className="text-xs text-spice-text-muted">{nivel.etiqueta}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
