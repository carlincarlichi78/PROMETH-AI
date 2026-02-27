import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import type { Factura } from '../types'

/** Formatea un numero con locale espanol */
function formatearImporte(valor: number | null): string {
  if (valor === null) return '-'
  return valor.toLocaleString('es-ES', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }) + ' EUR'
}

/** Formatea fecha ISO a DD/MM/YYYY */
function formatearFecha(fecha: string | null): string {
  if (!fecha) return '-'
  const partes = fecha.split('-')
  if (partes.length === 3) {
    return `${partes[2]}/${partes[1]}/${partes[0]}`
  }
  return fecha
}

/** Insignia de estado pagada/pendiente */
function InsigniaPagada({ pagada }: { pagada: boolean }) {
  return (
    <span className={`inline-block px-2 py-0.5 text-xs font-medium rounded-full ${
      pagada
        ? 'bg-green-100 text-green-800'
        : 'bg-amber-100 text-amber-800'
    }`}>
      {pagada ? 'Pagada' : 'Pendiente'}
    </span>
  )
}

/** Insignia de tipo factura */
function InsigniaTipo({ tipo }: { tipo: string }) {
  const esEmitida = tipo === 'emitida' || tipo === 'cliente'
  return (
    <span className={`inline-block px-2 py-0.5 text-xs font-medium rounded-full ${
      esEmitida
        ? 'bg-blue-100 text-blue-800'
        : 'bg-purple-100 text-purple-800'
    }`}>
      {esEmitida ? 'Emitida' : 'Recibida'}
    </span>
  )
}

type FiltroTipo = 'todos' | 'emitida' | 'recibida'
type FiltroPagada = 'todos' | 'si' | 'no'

/** Pagina de Facturas con filtros */
export function Facturas() {
  const { id } = useParams()
  const { fetchConAuth } = useApi()
  const empresaId = Number(id)

  const [facturas, setFacturas] = useState<Factura[]>([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filtroTipo, setFiltroTipo] = useState<FiltroTipo>('todos')
  const [filtroPagada, setFiltroPagada] = useState<FiltroPagada>('todos')

  const cargarDatos = async () => {
    setCargando(true)
    setError(null)
    try {
      let url = `/api/contabilidad/${empresaId}/facturas`
      const params: string[] = []
      if (filtroTipo !== 'todos') {
        params.push(`tipo=${filtroTipo}`)
      }
      if (filtroPagada !== 'todos') {
        params.push(`pagada=${filtroPagada === 'si' ? 'true' : 'false'}`)
      }
      if (params.length > 0) {
        url += `?${params.join('&')}`
      }
      const datos = await fetchConAuth<Factura[]>(url)
      setFacturas(datos)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al cargar facturas')
    } finally {
      setCargando(false)
    }
  }

  useEffect(() => {
    if (empresaId) {
      void cargarDatos()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [empresaId, filtroTipo, filtroPagada])

  if (error && !cargando) {
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

  return (
    <div>
      <Link to={`/empresa/${id}`} className="text-sm text-[var(--color-primary)] hover:underline mb-2 inline-block">
        Volver al resumen
      </Link>
      <h1 className="text-2xl font-bold text-gray-800 mb-6">Facturas</h1>

      {/* Filtros */}
      <div className="bg-white rounded-lg shadow p-4 mb-4 flex flex-wrap gap-4 items-center">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Tipo</label>
          <select
            value={filtroTipo}
            onChange={(e) => setFiltroTipo(e.target.value as FiltroTipo)}
            className="border border-gray-300 rounded px-3 py-1.5 text-sm bg-white"
          >
            <option value="todos">Todos</option>
            <option value="emitida">Emitidas</option>
            <option value="recibida">Recibidas</option>
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Estado pago</label>
          <select
            value={filtroPagada}
            onChange={(e) => setFiltroPagada(e.target.value as FiltroPagada)}
            className="border border-gray-300 rounded px-3 py-1.5 text-sm bg-white"
          >
            <option value="todos">Todos</option>
            <option value="si">Pagadas</option>
            <option value="no">Pendientes</option>
          </select>
        </div>
        <div className="ml-auto text-sm text-gray-500">
          {!cargando && `${facturas.length} factura${facturas.length !== 1 ? 's' : ''}`}
        </div>
      </div>

      {/* Tabla */}
      {cargando ? (
        <div className="bg-white rounded-lg shadow animate-pulse">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="px-5 py-4 border-b border-gray-100">
              <div className="h-4 bg-gray-200 rounded w-3/4" />
            </div>
          ))}
        </div>
      ) : facturas.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-6 text-center">
          <p className="text-gray-500">No se encontraron facturas con los filtros seleccionados.</p>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-gray-500 uppercase border-b bg-gray-50">
                <th className="px-5 py-3">Fecha</th>
                <th className="px-5 py-3">Numero</th>
                <th className="px-5 py-3">Tipo</th>
                <th className="px-5 py-3">Emisor</th>
                <th className="px-5 py-3 text-right">Base</th>
                <th className="px-5 py-3 text-right">IVA</th>
                <th className="px-5 py-3 text-right">Total</th>
                <th className="px-5 py-3 text-center">Estado</th>
              </tr>
            </thead>
            <tbody>
              {facturas.map((factura, i) => (
                <tr key={factura.id} className={i % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                  <td className="px-5 py-3 text-gray-700 whitespace-nowrap">
                    {formatearFecha(factura.fecha_factura)}
                  </td>
                  <td className="px-5 py-3 font-mono text-gray-700">
                    {factura.numero_factura ?? '-'}
                  </td>
                  <td className="px-5 py-3">
                    <InsigniaTipo tipo={factura.tipo} />
                  </td>
                  <td className="px-5 py-3 text-gray-800 max-w-xs truncate">
                    {factura.nombre_emisor ?? factura.cif_emisor ?? '-'}
                  </td>
                  <td className="px-5 py-3 text-right font-mono text-gray-800">
                    {formatearImporte(factura.base_imponible)}
                  </td>
                  <td className="px-5 py-3 text-right font-mono text-gray-800">
                    {formatearImporte(factura.iva_importe)}
                  </td>
                  <td className="px-5 py-3 text-right font-mono font-semibold text-gray-900">
                    {formatearImporte(factura.total)}
                  </td>
                  <td className="px-5 py-3 text-center">
                    <InsigniaPagada pagada={factura.pagada} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
