import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import type { Documento } from '../types'

/**
 * Bandeja de Entrada — muestra documentos pendientes de procesar.
 * Los PDFs en inbox seran procesados por el pipeline.
 */
export function Inbox() {
  const { id } = useParams()
  const empresaId = Number(id)
  const { fetchConAuth } = useApi()

  const [documentos, setDocumentos] = useState<Documento[]>([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const cargarDocumentos = useCallback(async () => {
    try {
      setCargando(true)
      setError(null)
      const datos = await fetchConAuth<Documento[]>(
        `/api/documentos/${empresaId}?estado=pendiente`
      )
      setDocumentos(datos)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al cargar documentos')
    } finally {
      setCargando(false)
    }
  }, [empresaId, fetchConAuth])

  useEffect(() => {
    cargarDocumentos()
  }, [cargarDocumentos])

  /** Extrae nombre de archivo de la ruta completa */
  const nombreArchivo = (ruta: string | null): string => {
    if (!ruta) return '(sin nombre)'
    const partes = ruta.replace(/\\/g, '/').split('/')
    return partes[partes.length - 1] ?? ruta
  }

  /** Formatea fecha para mostrar */
  const formatearFecha = (fecha: string | null): string => {
    if (!fecha) return '-'
    try {
      return new Date(fecha).toLocaleDateString('es-ES', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
      })
    } catch {
      return fecha
    }
  }

  /** Placeholder: procesar todos los documentos pendientes */
  const procesarTodo = () => {
    alert(
      `Se procesarian ${documentos.length} documentos pendientes.\n` +
      'Esta funcionalidad se conectara al pipeline en una version futura.'
    )
  }

  if (cargando) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Cargando documentos pendientes...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-red-800 mb-2">Error</h2>
        <p className="text-red-600">{error}</p>
        <button
          onClick={cargarDocumentos}
          className="mt-4 px-4 py-2 bg-red-100 text-red-700 rounded-md hover:bg-red-200 transition-colors"
        >
          Reintentar
        </button>
      </div>
    )
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Bandeja de Entrada</h1>
          <p className="text-sm text-gray-500 mt-1">
            {documentos.length} documento{documentos.length !== 1 ? 's' : ''} pendiente{documentos.length !== 1 ? 's' : ''}
          </p>
        </div>
        {documentos.length > 0 && (
          <button
            onClick={procesarTodo}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
          >
            Procesar todo
          </button>
        )}
      </div>

      {documentos.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <p className="text-gray-400 text-lg">No hay documentos pendientes</p>
          <p className="text-gray-300 text-sm mt-2">
            Los nuevos PDFs apareceran aqui automaticamente
          </p>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Archivo
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Tipo
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Confianza
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  OCR Tier
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Fecha proceso
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {documentos.map((doc) => (
                <tr key={doc.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4 text-sm text-gray-800 font-medium">
                    {nombreArchivo(doc.ruta_pdf)}
                  </td>
                  <td className="px-6 py-4">
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
                      {doc.tipo_doc}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600">
                    {doc.confianza !== null ? `${doc.confianza}%` : '-'}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600">
                    {doc.ocr_tier !== null ? `Tier ${doc.ocr_tier}` : '-'}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {formatearFecha(doc.fecha_proceso)}
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
