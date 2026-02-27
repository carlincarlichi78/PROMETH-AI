import { useState } from 'react'
import { useParams } from 'react-router-dom'

/** Pasos del wizard de importacion */
type PasoImportar = 1 | 2 | 3

/** Fila de asiento en la vista previa */
interface FilaPreview {
  fecha?: string
  concepto?: string
  subcuenta?: string
  debe?: number
  haber?: number
  [key: string]: unknown
}

/**
 * Importar Libro Diario — wizard de 3 pasos.
 * Paso 1: Subir archivo (drag & drop)
 * Paso 2: Vista previa de datos
 * Paso 3: Confirmacion e importacion
 */
export function Importar() {
  const { empresaId } = useParams<{ empresaId: string }>()

  const [paso, setPaso] = useState<PasoImportar>(1)
  const [archivoNombre, setArchivoNombre] = useState<string | null>(null)
  const [arrastrando, setArrastrando] = useState(false)
  const [importarId, setImportarId] = useState<string | null>(null)
  const [preview, setPreview] = useState<FilaPreview[]>([])
  const [error, setError] = useState<string | null>(null)
  const [cargando, setCargando] = useState(false)
  const [importado, setImportado] = useState(false)

  /** Nombres de los pasos */
  const nombresPasos = ['Subir archivo', 'Vista previa', 'Confirmar']

  /** Sube el archivo y obtiene la vista previa */
  const manejarArchivo = async (file: File) => {
    setArchivoNombre(file.name)
    setCargando(true)
    setError(null)
    try {
      const token = localStorage.getItem('sfce_token') ?? ''
      const fd = new FormData()
      fd.append('archivo', file)
      const resp = await fetch(`/api/contabilidad/${empresaId ?? ''}/importar`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: fd,
      })
      if (!resp.ok) {
        const detalle = await resp.json().catch(() => ({ detail: 'Error al procesar archivo' }))
        throw new Error((detalle as { detail?: string }).detail ?? `Error HTTP ${resp.status}`)
      }
      const datos = (await resp.json()) as { importar_id: string; total: number; asientos_preview: FilaPreview[] }
      setImportarId(datos.importar_id)
      setPreview(datos.asientos_preview)
      setPaso(2)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error al procesar archivo')
    } finally {
      setCargando(false)
    }
  }

  /** Manejo de drag and drop */
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setArrastrando(true)
  }

  const handleDragLeave = () => {
    setArrastrando(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setArrastrando(false)
    const archivos = e.dataTransfer.files
    if (archivos.length > 0 && archivos[0]) {
      void manejarArchivo(archivos[0])
    }
  }

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const archivos = e.target.files
    if (archivos && archivos.length > 0 && archivos[0]) {
      void manejarArchivo(archivos[0])
    }
  }

  /** Confirmar importacion via API */
  const confirmarImportacion = async () => {
    if (!importarId) return
    setCargando(true)
    setError(null)
    try {
      const token = localStorage.getItem('sfce_token') ?? ''
      const resp = await fetch(`/api/contabilidad/${empresaId ?? ''}/importar/${importarId}/confirmar`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!resp.ok) {
        const detalle = await resp.json().catch(() => ({ detail: 'Error al confirmar importacion' }))
        throw new Error((detalle as { detail?: string }).detail ?? `Error HTTP ${resp.status}`)
      }
      setImportado(true)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error al confirmar importacion')
    } finally {
      setCargando(false)
    }
  }

  /** Formatear numero como moneda */
  const formatearImporte = (valor: number): string => {
    return valor.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  }

  if (importado) {
    return (
      <div>
        <h1 className="text-2xl font-bold text-gray-800 mb-6">Importar Libro Diario</h1>
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <div className="text-green-500 text-5xl mb-4">✓</div>
          <h2 className="text-xl font-semibold text-gray-800 mb-2">Importacion completada</h2>
          <p className="text-gray-500 mb-6">
            El archivo <span className="font-medium">{archivoNombre}</span> se ha importado correctamente.
          </p>
          <button
            onClick={() => {
              setImportado(false)
              setPaso(1)
              setArchivoNombre(null)
              setImportarId(null)
              setPreview([])
            }}
            className="px-4 py-2 text-sm text-white bg-blue-600 rounded-md hover:bg-blue-700 transition-colors"
          >
            Importar otro archivo
          </button>
        </div>
      </div>
    )
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-800 mb-6">Importar Libro Diario</h1>

      {/* Indicador de pasos */}
      <div className="flex items-center mb-8">
        {nombresPasos.map((nombre, idx) => {
          const numeroPaso = (idx + 1) as PasoImportar
          const esActual = paso === numeroPaso
          const completado = paso > numeroPaso

          return (
            <div key={nombre} className="flex items-center">
              {idx > 0 && (
                <div
                  className={`w-16 h-0.5 ${
                    completado ? 'bg-blue-600' : 'bg-gray-200'
                  }`}
                />
              )}
              <div className="flex items-center gap-2">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                    esActual
                      ? 'bg-blue-600 text-white'
                      : completado
                        ? 'bg-blue-100 text-blue-600'
                        : 'bg-gray-100 text-gray-400'
                  }`}
                >
                  {completado ? '\u2713' : numeroPaso}
                </div>
                <span
                  className={`text-sm ${
                    esActual ? 'text-gray-800 font-medium' : 'text-gray-400'
                  }`}
                >
                  {nombre}
                </span>
              </div>
            </div>
          )
        })}
      </div>

      {/* Error */}
      {error && (
        <div className="mb-4 bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* Contenido del paso actual */}
      <div className="bg-white rounded-lg shadow p-6">
        {/* Paso 1: Subir archivo */}
        {paso === 1 && (
          <div>
            <h2 className="text-lg font-semibold text-gray-700 mb-4">
              Seleccionar archivo
            </h2>
            <p className="text-sm text-gray-500 mb-6">
              Arrastra un archivo CSV o Excel con el libro diario, o haz clic para seleccionar.
            </p>

            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              className={`border-2 border-dashed rounded-lg p-12 text-center transition-colors cursor-pointer ${
                arrastrando
                  ? 'border-blue-400 bg-blue-50'
                  : archivoNombre
                    ? 'border-green-300 bg-green-50'
                    : 'border-gray-300 hover:border-gray-400'
              }`}
            >
              {cargando ? (
                <div>
                  <p className="text-gray-500 animate-pulse">Procesando archivo...</p>
                </div>
              ) : archivoNombre ? (
                <div>
                  <p className="text-green-700 font-medium">{archivoNombre}</p>
                  <p className="text-sm text-green-600 mt-1">Archivo seleccionado</p>
                  <button
                    onClick={() => { setArchivoNombre(null); setError(null) }}
                    className="mt-3 text-sm text-gray-500 hover:text-gray-700 underline"
                  >
                    Cambiar archivo
                  </button>
                </div>
              ) : (
                <div>
                  <p className="text-gray-500 mb-2">Arrastra tu archivo aqui</p>
                  <p className="text-gray-400 text-sm mb-4">o</p>
                  <label className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 cursor-pointer transition-colors">
                    Seleccionar archivo
                    <input
                      type="file"
                      accept=".csv,.xlsx,.xls"
                      onChange={handleFileInput}
                      className="hidden"
                    />
                  </label>
                  <p className="text-xs text-gray-400 mt-3">
                    Formatos aceptados: CSV, XLSX, XLS
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Paso 2: Vista previa */}
        {paso === 2 && (
          <div>
            <h2 className="text-lg font-semibold text-gray-700 mb-4">
              Vista previa de datos
            </h2>
            <p className="text-sm text-gray-500 mb-4">
              Revisa los primeros registros antes de importar. Archivo: <span className="font-medium">{archivoNombre}</span>
            </p>

            {preview.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 border-b border-gray-200">
                    <tr>
                      <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase">Fecha</th>
                      <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase">Concepto</th>
                      <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase">Subcuenta</th>
                      <th className="px-4 py-2 text-right text-xs font-semibold text-gray-500 uppercase">Debe</th>
                      <th className="px-4 py-2 text-right text-xs font-semibold text-gray-500 uppercase">Haber</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {preview.map((fila, idx) => (
                      <tr key={idx} className="hover:bg-gray-50">
                        <td className="px-4 py-2 text-gray-700">{String(fila.fecha ?? '')}</td>
                        <td className="px-4 py-2 text-gray-700">{String(fila.concepto ?? '')}</td>
                        <td className="px-4 py-2 font-mono text-gray-600">{String(fila.subcuenta ?? '')}</td>
                        <td className="px-4 py-2 text-right text-gray-700">
                          {Number(fila.debe ?? 0) > 0 ? formatearImporte(Number(fila.debe)) : ''}
                        </td>
                        <td className="px-4 py-2 text-right text-gray-700">
                          {Number(fila.haber ?? 0) > 0 ? formatearImporte(Number(fila.haber)) : ''}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-sm text-gray-400 italic">Sin datos de vista previa disponibles</p>
            )}

            <p className="text-xs text-gray-400 mt-4">
              Mostrando {preview.length} registros de vista previa
            </p>
          </div>
        )}

        {/* Paso 3: Confirmacion */}
        {paso === 3 && (
          <div className="text-center py-6">
            <h2 className="text-lg font-semibold text-gray-700 mb-4">
              Confirmar importacion
            </h2>
            <div className="bg-gray-50 rounded-lg p-6 mb-6 inline-block text-left">
              <dl className="space-y-2 text-sm">
                <div className="flex gap-4">
                  <dt className="text-gray-500 w-24">Archivo:</dt>
                  <dd className="text-gray-800 font-medium">{archivoNombre}</dd>
                </div>
                <div className="flex gap-4">
                  <dt className="text-gray-500 w-24">Registros:</dt>
                  <dd className="text-gray-800 font-medium">{preview.length} partidas en vista previa</dd>
                </div>
                <div className="flex gap-4">
                  <dt className="text-gray-500 w-24">Formato:</dt>
                  <dd className="text-gray-800 font-medium">CSV / Excel</dd>
                </div>
              </dl>
            </div>

            <p className="text-sm text-gray-500 mb-6">
              Los asientos se crearan en la base de datos local. Esta accion se puede revertir.
            </p>

            <button
              onClick={() => void confirmarImportacion()}
              disabled={cargando}
              className="px-6 py-2.5 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:bg-blue-300 disabled:cursor-not-allowed transition-colors"
            >
              {cargando ? 'Importando...' : 'Importar'}
            </button>
          </div>
        )}
      </div>

      {/* Botones de navegacion */}
      <div className="flex justify-between mt-6">
        <button
          onClick={() => setPaso((prev) => (prev > 1 ? ((prev - 1) as PasoImportar) : prev))}
          disabled={paso === 1 || cargando}
          className="px-4 py-2 text-sm text-gray-600 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Anterior
        </button>
        <button
          onClick={() => setPaso((prev) => (prev < 3 ? ((prev + 1) as PasoImportar) : prev))}
          disabled={paso === 3 || (paso === 1 && !archivoNombre) || cargando}
          className="px-4 py-2 text-sm text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Siguiente
        </button>
      </div>
    </div>
  )
}
