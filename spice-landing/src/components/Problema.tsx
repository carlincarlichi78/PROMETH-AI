import { Clock, FileWarning, AlertTriangle, CalendarClock, ArrowRight } from 'lucide-react'
import { useInView } from '../hooks/useInView'

interface PainPoint {
  icono: React.ElementType
  titulo: string
  descripcion: string
}

const painPoints: PainPoint[] = [
  {
    icono: Clock,
    titulo: 'Registro manual',
    descripcion:
      'Cada factura requiere 3 minutos de introduccion manual. Con 200 facturas al mes, son 10 horas solo de data entry.',
  },
  {
    icono: FileWarning,
    titulo: 'Cada proveedor, un formato',
    descripcion:
      'No hay dos facturas iguales. Diferentes plantillas, posiciones, formatos de fecha, desglose de IVA...',
  },
  {
    icono: AlertTriangle,
    titulo: 'Errores de transcripcion',
    descripcion:
      'Un CIF mal copiado, un IVA aplicado incorrectamente, un importe cruzado. Y no se detecta hasta la presentacion del modelo.',
  },
  {
    icono: CalendarClock,
    titulo: 'Plazos que no esperan',
    descripcion:
      'El 303, el 111, el 130... cada 20 dias hay un plazo. Y un error en los datos de base arrastra a todos los modelos.',
  },
]

function TarjetaPain({ punto }: { punto: PainPoint }) {
  const Icono = punto.icono
  return (
    <div className="glass-card p-6 hover:border-spice-red/30 transition-colors">
      <Icono className="text-spice-red mb-4" size={32} strokeWidth={1.5} />
      <h3 className="text-lg font-heading font-bold text-spice-text mb-2">
        {punto.titulo}
      </h3>
      <p className="text-spice-text-muted font-body text-sm leading-relaxed">
        {punto.descripcion}
      </p>
    </div>
  )
}

function Comparativo() {
  const { ref, visible } = useInView()

  return (
    <div ref={ref} className="mt-16 flex flex-col items-center">
      <div
        className={`flex flex-col sm:flex-row items-center gap-4 sm:gap-8 transition-all duration-700 ${
          visible
            ? 'opacity-100 translate-y-0'
            : 'opacity-0 translate-y-8'
        }`}
      >
        {/* Antes */}
        <div className="glass-card px-6 py-4 text-center border-spice-red/30">
          <p className="text-3xl font-heading font-bold text-spice-red">
            10 h<span className="text-lg font-normal text-spice-text-muted">/mes</span>
          </p>
          <p className="text-sm text-spice-text-muted mt-1">
            de registro manual
          </p>
        </div>

        {/* Flecha */}
        <div
          className={`transition-all duration-700 delay-300 ${
            visible ? 'opacity-100 scale-100' : 'opacity-0 scale-50'
          }`}
        >
          <ArrowRight
            className="text-spice-emerald rotate-90 sm:rotate-0"
            size={32}
            strokeWidth={2}
          />
        </div>

        {/* Despues */}
        <div className="glass-card px-6 py-4 text-center border-spice-emerald/30">
          <p className="text-3xl font-heading font-bold text-spice-emerald">
            15 min<span className="text-lg font-normal text-spice-text-muted">/mes</span>
          </p>
          <p className="text-sm text-spice-text-muted mt-1">
            de supervision
          </p>
        </div>
      </div>
    </div>
  )
}

export default function Problema() {
  return (
    <section id="problema" className="py-20 px-4">
      <div className="max-w-5xl mx-auto">
        {/* Titulo */}
        <h2 className="text-3xl md:text-4xl font-heading font-bold text-center text-spice-text mb-12">
          El dia a dia en un despacho
        </h2>

        {/* Grid de pain points */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {painPoints.map((punto) => (
            <TarjetaPain key={punto.titulo} punto={punto} />
          ))}
        </div>

        {/* Comparativo animado */}
        <Comparativo />
      </div>
    </section>
  )
}
