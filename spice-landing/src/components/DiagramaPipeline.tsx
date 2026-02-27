import {
  Scan,
  ShieldCheck,
  FilePlus,
  BookOpen,
  Wrench,
  CheckCircle,
  FileOutput,
  FolderOpen,
} from 'lucide-react'
import { useInView } from '../hooks/useInView'
import { fases } from '../data/pipeline'
import type { FasePipeline } from '../data/pipeline'

/** Mapeo icono string -> componente lucide */
const iconos: Record<string, React.ComponentType<{ className?: string; size?: number }>> = {
  'scan': Scan,
  'shield-check': ShieldCheck,
  'file-plus': FilePlus,
  'book-open': BookOpen,
  'wrench': Wrench,
  'check-circle': CheckCircle,
  'file-output': FileOutput,
}

function NodoPipeline({ fase, indice }: { fase: FasePipeline; indice: number }) {
  const { ref, visible } = useInView()
  const Icono = iconos[fase.icono] ?? Scan

  return (
    <div
      ref={ref}
      className="relative flex items-start gap-4 md:gap-6 transition-all duration-600"
      style={{
        opacity: visible ? 1 : 0,
        transform: visible ? 'translateX(0)' : 'translateX(-32px)',
        transitionDelay: `${indice * 120}ms`,
      }}
    >
      {/* Circulo numerado */}
      <div className="relative z-10 flex-shrink-0 flex items-center justify-center w-10 h-10 rounded-full bg-spice-emerald text-white font-heading font-bold text-sm">
        {fase.numero}
      </div>

      {/* Caja de contenido */}
      <div className="glass-card p-4 md:p-5 flex-1">
        <div className="flex items-center gap-2 mb-1">
          <Icono className="text-spice-emerald" size={18} />
          <h3 className="font-heading font-bold text-spice-text text-sm md:text-base tracking-wide">
            {fase.nombre}
          </h3>
        </div>
        <p className="text-spice-text text-sm mb-1">{fase.descripcion}</p>
        <p className="text-spice-text-muted text-xs leading-relaxed mb-2">{fase.detalle}</p>
        <p className="text-spice-gold text-sm font-medium">{fase.datoClave}</p>
      </div>
    </div>
  )
}

function CajaEntrada() {
  const { ref, visible } = useInView()

  return (
    <div
      ref={ref}
      className="glass-card p-5 md:p-6 border-spice-gold/40 transition-all duration-600 max-w-2xl mx-auto"
      style={{
        opacity: visible ? 1 : 0,
        transform: visible ? 'translateY(0)' : 'translateY(24px)',
        borderColor: 'rgba(212, 160, 23, 0.4)',
      }}
    >
      <div className="flex items-center gap-3">
        <FolderOpen className="text-spice-gold flex-shrink-0" size={28} />
        <div>
          <p className="font-heading font-bold text-spice-text text-sm md:text-base">
            Documentos del cliente
          </p>
          <p className="text-spice-text-muted text-xs md:text-sm">
            Facturas, nominas, extractos bancarios, recibos de la Seguridad Social, impuestos, seguros...
          </p>
        </div>
      </div>
    </div>
  )
}

function CajaSalida() {
  const { ref, visible } = useInView()

  return (
    <div
      ref={ref}
      className="glass-card p-5 md:p-6 transition-all duration-600 max-w-2xl mx-auto"
      style={{
        opacity: visible ? 1 : 0,
        transform: visible ? 'translateY(0)' : 'translateY(24px)',
        borderColor: 'rgba(16, 185, 129, 0.4)',
      }}
    >
      <div className="flex items-center gap-3">
        <CheckCircle className="text-spice-emerald flex-shrink-0" size={28} />
        <div>
          <p className="font-heading font-bold text-spice-text text-sm md:text-base">
            Contabilidad verificada
          </p>
          <p className="text-spice-text-muted text-xs md:text-sm">
            Indice de fiabilidad 95%+ — Libros, modelos fiscales e informes listos para presentar
          </p>
        </div>
      </div>
    </div>
  )
}

export default function DiagramaPipeline() {
  return (
    <section id="proceso" className="py-20 px-4">
      {/* Titulo */}
      <div className="text-center mb-12 max-w-3xl mx-auto">
        <h2 className="text-3xl md:text-4xl font-heading font-bold text-spice-text mb-3">
          Proceso de contabilizacion en 7 pasos
        </h2>
        <p className="text-spice-text-muted text-base md:text-lg">
          Desde que el documento entra hasta que el asiento esta verificado
        </p>
      </div>

      {/* Caja de entrada */}
      <CajaEntrada />

      {/* Conector entrada -> primer nodo */}
      <div className="flex justify-center my-4">
        <svg width="2" height="32" className="overflow-visible">
          <line
            x1="1" y1="0" x2="1" y2="32"
            stroke="rgba(16, 185, 129, 0.4)"
            strokeWidth="2"
            strokeDasharray="4 4"
          />
        </svg>
      </div>

      {/* Pipeline vertical */}
      <div className="relative max-w-2xl mx-auto">
        {/* Linea SVG central (visible solo en md+) */}
        <div className="hidden md:block absolute left-5 top-0 bottom-0 w-px">
          <svg width="2" height="100%" className="overflow-visible">
            <line
              x1="1" y1="0" x2="1" y2="100%"
              stroke="rgba(16, 185, 129, 0.2)"
              strokeWidth="2"
            />
          </svg>
        </div>

        {/* Linea vertical mobile */}
        <div className="md:hidden absolute left-5 top-0 bottom-0 w-px bg-spice-emerald/20" />

        {/* Nodos */}
        <div className="flex flex-col gap-6">
          {fases.map((fase, i) => (
            <NodoPipeline key={fase.numero} fase={fase} indice={i} />
          ))}
        </div>
      </div>

      {/* Conector ultimo nodo -> salida */}
      <div className="flex justify-center my-4">
        <svg width="2" height="32" className="overflow-visible">
          <line
            x1="1" y1="0" x2="1" y2="32"
            stroke="rgba(16, 185, 129, 0.4)"
            strokeWidth="2"
            strokeDasharray="4 4"
          />
        </svg>
      </div>

      {/* Caja de salida */}
      <CajaSalida />
    </section>
  )
}
