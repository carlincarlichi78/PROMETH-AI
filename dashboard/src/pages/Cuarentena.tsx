import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import type { Cuarentena as CuarentenaItem } from '../types'

/**
 * Cuarentena — documentos que requieren intervencion manual.
 * Muestra preguntas pendientes con opciones y campo de respuesta libre.
 */
export function Cuarentena() {
  const { id } = useParams()
  const empresaId = Number(id)
  const { fetchConAuth } = useApi()

  const [items, setItems] = useState<CuarentenaItem[]>([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [respuestas, setRespuestas] = useState<Record<number, string>>({})
  const [enviando, setEnviando] = useState<number | null>(null)
  const [mensajeExito, setMensajeExito] = useState<string | null>(null)

  const cargarCuarentena = useCallback(async () => {
    try {
      setCargando(true)
      setError(null)
      const datos = await fetchConAuth<CuarentenaItem[]>(
        `/api/documentos/${empresaId}/cuarentena`
      )
      // Solo mostrar items no resueltos
      setItems(datos.filter((item) => !item.resuelta))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al cargar cuarentena')
    } finally {
      setCargando(false)
    }
  }, [empresaId, fetchConAuth])

  useEffect(() => {
    cargarCuarentena()
  }, [cargarCuarentena])

  /** Actualiza la respuesta seleccionada/escrita para un item */
  const actualizarRespuesta = (itemId: number, valor: string) => {
    setRespuestas((prev) => ({ ...prev, [itemId]: valor }))
  }

  /** Envia la resolucion al backend */
  const resolverItem = async (itemId: number) => {
    const respuesta = respuestas[itemId]
    if (!respuesta?.trim()) return

    try {
      setEnviando(itemId)
      await fetchConAuth<CuarentenaItem>(
        `/api/documentos/${empresaId}/cuarentena/${itemId}/resolver`,
        {
          method: 'POST',
          body: { respuesta: respuesta.trim() },
        }
      )

      // Eliminar del listado local
      setItems((prev) => prev.filter((item) => item.id !== itemId))
      setRespuestas((prev) => {
        const copia = { ...prev }
        delete copia[itemId]
        return copia
      })
      setMensajeExito('Cuarentena resuelta correctamente')
      setTimeout(() => setMensajeExito(null), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al resolver cuarentena')
    } finally {
      setEnviando(null)
    }
  }

  /** Color del badge segun tipo de pregunta */
  const colorBadge = (tipo: string): string => {
    switch (tipo) {
      case 'entidad_desconocida':
        return 'bg-orange-100 text-orange-700'
      case 'campo_ambiguo':
        return 'bg-yellow-100 text-yellow-700'
      case 'duplicado':
        return 'bg-purple-100 text-purple-700'
      case 'importe_anomalo':
        return 'bg-red-100 text-red-700'
      default:
        return 'bg-gray-100 text-gray-700'
    }
  }

  if (cargando) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Cargando cuarentena...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-red-800 mb-2">Error</h2>
        <p className="text-red-600">{error}</p>
        <button
          onClick={cargarCuarentena}
          className="mt-4 px-4 py-2 bg-red-100 text-red-700 rounded-md hover:bg-red-200 transition-colors"
        >
          Reintentar
        </button>
      </div>
    )
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Cuarentena</h1>
        <p className="text-sm text-gray-500 mt-1">
          {items.length} item{items.length !== 1 ? 's' : ''} pendiente{items.length !== 1 ? 's' : ''} de resolucion
        </p>
      </div>

      {/* Mensaje de exito */}
      {mensajeExito && (
        <div className="mb-4 bg-green-50 border border-green-200 rounded-lg px-4 py-3 text-green-700 text-sm">
          {mensajeExito}
        </div>
      )}

      {items.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <p className="text-gray-400 text-lg">No hay documentos en cuarentena</p>
          <p className="text-gray-300 text-sm mt-2">
            Los documentos que requieran intervencion apareceran aqui
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {items.map((item) => (
            <div key={item.id} className="bg-white rounded-lg shadow p-6">
              {/* Cabecera */}
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <span
                    className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colorBadge(item.tipo_pregunta)}`}
                  >
                    {item.tipo_pregunta.replace(/_/g, ' ')}
                  </span>
                  <span className="text-xs text-gray-400">
                    Doc #{item.documento_id}
                  </span>
                </div>
              </div>

              {/* Pregunta */}
              <p className="text-gray-800 mb-4">{item.pregunta}</p>

              {/* Opciones (si hay) como radio buttons */}
              {item.opciones && item.opciones.length > 0 && (
                <div className="mb-4 space-y-2">
                  <p className="text-sm font-medium text-gray-600">Opciones sugeridas:</p>
                  {item.opciones.map((opcion, idx) => {
                    const opcionStr = typeof opcion === 'string' ? opcion : String(opcion)
                    return (
                      <label
                        key={idx}
                        className="flex items-center gap-2 cursor-pointer text-sm text-gray-700 hover:text-gray-900"
                      >
                        <input
                          type="radio"
                          name={`opcion-${item.id}`}
                          value={opcionStr}
                          checked={respuestas[item.id] === opcionStr}
                          onChange={() => actualizarRespuesta(item.id, opcionStr)}
                          className="text-blue-600"
                        />
                        {opcionStr}
                      </label>
                    )
                  })}
                </div>
              )}

              {/* Campo de respuesta libre */}
              <div className="flex gap-3">
                <input
                  type="text"
                  placeholder="Escribe una respuesta..."
                  value={respuestas[item.id] ?? ''}
                  onChange={(e) => actualizarRespuesta(item.id, e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') resolverItem(item.id)
                  }}
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
                <button
                  onClick={() => resolverItem(item.id)}
                  disabled={!respuestas[item.id]?.trim() || enviando === item.id}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
                >
                  {enviando === item.id ? 'Enviando...' : 'Resolver'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
