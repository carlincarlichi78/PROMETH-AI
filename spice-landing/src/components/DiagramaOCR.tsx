import { FileText, HelpCircle, CheckCircle, ArrowDown } from 'lucide-react'
import { useInView } from '../hooks/useInView'

/** Flecha vertical entre nodos */
function Flecha() {
  return (
    <div className="flex justify-center">
      <div className="border-l-2 border-spice-emerald h-8 relative">
        <ArrowDown
          size={16}
          className="text-spice-emerald absolute -bottom-2 -left-[9px]"
        />
      </div>
    </div>
  )
}

/** Conector horizontal (visible solo en desktop, para ramas SI/NO) */
function ConectorHorizontal({ lado }: { lado: 'izquierda' | 'derecha' }) {
  return (
    <div
      className={`hidden md:block absolute top-1/2 -translate-y-1/2 w-8 border-t-2 border-spice-emerald ${
        lado === 'izquierda' ? 'right-full' : 'left-full'
      }`}
    />
  )
}

/** Caja de proceso estandar */
function CajaProceso({ texto, delay }: { texto: string; delay: number }) {
  return (
    <div
      className="glass-card border-l-4 border-spice-emerald p-4 max-w-md mx-auto text-center animate-fade-in-up"
      style={{ animationDelay: `${delay}ms` }}
    >
      <p className="text-spice-text text-sm md:text-base">{texto}</p>
    </div>
  )
}

/** Caja de decision (simula diamante con estilo diferente) */
function CajaDecision({
  texto,
  delay,
}: {
  texto: string
  delay: number
}) {
  return (
    <div
      className="glass-card bg-spice-emerald/5 border-spice-emerald/40 p-4 max-w-md mx-auto text-center animate-fade-in-up"
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className="flex items-center justify-center gap-2 mb-1">
        <HelpCircle size={18} className="text-spice-gold shrink-0" />
        <span className="text-spice-gold font-heading font-semibold text-sm uppercase tracking-wide">
          Decision
        </span>
      </div>
      <p className="text-spice-text text-sm md:text-base">{texto}</p>
    </div>
  )
}

/** Caja de resultado de nivel */
function CajaNivel({
  nivel,
  titulo,
  porcentaje,
  motores,
  color,
  delay,
}: {
  nivel: number
  titulo: string
  porcentaje: string
  motores: string
  color: 'emerald' | 'yellow' | 'orange'
  delay: number
}) {
  const estilos = {
    emerald: 'bg-emerald-900/30 border-spice-emerald',
    yellow: 'bg-yellow-900/30 border-yellow-500',
    orange: 'bg-orange-900/30 border-orange-500',
  }
  const textoColor = {
    emerald: 'text-spice-emerald',
    yellow: 'text-yellow-400',
    orange: 'text-orange-400',
  }

  return (
    <div
      className={`glass-card border-l-4 p-4 ${estilos[color]} animate-fade-in-up`}
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className="flex items-center gap-2 mb-1">
        <CheckCircle size={18} className={textoColor[color]} />
        <span className={`font-heading font-bold text-sm ${textoColor[color]}`}>
          NIVEL {nivel}
        </span>
      </div>
      <p className="text-spice-text font-semibold text-sm md:text-base">{titulo}</p>
      <div className="flex items-center gap-3 mt-2 text-xs text-spice-text-muted">
        <span className={`font-bold ${textoColor[color]}`}>{porcentaje}</span>
        <span>{motores}</span>
      </div>
    </div>
  )
}

/** Etiqueta SI/NO sobre una rama */
function EtiquetaRama({
  texto,
  color,
}: {
  texto: string
  color: 'emerald' | 'red'
}) {
  const cls =
    color === 'emerald'
      ? 'bg-spice-emerald/20 text-spice-emerald'
      : 'bg-spice-red/20 text-spice-red'
  return (
    <span
      className={`inline-block text-xs font-bold px-2 py-0.5 rounded-full ${cls}`}
    >
      {texto}
    </span>
  )
}

