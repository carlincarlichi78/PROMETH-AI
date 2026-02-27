import { useInView } from '../hooks/useInView'
import {
  FileSearch,
  AlertTriangle,
  Lightbulb,
} from 'lucide-react'

/** Pasos de decision del clasificador */
const pasos = [
  {
    numero: 1,
    pregunta: 'Tengo una regla especifica para este CIF?',
    ejemplo: 'B12345678 siempre va a la 629',
    fiabilidad: 95,
  },
  {
    numero: 2,
    pregunta: 'He visto antes a este proveedor?',
    ejemplo: 'La ultima vez fue a servicios exteriores',
    fiabilidad: 85,
  },
  {
    numero: 3,
    pregunta: 'Reconozco el tipo de documento?',
    ejemplo: 'Es una nomina → cuenta 640 Sueldos',
    fiabilidad: 80,
  },
  {
    numero: 4,
    pregunta: 'Hay palabras clave que me orientan?',
    ejemplo: 'Dice "alquiler" → cuenta 621',
    fiabilidad: 60,
  },
  {
    numero: 5,
    pregunta: 'Tengo datos del libro diario anterior?',
    ejemplo: 'El ano pasado este CIF iba a la 629',
    fiabilidad: 75,
  },
]

/** Color de la barra de fiabilidad segun porcentaje */
function colorFiabilidad(porcentaje: number): string {
  if (porcentaje >= 80) return 'bg-spice-emerald'
  if (porcentaje >= 60) return 'bg-spice-gold'
  return 'bg-orange-500'
}

/** Texto del color de la barra */
function colorTextoFiabilidad(porcentaje: number): string {
  if (porcentaje >= 80) return 'text-spice-emerald'
  if (porcentaje >= 60) return 'text-spice-gold'
  return 'text-orange-500'
}

export default function DiagramaClasificador() {
  const { ref, visible } = useInView()

  return (
    <section id="clasificador" className="py-20 px-4" ref={ref}>
      <div className="max-w-3xl mx-auto">
        {/* Titulo */}
        <div
          className={`text-center mb-14 transition-all duration-700 ${
            visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-6'
          }`}
        >
          <h2 className="text-3xl md:text-4xl font-heading font-bold text-spice-text mb-3">
            Como decide la subcuenta: cascada de decision
          </h2>
          <p className="text-spice-text-muted text-lg max-w-2xl mx-auto">
            Paso a paso, como SPICE decide a que cuenta contable va cada
            documento
          </p>
        </div>

        {/* Diagrama vertical */}
        <div className="relative">
          {/* Nodo inicio */}
          <div
            className={`glass-card p-5 flex items-center gap-4 transition-all duration-700 ${
              visible
                ? 'opacity-100 translate-y-0'
                : 'opacity-0 translate-y-8'
            }`}
          >
            <FileSearch className="w-7 h-7 text-spice-emerald flex-shrink-0" />
            <div>
              <p className="font-heading font-bold text-spice-text">
                Documento leido
              </p>
              <p className="text-sm text-spice-text-muted">
                Datos extraidos por OCR triple consenso
              </p>
            </div>
          </div>

          {/* Pasos de decision */}
          {pasos.map((paso, i) => (
            <div key={paso.numero}>
              {/* Conector vertical */}
              <div className="ml-6 border-l-2 border-spice-emerald/40 h-8" />

              {/* Caja de pregunta */}
              <div
                className={`glass-card p-4 md:p-5 transition-all duration-700 ${
                  visible
                    ? 'opacity-100 translate-y-0'
                    : 'opacity-0 translate-y-8'
                }`}
                style={{ transitionDelay: `${(i + 1) * 150}ms` }}
              >
                <div className="flex flex-col md:flex-row md:items-start gap-3 md:gap-4">
                  {/* Contenido principal */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="flex-shrink-0 w-7 h-7 rounded-full bg-spice-emerald/20 flex items-center justify-center">
                        <span className="text-xs font-heading font-bold text-spice-emerald">
                          {paso.numero}
                        </span>
                      </span>
                      <h3 className="font-heading font-semibold text-spice-text text-sm md:text-base">
                        {paso.pregunta}
                      </h3>
                    </div>
                    <p className="text-sm text-spice-text-muted ml-9">
                      {paso.ejemplo}
                    </p>
                    <p className="text-xs text-spice-emerald/70 ml-9 mt-1">
                      SI → usa esta subcuenta
                    </p>
                  </div>

                  {/* Barra de fiabilidad */}
                  <div className="flex-shrink-0 md:w-36 ml-9 md:ml-0">
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-2.5 bg-white/10 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-1000 ease-out ${colorFiabilidad(paso.fiabilidad)}`}
                          style={{
                            width: visible ? `${paso.fiabilidad}%` : '0%',
                            transitionDelay: `${(i + 1) * 150 + 400}ms`,
                          }}
                        />
                      </div>
                      <span
                        className={`text-xs font-heading font-bold w-9 text-right ${colorTextoFiabilidad(paso.fiabilidad)}`}
                      >
                        {paso.fiabilidad}%
                      </span>
                    </div>
                    <p className="text-[10px] text-spice-text-muted mt-0.5 text-right">
                      fiabilidad
                    </p>
                  </div>
                </div>
              </div>
            </div>
          ))}

          {/* Conector a cuarentena */}
          <div className="ml-6 border-l-2 border-spice-red/40 h-8" />

          {/* Nodo cuarentena */}
          <div
            className={`glass-card border-spice-red p-5 flex items-start gap-4 transition-all duration-700 ${
              visible
                ? 'opacity-100 translate-y-0'
                : 'opacity-0 translate-y-8'
            }`}
            style={{ transitionDelay: '900ms' }}
          >
            <AlertTriangle className="w-6 h-6 text-spice-red flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-heading font-bold text-spice-red">
                CUARENTENA
              </p>
              <p className="text-sm text-spice-text-muted">
                El gestor decide, con opciones sugeridas por SPICE
              </p>
            </div>
          </div>

          {/* Conector a aprendizaje */}
          <div className="ml-6 border-l-2 border-spice-gold/40 h-8" />

          {/* Nodo aprendizaje */}
          <div
            className={`glass-card border-spice-gold p-5 flex items-start gap-4 transition-all duration-700 ${
              visible
                ? 'opacity-100 translate-y-0'
                : 'opacity-0 translate-y-8'
            }`}
            style={{ transitionDelay: '1050ms' }}
          >
            <Lightbulb className="w-6 h-6 text-spice-gold flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-heading font-bold text-spice-gold">
                SPICE APRENDE
              </p>
              <p className="text-sm text-spice-text-muted">
                La proxima vez ya sabra donde va. El gestor entrena al sistema
                con cada decision.
              </p>
            </div>
          </div>
        </div>

        {/* Nota inferior */}
        <p
          className={`text-sm text-spice-text-muted text-center mt-8 transition-all duration-700 ${
            visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
          }`}
          style={{ transitionDelay: '1200ms' }}
        >
          Si la fiabilidad es inferior al 70% en cualquier paso, el documento
          tambien va a cuarentena.
        </p>
      </div>
    </section>
  )
}
