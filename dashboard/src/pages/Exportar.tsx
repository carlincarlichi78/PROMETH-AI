import { useState } from 'react'

/** Formatos de exportacion disponibles */
type FormatoExportar = 'csv_diario' | 'excel_multihoja' | 'csv_facturas'

/** Descripcion de cada formato */
const FORMATOS: { valor: FormatoExportar; etiqueta: string; descripcion: string }[] = [
  {
    valor: 'csv_diario',
    etiqueta: 'CSV Libro Diario',
    descripcion: 'Exporta todos los asientos y partidas en formato CSV plano.',
  },
  {
    valor: 'excel_multihoja',
    etiqueta: 'Excel Multi-hoja',
    descripcion: 'Libro diario, facturas, balance y PyG en hojas separadas.',
  },
  {
    valor: 'csv_facturas',
    etiqueta: 'CSV Facturas',
    descripcion: 'Listado de facturas emitidas y recibidas en formato CSV.',
  },
]

/**
 * Exportar Datos — seleccion de formato y rango de fechas.
 * Permite descargar datos contables en CSV o Excel.
 */
export function Exportar() {
  const [formato, setFormato] = useState<FormatoExportar>('csv_diario')
  const [desde, setDesde] = useState('')
  const [hasta, setHasta] = useState('')

  /** Placeholder: ejecutar exportacion */
  const exportar = () => {
    const formatoSeleccionado = FORMATOS.find((f) => f.valor === formato)
    const rangoTexto = desde && hasta
      ? `desde ${desde} hasta ${hasta}`
      : desde
        ? `desde ${desde}`
        : hasta
          ? `hasta ${hasta}`
          : 'todo el ejercicio'

    alert(
      `Se exportaria: ${formatoSeleccionado?.etiqueta}\n` +
      `Rango: ${rangoTexto}\n\n` +
      'Esta funcionalidad se conectara al backend en una version futura.'
    )
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-800 mb-6">Exportar Datos</h1>

      <div className="bg-white rounded-lg shadow p-6 space-y-8">
        {/* Seleccion de formato */}
        <div>
          <h2 className="text-lg font-semibold text-gray-700 mb-4">Formato de exportacion</h2>
          <div className="space-y-3">
            {FORMATOS.map((f) => (
              <label
                key={f.valor}
                className={`flex items-start gap-3 p-4 rounded-lg border cursor-pointer transition-colors ${
                  formato === f.valor
                    ? 'border-blue-300 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <input
                  type="radio"
                  name="formato"
                  value={f.valor}
                  checked={formato === f.valor}
                  onChange={() => setFormato(f.valor)}
                  className="mt-1 text-blue-600"
                />
                <div>
                  <span className="text-sm font-medium text-gray-800">{f.etiqueta}</span>
                  <p className="text-xs text-gray-500 mt-0.5">{f.descripcion}</p>
                </div>
              </label>
            ))}
          </div>
        </div>

        {/* Rango de fechas */}
        <div>
          <h2 className="text-lg font-semibold text-gray-700 mb-4">Rango de fechas</h2>
          <div className="flex items-center gap-4">
            <div className="flex-1">
              <label className="block text-sm text-gray-600 mb-1">Desde</label>
              <input
                type="date"
                value={desde}
                onChange={(e) => setDesde(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            <div className="flex-1">
              <label className="block text-sm text-gray-600 mb-1">Hasta</label>
              <input
                type="date"
                value={hasta}
                onChange={(e) => setHasta(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>
          <p className="text-xs text-gray-400 mt-2">
            Deja vacio para exportar todo el ejercicio
          </p>
        </div>

        {/* Boton exportar */}
        <div className="pt-2">
          <button
            onClick={exportar}
            className="px-6 py-2.5 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors"
          >
            Exportar
          </button>
        </div>
      </div>
    </div>
  )
}
