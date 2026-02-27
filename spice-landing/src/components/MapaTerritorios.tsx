import { useState } from 'react'
import { MapPin } from 'lucide-react'
import { useInView } from '../hooks/useInView'
import { territorios, type Territorio } from '../data/territorios'

/** Tarjeta clicable de un territorio en el grid */
function TarjetaTerritorio({
  territorio,
  seleccionado,
  onClick,
}: {
  territorio: Territorio
  seleccionado: boolean
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={`glass-card p-4 text-left transition-all duration-300 cursor-pointer ${
        seleccionado
          ? 'scale-105 shadow-lg border-2'
          : 'hover:scale-[1.02] border border-spice-border'
      }`}
      style={{
        borderColor: seleccionado ? territorio.color : undefined,
        boxShadow: seleccionado
          ? `0 0 24px ${territorio.color}20`
          : undefined,
      }}
    >
      <div className="flex items-center gap-2 mb-1">
        <MapPin
          size={16}
          strokeWidth={2}
          style={{ color: territorio.color }}
        />
        <span
          className="font-heading font-bold text-sm"
          style={{ color: seleccionado ? territorio.color : undefined }}
        >
          {territorio.nombre}
        </span>
      </div>
      <p className="text-xs text-spice-text-muted">{territorio.impuesto}</p>
    </button>
  )
}

/** Panel de detalle del territorio seleccionado */
function DetalleTerritorioPanel({ territorio }: { territorio: Territorio }) {
  return (
    <div className="glass-card p-6 h-full">
      {/* Nombre con color */}
      <h3
        className="text-2xl font-heading font-bold mb-4"
        style={{ color: territorio.color }}
      >
        {territorio.nombre}
      </h3>

      {/* Impuesto indirecto + tipos */}
      <div className="mb-4">
        <p className="text-xs uppercase text-spice-text-muted font-medium mb-2">
          Impuesto indirecto
        </p>
        <p className="font-heading font-bold text-spice-text mb-2">
          {territorio.impuesto}
        </p>
        <div className="flex flex-wrap gap-2">
          {territorio.tipos.map((tipo) => (
            <span
              key={tipo.nombre}
              className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium border"
              style={{
                borderColor: `${territorio.color}50`,
                color: territorio.color,
                backgroundColor: `${territorio.color}10`,
              }}
            >
              {tipo.nombre}: {tipo.pct}%
            </span>
          ))}
        </div>
      </div>

      {/* Impuesto de Sociedades */}
      <div className="mb-4">
        <p className="text-xs uppercase text-spice-text-muted font-medium mb-1">
          Impuesto de Sociedades
        </p>
        <p className="text-sm text-spice-text/90">{territorio.is}</p>
      </div>

      {/* Modelos */}
      <div>
        <p className="text-xs uppercase text-spice-text-muted font-medium mb-1">
          Modelos fiscales
        </p>
        <p className="text-sm text-spice-text/90">{territorio.modelos}</p>
      </div>
    </div>
  )
}

export default function MapaTerritorios() {
  const [seleccionadoId, setSeleccionadoId] = useState('peninsula')
  const { ref, visible } = useInView()

  const territorioActivo = territorios.find((t) => t.id === seleccionadoId) ?? territorios[0]

  return (
    <section id="territorios" className="py-20 px-4">
      <div className="max-w-5xl mx-auto">
        {/* Titulo y subtitulo */}
        <h2 className="text-3xl md:text-4xl font-heading font-bold text-center text-spice-text mb-4">
          5 territorios fiscales, un solo sistema
        </h2>
        <p className="text-center text-spice-text-muted mb-12 max-w-2xl mx-auto">
          Configuras el territorio del cliente y SPICE aplica la normativa correcta
        </p>

        {/* Grid: mapa + detalle */}
        <div
          ref={ref}
          className={`grid grid-cols-1 lg:grid-cols-2 gap-8 transition-all duration-700 ${
            visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'
          }`}
        >
          {/* Mapa conceptual: grid 2x3 con 5 tarjetas */}
          <div className="grid grid-cols-2 gap-3">
            {territorios.map((territorio) => (
              <TarjetaTerritorio
                key={territorio.id}
                territorio={territorio}
                seleccionado={territorio.id === seleccionadoId}
                onClick={() => setSeleccionadoId(territorio.id)}
              />
            ))}
          </div>

          {/* Panel de detalle */}
          <DetalleTerritorioPanel territorio={territorioActivo} />
        </div>

        {/* Destacado inferior */}
        <p className="text-center text-spice-text-muted mt-10 max-w-2xl mx-auto text-sm leading-relaxed">
          Cada 1 de enero se actualiza la normativa con los tipos vigentes del nuevo ejercicio.
          Sin tocar el programa.
        </p>
      </div>
    </section>
  )
}
