import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import type { PyG as PyGType } from '../types'

/** Formatea un numero con locale espanol (1.234,56 EUR) */
function formatearImporte(valor: number): string {
  return valor.toLocaleString('es-ES', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }) + ' EUR'
}

/** Tabla de detalle por subcuenta */
function TablaDetalle({ titulo, detalle, colorTotal }: {
  titulo: string
  detalle: Record<string, number>
  colorTotal: string
}) {
  const entradas = Object.entries(detalle).sort(([a], [b]) => a.localeCompare(b))
  const total = entradas.reduce((sum, [, v]) => sum + v, 0)

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="px-5 py-4 border-b border-gray-100">
        <h3 className="text-base font-semibold text-gray-700">{titulo}</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-gray-500 uppercase border-b">
              <th className="px-5 py-3">Subcuenta</th>
              <th className="px-5 py-3 text-right">Importe</th>
            </tr>
          </thead>
          <tbody>
            {entradas.length === 0 && (
              <tr>
                <td colSpan={2} className="px-5 py-4 text-gray-400 text-center">Sin datos</td>
              </tr>
            )}
            {entradas.map(([subcuenta, importe], i) => (
              <tr key={subcuenta} className={i % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                <td className="px-5 py-2 font-mono text-gray-700">{subcuenta}</td>
                <td className="px-5 py-2 text-right text-gray-800">
                  {formatearImporte(importe)}
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="border-t-2 border-gray-200 font-semibold">
              <td className="px-5 py-3">Total</td>
              <td className={`px-5 py-3 text-right ${colorTotal}`}>
                {formatearImporte(total)}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  )
}

/** Pagina de Perdidas y Ganancias */
export function PyG() {
  const { id } = useParams()
  const { fetchConAuth } = useApi()
  const empresaId = Number(id)

  const [datos, setDatos] = useState<PyGType | null>(null)
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const cargarDatos = async () => {
    setCargando(true)
    setError(null)
    try {
      const pyg = await fetchConAuth<PyGType>(`/api/contabilidad/${empresaId}/pyg`)
      setDatos(pyg)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al cargar PyG')
    } finally {
      setCargando(false)
    }
  }

  useEffect(() => {
    if (empresaId) {
      void cargarDatos()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [empresaId])

  if (cargando) {
    return (
      <div className="animate-pulse">
        <div className="h-8 bg-gray-200 rounded w-1/3 mb-6" />
        <div className="grid grid-cols-3 gap-4 mb-6">
          {[1, 2, 3].map((i) => <div key={i} className="bg-white rounded-lg shadow p-6 h-24" />)}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div>
        <Link to={`/empresa/${id}`} className="text-sm text-[var(--color-primary)] hover:underline mb-4 inline-block">
          Volver al resumen
        </Link>
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-700 mb-2">{error}</p>
          <button
            onClick={() => void cargarDatos()}
            className="px-4 py-2 text-sm bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
          >
            Reintentar
          </button>
        </div>
      </div>
    )
  }

  if (!datos) return null

  const esPositivo = datos.resultado >= 0

  return (
    <div>
      <Link to={`/empresa/${id}`} className="text-sm text-[var(--color-primary)] hover:underline mb-2 inline-block">
        Volver al resumen
      </Link>
      <h1 className="text-2xl font-bold text-gray-800 mb-6">Perdidas y Ganancias</h1>

      {/* Resumen */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-white rounded-lg shadow border-l-4 border-green-500 p-4">
          <p className="text-sm text-gray-500">Ingresos</p>
          <p className="text-xl font-bold text-green-700">{formatearImporte(datos.ingresos)}</p>
        </div>
        <div className="bg-white rounded-lg shadow border-l-4 border-red-500 p-4">
          <p className="text-sm text-gray-500">Gastos</p>
          <p className="text-xl font-bold text-red-700">{formatearImporte(datos.gastos)}</p>
        </div>
        <div className={`bg-white rounded-lg shadow border-l-4 p-4 ${esPositivo ? 'border-blue-500' : 'border-orange-500'}`}>
          <p className="text-sm text-gray-500">Resultado</p>
          <p className={`text-xl font-bold ${esPositivo ? 'text-blue-700' : 'text-orange-700'}`}>
            {formatearImporte(datos.resultado)}
          </p>
        </div>
      </div>

      {/* Detalle en dos columnas */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <TablaDetalle
          titulo="Gastos (grupo 6)"
          detalle={datos.detalle_gastos}
          colorTotal="text-red-700"
        />
        <TablaDetalle
          titulo="Ingresos (grupo 7)"
          detalle={datos.detalle_ingresos}
          colorTotal="text-green-700"
        />
      </div>
    </div>
  )
}