export default function DiagramaOCR() {
  const { ref, visible } = useInView()

  return (
    <section id="lectura" className="py-20 px-4" ref={ref}>
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
            Lectura inteligente de documentos
          </h2>
          <p
            className={`text-spice-text-muted max-w-xl mx-auto transition-all duration-700 delay-150 ${
              visible
                ? 'opacity-100 translate-y-0'
                : 'opacity-0 translate-y-6'
            }`}
          >
            Tres niveles de verificacion para garantizar la maxima precision
          </p>
        </div>

        {/* Diagrama */}
        {visible && (
          <div className="flex flex-col items-center">
            {/* --- Nodo inicial --- */}
            <div className="glass-card p-5 flex items-center gap-3 animate-fade-in-up max-w-xs mx-auto">
              <FileText size={28} className="text-spice-emerald shrink-0" />
              <span className="text-spice-text font-heading font-semibold">
                Llega un documento
              </span>
            </div>

            <Flecha />

            {/* --- Motor 1 --- */}
            <CajaProceso
              texto="Motor de IA #1 lee el documento"
              delay={100}
            />

            <Flecha />

            {/* --- Decision 1 --- */}
            <CajaDecision
              texto="Los datos son claros y cuadran?"
              delay={200}
            />

            {/* --- Ramas Decision 1 --- */}
            <div className="w-full max-w-3xl mt-2">
              {/* Layout desktop: 2 columnas con gap central */}
              <div className="flex flex-col md:flex-row md:items-start gap-4 md:gap-6">
                {/* Rama SI — Nivel 1 */}
                <div className="flex-1 flex flex-col items-center gap-2">
                  <EtiquetaRama texto="SI" color="emerald" />
                  <div className="relative w-full">
                    <ConectorHorizontal lado="derecha" />
                    <CajaNivel
                      nivel={1}
                      titulo="Lectura directa"
                      porcentaje="~70% de los documentos"
                      motores="1 motor"
                      color="emerald"
                      delay={300}
                    />
                  </div>
                </div>

                {/* Rama NO — continua */}
                <div className="flex-1 flex flex-col items-center gap-2">
                  <EtiquetaRama texto="NO" color="red" />
                  <div className="relative w-full">
                    <ConectorHorizontal lado="izquierda" />
                    <div className="flex flex-col items-center gap-0">
                      {/* Motor 2 */}
                      <CajaProceso
                        texto="Motor de IA #2 lee el mismo documento"
                        delay={400}
                      />

                      <Flecha />

                      {/* Decision 2 */}
                      <CajaDecision
                        texto="Ambos motores coinciden?"
                        delay={500}
                      />

                      {/* Ramas Decision 2 */}
                      <div className="w-full mt-2">
                        <div className="flex flex-col md:flex-row md:items-start gap-4 md:gap-6">
                          {/* Rama SI — Nivel 2 */}
                          <div className="flex-1 flex flex-col items-center gap-2">
                            <EtiquetaRama texto="SI" color="emerald" />
                            <CajaNivel
                              nivel={2}
                              titulo="Doble lectura"
                              porcentaje="~25% de los documentos"
                              motores="2 motores"
                              color="yellow"
                              delay={600}
                            />
                          </div>

                          {/* Rama NO — Nivel 3 */}
                          <div className="flex-1 flex flex-col items-center gap-2">
                            <EtiquetaRama texto="NO" color="red" />
                            <div className="flex flex-col items-center gap-0 w-full">
                              <CajaProceso
                                texto="Motor de IA #3 lee el documento"
                                delay={700}
                              />

                              <Flecha />

                              <div
                                className="glass-card bg-orange-900/20 border-orange-500/40 p-3 max-w-md mx-auto text-center animate-fade-in-up text-sm text-orange-300"
                                style={{ animationDelay: '750ms' }}
                              >
                                Se queda con lo que digan 2 de 3
                              </div>

                              <Flecha />

                              <CajaNivel
                                nivel={3}
                                titulo="Triple lectura, maxima seguridad"
                                porcentaje="~5% de los documentos"
                                motores="3 motores"
                                color="orange"
                                delay={800}
                              />
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Texto explicativo */}
            <p
              className="mt-12 max-w-2xl mx-auto text-center text-spice-text-muted text-sm md:text-base leading-relaxed animate-fade-in-up"
              style={{ animationDelay: '900ms' }}
            >
              El 70% de los documentos se leen correctamente a la primera. Solo
              los mas complejos necesitan triple verificacion. Asi se optimiza el
              coste sin sacrificar precision.
            </p>
          </div>
        )}
      </div>
    </section>
  )
}
