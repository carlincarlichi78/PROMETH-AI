import { useState } from 'react'
import { useParams } from 'react-router-dom'

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
  const { empresaId } = useParams<{ empresaId: string }>()

  const [formato, setFormato] = useState<FormatoExportar>('csv_diario')
  const [desde, setDesde] = useState('')
  const [hasta, setHasta] = useState('')
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState<string | null>(null)

  /** Descarga el archivo exportado */
  const descargar = async () => {
    setCargando(true)
    setError(null)
    try {
      const token = localStorage.getItem('sfce_token') ?? ''
      const params = new URLSearchParams({ tipo: formato })
      const esExcel = formato === 'excel_multihoja'
      params.set('formato', esExcel ? 'excel' : 'csv')
      if (desde) params.set('desde', desde)
      if (hasta) params.set('hasta', hasta)

      const resp = await fetch(`/api/contabilidad/${empresaId ?? ''}/exportar?${params.toString()}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!resp.ok) {
        const detalle = await resp.json().catch(() => ({ detail: 'Error al exportar' }))
        throw new Error((detalle as { detail?: string }).detail ?? `Error HTTP ${resp.status}`)
      }
      const blob = await resp.blob()
      const ext = esExcel ? 'xlsx' : 'csv'
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${formato}_${empresaId ?? 'empresa'}.${ext}`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error al exportar')
    } finally {
      setCargando(false)
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-800 mb-6">Exportar Datos</h1>

      {/* Error */}
      {error && (
        <div className="mb-4 bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-red-700 text-sm">
          {error}
        </div>
      )}

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
            onClick={() => void descargar()}
            disabled={cargando}
            className="px-6 py-2.5 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:bg-blue-300 disabled:cursor-not-allowed transition-colors"
          >
            {cargando ? 'Exportando...' : 'Exportar'}
          </button>
        </div>
      </div>
    </div>
  )
}
