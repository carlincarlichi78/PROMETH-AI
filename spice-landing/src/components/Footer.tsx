import { useInView } from '../hooks/useInView'

const hitos = [
  {
    etiqueta: 'Hoy',
    color: 'bg-spice-emerald',
    borde: 'border-spice-emerald',
    descripcion:
      'Contabilizacion automatica, lectura inteligente, aprendizaje evolutivo',
  },
  {
    etiqueta: 'En desarrollo',
    color: 'bg-spice-gold',
    borde: 'border-spice-gold',
    descripcion:
      'Panel de control en tiempo real, cierre de ejercicio automatizado',
  },
  {
    etiqueta: 'Proximo',
    color: 'bg-spice-text-muted',
    borde: 'border-spice-text-muted',
    descripcion:
      'Servicio en la nube para gestorias, calendario fiscal, conciliacion bancaria',
  },
]

export default function Footer() {
  const { ref, visible } = useInView()

  return (
    <footer className="py-16 px-4 border-t border-spice-border" ref={ref}>
      <div className="max-w-4xl mx-auto">
        {/* Roadmap timeline */}
        <div
          className={`transition-all duration-700 ${
            visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-6'
          }`}
        >
          {/* Timeline horizontal en desktop, vertical en mobile */}
          <div className="relative">
            {/* Linea horizontal (desktop) */}
            <div className="hidden md:block absolute top-4 left-0 right-0 h-px bg-spice-border" />

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              {hitos.map((hito, i) => (
                <div key={i} className="relative flex flex-col items-center text-center">
                  {/* Dot */}
                  <div
                    className={`w-8 h-8 rounded-full ${hito.color} border-4 border-spice-bg relative z-10 shrink-0`}
                  />

                  {/* Contenido */}
                  <div className="mt-4">
                    <h4 className="font-heading font-bold text-spice-text text-sm mb-2">
                      {hito.etiqueta}
                    </h4>
                    <p className="text-sm text-spice-text-muted leading-relaxed">
                      {hito.descripcion}
                    </p>
                  </div>

                  {/* Linea vertical entre nodos (mobile) */}
                  {i < hitos.length - 1 && (
                    <div className="md:hidden w-px h-6 bg-spice-border mt-4" />
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Separador */}
        <div className="border-t border-spice-border my-12" />

        {/* Credits */}
        <div className="text-center space-y-2">
          <p className="text-spice-text text-sm">
            Desarrollado por{' '}
            <span className="font-heading font-semibold">Carlos Canete Gomez</span>
          </p>
          <a
            href="https://carloscanetegomez.dev"
            target="_blank"
            rel="noopener noreferrer"
            className="text-spice-emerald hover:underline text-sm inline-block"
          >
            carloscanetegomez.dev
          </a>
          <p className="text-spice-text-muted text-sm">&copy; 2026</p>
        </div>
      </div>
    </footer>
  )
}
