import { useInView } from '../hooks/useInView'
import { Shield } from 'lucide-react'

/** Datos de los 6 niveles de la piramide */
const niveles = [
  {
    nivel: 0,
    titulo: 'NORMATIVA VIGENTE',
    descripcion: 'La ley siempre manda',
    ejemplo: 'IVA general 2025 = 21%',
    maxW: 'max-w-4xl',
    fondo: 'bg-amber-900/40 border-spice-gold',
  },
  {
    nivel: 1,
    titulo: 'PLAN GENERAL CONTABLE',
    descripcion: 'Estructura de cuentas',
    ejemplo: 'Grupo 6 = gastos',
    maxW: 'max-w-[52rem]',
    fondo: 'bg-amber-800/30 border-amber-700/40',
  },
  {
    nivel: 2,
    titulo: 'PERFIL FISCAL',
    descripcion: 'Obligaciones segun forma juridica',
    ejemplo: 'S.L. peninsula: IS 25%, modelo 303',
    maxW: 'max-w-[46rem]',
    fondo: 'bg-amber-700/20 border-amber-600/30',
  },
  {
    nivel: 3,
    titulo: 'CRITERIO DEL GESTOR',
    descripcion: 'Reglas del despacho',
    ejemplo: 'Alquiler siempre a cuenta 621',
    maxW: 'max-w-[38rem]',
    fondo: 'bg-emerald-900/30 border-emerald-700/30',
  },
  {
    nivel: 4,
    titulo: 'CONFIGURACION CLIENTE',
    descripcion: 'Mapeo especifico',
    ejemplo: 'Acme SL → subcuenta 6290000001',
    maxW: 'max-w-[30rem]',
    fondo: 'bg-emerald-800/30 border-emerald-600/30',
  },
  {
    nivel: 5,
    titulo: 'APRENDIZAJE',
    descripcion: 'Lo que SPICE ha aprendido',
    ejemplo: 'Acme factura servicios informaticos',
    maxW: 'max-w-[22rem]',
    fondo: 'bg-spice-emerald/20 border-spice-emerald/40',
  },
]

export default function DiagramaJerarquia() {
  const { ref, visible } = useInView()

  return (
    <section id="jerarquia" className="py-20 px-4" ref={ref}>
      <div className="max-w-6xl mx-auto">
        {/* Titulo */}
        <div
          className={`text-center mb-14 transition-all duration-700 ${
            visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-6'
          }`}
        >
          <h2 className="text-3xl md:text-4xl font-heading font-bold text-spice-text mb-3">
            Como decide SPICE: jerarquia de criterios contables
          </h2>
          <p className="text-spice-text-muted text-lg max-w-2xl mx-auto">
            Cada decision contable respeta un orden de autoridad
          </p>
        </div>

        {/* Piramide con indicador lateral */}
        <div className="relative">
          {/* Flecha lateral de AUTORIDAD — visible solo en md+ */}
          <div className="hidden md:flex absolute -left-2 top-0 bottom-16 w-16 flex-col items-center justify-between">
            {/* Flecha vertical */}
            <div className="relative flex-1 flex flex-col items-center">
              <span className="text-xs font-heading font-bold text-spice-gold tracking-widest rotate-0 mb-2">
                MAX
              </span>
              <div className="flex-1 w-px bg-gradient-to-b from-spice-gold via-spice-gold/50 to-spice-emerald/30 relative">
                {/* Punta superior */}
                <div className="absolute -top-1 left-1/2 -translate-x-1/2 w-0 h-0 border-l-[5px] border-r-[5px] border-b-[8px] border-l-transparent border-r-transparent border-b-spice-gold" />
                {/* Punta inferior */}
                <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-0 h-0 border-l-[5px] border-r-[5px] border-t-[8px] border-l-transparent border-r-transparent border-t-spice-emerald/40" />
              </div>
              <span className="text-xs font-heading font-bold text-spice-emerald/60 tracking-widest mt-2">
                MIN
              </span>
            </div>
            {/* Texto vertical AUTORIDAD */}
            <div className="absolute top-1/2 -translate-y-1/2 -rotate-90 whitespace-nowrap">
              <span className="text-sm font-heading font-bold text-spice-text-muted/50 tracking-[0.3em] uppercase">
                Autoridad
              </span>
            </div>
          </div>

          {/* Niveles de la piramide */}
          <div className="flex flex-col items-center gap-3 md:ml-16">
            {niveles.map((n, i) => (
              <div
                key={n.nivel}
                className={`w-full ${n.maxW} mx-auto rounded-lg border p-4 md:p-5 ${n.fondo} transition-all duration-700 ${
                  visible
                    ? 'opacity-100 translate-y-0'
                    : 'opacity-0 translate-y-8'
                }`}
                style={{ transitionDelay: `${i * 120}ms` }}
              >
                <div className="flex items-start gap-3 md:gap-4">
                  {/* Numero de nivel */}
                  <div className="flex-shrink-0 w-9 h-9 rounded-full bg-white/10 flex items-center justify-center">
                    <span className="text-sm font-heading font-bold text-spice-text">
                      {n.nivel}
                    </span>
                  </div>

                  {/* Contenido */}
                  <div className="flex-1 min-w-0">
                    <h3 className="font-heading font-bold text-spice-text text-sm md:text-base tracking-wide">
                      {n.titulo}
                    </h3>
                    <p className="text-spice-text-muted text-sm mt-0.5">
                      {n.descripcion}
                    </p>
                    <p className="text-spice-text/60 text-xs md:text-sm mt-1 italic">
                      Ej: {n.ejemplo}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Destacado inferior */}
        <div
          className={`mt-10 max-w-3xl mx-auto transition-all duration-700 ${
            visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-6'
          }`}
          style={{ transitionDelay: '800ms' }}
        >
          <div className="glass-card border-spice-gold p-5 md:p-6 flex items-start gap-4">
            <Shield className="w-6 h-6 text-spice-gold flex-shrink-0 mt-0.5" />
            <p className="text-spice-text text-sm md:text-base leading-relaxed">
              <span className="font-heading font-bold text-spice-gold">
                La normativa siempre prevalece.
              </span>{' '}
              Ningun criterio inferior puede contradecir a uno superior. SPICE
              respeta esta jerarquia en cada asiento que genera.
            </p>
          </div>
        </div>
      </div>
    </section>
  )
}
