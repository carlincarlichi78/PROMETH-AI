import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import type { ActivoFijo } from '../types'

/** Formatea un numero con locale espanol */
function formatearImporte(valor: number): string {
  return valor.toLocaleString('es-ES', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }) + ' EUR'
}

/** Formatea fecha ISO a DD/MM/YYYY */
function formatearFecha(fecha: string): string {
  const partes = fecha.split('-')
  if (partes.length === 3) {
    return `${partes[2]}/${partes[1]}/${partes[0]}`
  }
  return fecha
}

/** Barra de progreso para porcentaje de amortizacion */
function BarraAmortizacion({ porcentaje }: { porcentaje: number }) {
  const porcentajeAcotado = Math.min(100, Math.max(0, porcentaje))
  const color = porcentajeAcotado >= 90
    ? 'bg-green-500'
    : porcentajeAcotado >= 50
      ? 'bg-blue-500'
      : 'bg-amber-500'

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${color}`}
          style={{ width: `${porcentajeAcotado}%` }}
        />
      </div>
      <span className="text-xs text-gray-600 w-12 text-right font-mono">
        {porcentajeAcotado.toFixed(1)}%
      </span>
    </div>
  )
}

/** Pagina de Activos Fijos */
export function Activos() {
  const { id } = useParams()
  const { fetchConAuth } = useApi()
  const empresaId = Number(id)

  const [activos, setActivos] = useState<ActivoFijo[]>([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const cargarDatos = async () => {
    setCargando(true)
    setError(null)
    try {
      const datos = await fetchConAuth<ActivoFijo[]>(`/api/contabilidad/${empresaId}/activos`)
      setActivos(datos)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al cargar activos')
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
        <div className="h-8 bg-gray-200 rounded w-1/4 mb-6" />
        <div className="bg-white rounded-lg shadow">
          {[1, 2, 3].map((i) => (
            <div key={i} className="px-5 py-4 border-b border-gray-100">
              <div className="h-4 bg-gray-200 rounded w-3/4" />
            </div>
          ))}
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

  // Totales
  const totalValor = activos.reduce((s, a) => s + a.valor_adquisicion, 0)
  const totalAmortizado = activos.reduce((s, a) => s + a.amortizacion_acumulada, 0)
  const totalNeto = totalValor - totalAmortizado

  return (
    <div>
      <Link to={`/empresa/${id}`} className="text-sm text-[var(--color-primary)] hover:underline mb-2 inline-block">
        Volver al resumen
      </Link>
      <h1 className="text-2xl font-bold text-gray-800 mb-6">Activos Fijos</h1>

      {/* Resumen */}
      {activos.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className="bg-white rounded-lg shadow border-l-4 border-blue-500 p-4">
            <p className="text-sm text-gray-500">Valor total adquisicion</p>
            <p className="text-xl font-bold text-blue-700">{formatearImporte(totalValor)}</p>
          </div>
          <div className="bg-white rounded-lg shadow border-l-4 border-amber-500 p-4">
            <p className="text-sm text-gray-500">Amortizacion acumulada</p>
            <p className="text-xl font-bold text-amber-700">{formatearImporte(totalAmortizado)}</p>
          </div>
          <div className="bg-white rounded-lg shadow border-l-4 border-green-500 p-4">
            <p className="text-sm text-gray-500">Valor neto contable</p>
            <p className="text-xl font-bold text-green-700">{formatearImporte(totalNeto)}</p>
          </div>
        </div>
      )}

      {/* Tabla */}
      {activos.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-6 text-center">
          <p className="text-gray-500">No se encontraron activos fijos.</p>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-gray-500 uppercase border-b bg-gray-50">
                <th className="px-5 py-3">Descripcion</th>
                <th className="px-5 py-3">Tipo</th>
                <th className="px-5 py-3">Fecha adquisicion</th>
                <th className="px-5 py-3 text-right">Valor adquisicion</th>
                <th className="px-5 py-3 text-right">Amortizacion acum.</th>
                <th className="px-5 py-3 w-40">% Amortizado</th>
              </tr>
            </thead>
            <tbody>
              {activos.map((activo, i) => {
                const porcentaje = activo.valor_adquisicion > 0
                  ? (activo.amortizacion_acumulada / activo.valor_adquisicion) * 100
                  : 0

                return (
                  <tr key={activo.id} className={i % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                    <td className="px-5 py-3 text-gray-800 font-medium max-w-xs truncate">
                      {activo.descripcion}
                    </td>
                    <td className="px-5 py-3 text-gray-600">
                      {activo.tipo_bien ?? '-'}
                    </td>
                    <td className="px-5 py-3 text-gray-700 whitespace-nowrap">
                      {formatearFecha(activo.fecha_adquisicion)}
                    </td>
                    <td className="px-5 py-3 text-right font-mono text-gray-800">
                      {formatearImporte(activo.valor_adquisicion)}
                    </td>
                    <td className="px-5 py-3 text-right font-mono text-gray-800">
                      {formatearImporte(activo.amortizacion_acumulada)}
                    </td>
                    <td className="px-5 py-3">
                      <BarraAmortizacion porcentaje={porcentaje} />
                    </td>
                  </tr>
                )
              })}
            </tbody>
            <tfoot>
              <tr className="border-t-2 border-gray-200 font-semibold bg-gray-50">
                <td className="px-5 py-3" colSpan={3}>Total</td>
                <td className="px-5 py-3 text-right font-mono">{formatearImporte(totalValor)}</td>
                <td className="px-5 py-3 text-right font-mono">{formatearImporte(totalAmortizado)}</td>
                <td className="px-5 py-3">
                  <BarraAmortizacion porcentaje={totalValor > 0 ? (totalAmortizado / totalValor) * 100 : 0} />
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      )}

      <p className="text-xs text-gray-400 mt-3">
        {activos.length} activo{activos.length !== 1 ? 's' : ''} fijo{activos.length !== 1 ? 's' : ''}
      </p>
    </div>
  )
}
