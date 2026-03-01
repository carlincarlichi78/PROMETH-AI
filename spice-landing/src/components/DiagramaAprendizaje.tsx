import { useState } from 'react'
import { FileText, CheckCircle, BookMarked, AlertTriangle, ChevronDown, Lightbulb } from 'lucide-react'
import { useInView } from '../hooks/useInView'

/** Nodo del diagrama con icono y contenido */
function Nodo({
  children,
  icono,
  clase = '',
}: {
  children: React.ReactNode
  icono?: React.ReactNode
  clase?: string
}) {
  return (
    <div className={`glass-card p-4 flex items-center gap-3 ${clase}`}>
      {icono}
      <span className="text-sm md:text-base">{children}</span>
    </div>
  )
}

/** Flecha vertical entre nodos */
function FlechaAbajo() {
  return (
    <div className="flex justify-center py-1">
      <ChevronDown className="w-5 h-5 text-prometh-muted" />
    </div>
  )
}

/** Diamante de decision */
function Decision({ texto }: { texto: string }) {
  return (
    <div className="flex justify-center">
      <div className="bg-prometh-amber/10 border border-prometh-amber/30 rounded-lg px-4 py-2 text-center">
        <span className="text-sm font-heading text-prometh-amber">{texto}</span>
      </div>
    </div>
  )
}

/** Etiqueta de rama (SI / NO) */
function Rama({ texto, color }: { texto: string; color: 'emerald' | 'red' | 'gold' }) {
  const colores = {
    emerald: 'text-prometh-amber',
    red: 'text-prometh-red',
    gold: 'text-prometh-amber',
  }
  return (
    <span className={`text-xs font-heading font-bold ${colores[color]}`}>{texto}</span>
  )
}

const estrategias = [
  'Dar de alta al proveedor con los datos del documento',
  'Buscar un proveedor con nombre parecido',
  'Recuperar datos que faltan del propio documento',
  'Corregir formatos (fechas, importes...)',
  'Recalcular importes desde los datos disponibles',
  'Crear la subcuenta contable si no existe',
]

