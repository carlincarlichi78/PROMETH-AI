import { useState } from 'react'
import { ChevronDown } from 'lucide-react'
import { useInView } from '../hooks/useInView'
import { formasJuridicas, type FormaJuridica } from '../data/formasJuridicas'

function TarjetaForma({
  forma,
  expandida,
  onToggle,
}: {
  forma: FormaJuridica
  expandida: boolean
  onToggle: () => void
}) {
  return (
    <div
      onClick={onToggle}
      className="glass-card p-4 cursor-pointer hover:border-spice-emerald/30 transition-all duration-300"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1">
          <h4 className="font-bold text-spice-text text-sm md:text-base">{forma.nombre}</h4>
          <p className="text-sm text-spice-text-muted mt-1">{forma.regimen}</p>
        </div>
        <ChevronDown
          className={`w-4 h-4 text-spice-text-muted shrink-0 mt-1 transition-transform duration-300 ${
            expandida ? 'rotate-180' : ''
          }`}
        />
      </div>

      {/* Badges de modelos */}
      {forma.modelos.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-3">
          {forma.modelos.map((modelo) => (
            <span
              key={modelo}
              className="bg-spice-emerald/20 text-spice-emerald text-xs px-2 py-0.5 rounded"
            >
              {modelo}
            </span>
          ))}
        </div>
      )}

      {/* Contenido expandido */}
      <div
        className={`overflow-hidden transition-all duration-300 ${
          expandida ? 'max-h-40 mt-3' : 'max-h-0'
        }`}
      >
        <div className="border-t border-spice-border pt-3">
          <p className="text-sm text-spice-text-muted">{forma.particularidades}</p>
        </div>
      </div>
    </div>
  )
}

export default function FormasJuridicas() {
  const { ref, visible } = useInView()
  const [expandida, setExpandida] = useState<string | null>(null)

  const fisicas = formasJuridicas.filter((f) => f.tipo === 'fisica')
  const juridicas = formasJuridicas.filter((f) => f.tipo === 'juridica')

  const toggleExpansion = (id: string) => {
    setExpandida((prev) => (prev === id ? null : id))
  }

  return (
    <section className="py-20 px-4" ref={ref}>
      <div className="max-w-6xl mx-auto">
        {/* Titulo */}
        <div className="text-center mb-12">
          <h2 className="text-3xl font-heading font-bold text-spice-text mb-3">
            Todas las formas juridicas, todos los regimenes
          </h2>
        </div>

        <div
          className={`space-y-12 transition-all duration-700 ${
            visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-6'
          }`}
        >
          {/* Personas fisicas */}
          <div>
            <h3 className="text-spice-gold font-heading font-semibold text-lg mb-4">
              Personas fisicas
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {fisicas.map((forma) => (
                <TarjetaForma
                  key={forma.id}
                  forma={forma}
                  expandida={expandida === forma.id}
                  onToggle={() => toggleExpansion(forma.id)}
                />
              ))}
            </div>
          </div>

          {/* Personas juridicas */}
          <div>
            <h3 className="text-spice-gold font-heading font-semibold text-lg mb-4">
              Personas juridicas
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {juridicas.map((forma) => (
                <TarjetaForma
                  key={forma.id}
                  forma={forma}
                  expandida={expandida === forma.id}
                  onToggle={() => toggleExpansion(forma.id)}
                />
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