export default function DiagramaAprendizaje() {
  const { ref, visible } = useInView()
  const [estrategiaAbierta, setEstrategiaAbierta] = useState(false)

  return (
    <section className="py-20 px-4" ref={ref}>
      <div className="max-w-4xl mx-auto">
        {/* Titulo */}
        <div className="text-center mb-12">
          <h2 className="text-3xl font-heading font-bold text-prometh-text mb-3">
            Un sistema que mejora con el uso
          </h2>
          <p className="text-prometh-muted text-lg">
            Con cada documento que procesa, SPICE aprende
          </p>
        </div>

        {/* Diagrama */}
        <div
          className={`max-w-lg mx-auto flex flex-col gap-1 transition-all duration-700 ${
            visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-6'
          }`}
        >
          {/* Nodo inicio */}
          <Nodo
            icono={<FileText className="w-5 h-5 text-prometh-amber shrink-0" />}
            clase="border-prometh-amber/30"
          >
            Llega un documento
          </Nodo>

          <FlechaAbajo />

          {/* Intentar contabilizar */}
          <Nodo clase="border-prometh-border">Intentar contabilizar</Nodo>

          <FlechaAbajo />

          {/* Decision: algo falla? */}
          <Decision texto="Algo falla?" />

          {/* Rama NO: exito directo */}
          <div className="flex gap-4 mt-2">
            <div className="flex-1 flex flex-col items-center gap-1">
              <Rama texto="NO" color="emerald" />
              <div className="w-full bg-prometh-amber/10 border border-prometh-amber/40 rounded-lg p-3 flex items-center gap-2 justify-center">
                <CheckCircle className="w-4 h-4 text-prometh-amber shrink-0" />
                <span className="text-sm text-prometh-amber font-medium">
                  Contabilizado correctamente
                </span>
              </div>
            </div>
            <div className="flex-1 flex flex-col items-center gap-1">
              <Rama texto="SI" color="gold" />
              <ChevronDown className="w-4 h-4 text-prometh-muted" />
            </div>
          </div>

          {/* Decision: ya conozco este problema? */}
          <Decision texto="Ya conozco este problema?" />

          <div className="flex gap-4 mt-2">
            {/* Rama SI: solucion conocida */}
            <div className="flex-1 flex flex-col items-center gap-1">
              <Rama texto="SI" color="emerald" />
              <div className="glass-card p-3 w-full text-center">
                <span className="text-xs md:text-sm text-prometh-muted">
                  Aplicar solucion que funciono antes
                </span>
              </div>
              <ChevronDown className="w-4 h-4 text-prometh-muted" />
              <div className="w-full bg-prometh-amber/10 border border-prometh-amber/40 rounded-lg p-2 flex items-center gap-2 justify-center">
                <CheckCircle className="w-4 h-4 text-prometh-amber shrink-0" />
                <span className="text-xs text-prometh-amber">Resuelto</span>
              </div>
            </div>

            {/* Rama NO: probar estrategias */}
            <div className="flex-1 flex flex-col items-center gap-1">
              <Rama texto="NO" color="gold" />
              <ChevronDown className="w-4 h-4 text-prometh-muted" />
            </div>
          </div>

          {/* Estrategias */}
          <div className="mt-2">
            <button
              onClick={() => setEstrategiaAbierta(!estrategiaAbierta)}
              className="glass-card p-4 w-full text-left cursor-pointer hover:border-prometh-amber/30 transition-colors"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Lightbulb className="w-4 h-4 text-prometh-amber shrink-0" />
                  <span className="text-sm font-heading font-medium">
                    Probar 6 estrategias de resolucion
                  </span>
                </div>
                <ChevronDown
                  className={`w-4 h-4 text-prometh-muted transition-transform duration-300 ${
                    estrategiaAbierta ? 'rotate-180' : ''
                  }`}
                />
              </div>
              <div
                className={`overflow-hidden transition-all duration-300 ${
                  estrategiaAbierta ? 'max-h-80 mt-3' : 'max-h-0'
                }`}
              >
                <ol className="space-y-2">
                  {estrategias.map((e, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-prometh-muted">
                      <span className="text-prometh-amber font-heading font-bold shrink-0">
                        {i + 1}.
                      </span>
                      {e}
                    </li>
                  ))}
                </ol>
              </div>
            </button>
          </div>

          <FlechaAbajo />

          {/* Decision: se resolvio? */}
          <Decision texto="Se resolvio?" />

          <div className="flex gap-4 mt-2">
            {/* Rama SI: guardar */}
            <div className="flex-1 flex flex-col items-center gap-1">
              <Rama texto="SI" color="emerald" />
              <div className="w-full bg-prometh-amber/10 border border-prometh-amber/40 rounded-lg p-3 flex items-center gap-2 justify-center">
                <BookMarked className="w-4 h-4 text-prometh-amber shrink-0" />
                <span className="text-xs md:text-sm text-prometh-amber font-medium">
                  Guardar solucion para la proxima vez
                </span>
              </div>
            </div>

            {/* Rama NO: cuarentena */}
            <div className="flex-1 flex flex-col items-center gap-1">
              <Rama texto="NO" color="red" />
              <div className="w-full bg-prometh-red/10 border border-prometh-red/40 rounded-lg p-3 flex items-center gap-2 justify-center">
                <AlertTriangle className="w-4 h-4 text-prometh-red shrink-0" />
                <span className="text-xs md:text-sm text-prometh-red font-medium">
                  CUARENTENA: preguntar al gestor
                </span>
              </div>
              <ChevronDown className="w-4 h-4 text-prometh-muted" />
              <div className="w-full bg-prometh-amber/10 border border-prometh-amber/40 rounded-lg p-2 flex items-center gap-2 justify-center">
                <BookMarked className="w-3 h-3 text-prometh-amber shrink-0" />
                <span className="text-xs text-prometh-amber">
                  Aplicar su decision y aprender de ella
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Ejemplo visual */}
        <div
          className={`glass-card max-w-lg mx-auto mt-12 p-6 transition-all duration-700 delay-300 ${
            visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-6'
          }`}
        >
          <div className="space-y-4">
            <div className="flex items-start gap-3">
              <div className="w-2 h-2 rounded-full bg-prometh-amber mt-2 shrink-0" />
              <p className="text-sm text-prometh-muted">
                <span className="text-prometh-text font-medium">Lunes:</span> llega factura
                de proveedor nuevo. SPICE no lo conoce → pregunta al gestor.
              </p>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-2 h-2 rounded-full bg-prometh-amber mt-2 shrink-0" />
              <p className="text-sm text-prometh-muted">
                <span className="text-prometh-text font-medium">Martes:</span> llega otra
                factura del mismo proveedor → SPICE ya sabe quien es.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
