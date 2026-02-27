import { useState } from 'react'

/** Pasos del wizard de importacion */
type PasoImportar = 1 | 2 | 3

/** Datos de ejemplo para la vista previa */
const DATOS_PREVIEW = [
  { fecha: '15/01/2025', concepto: 'Factura proveedor ABC', subcuenta: '6000000001', debe: 1200.0, haber: 0 },
  { fecha: '15/01/2025', concepto: 'Factura proveedor ABC', subcuenta: '4720000000', debe: 252.0, haber: 0 },
  { fecha: '15/01/2025', concepto: 'Factura proveedor ABC', subcuenta: '4000000001', debe: 0, haber: 1452.0 },
  { fecha: '20/01/2025', concepto: 'Venta cliente XYZ', subcuenta: '4300000001', debe: 2420.0, haber: 0 },
  { fecha: '20/01/2025', concepto: 'Venta cliente XYZ', subcuenta: '7000000001', debe: 0, haber: 2000.0 },
  { fecha: '20/01/2025', concepto: 'Venta cliente XYZ', subcuenta: '4770000000', debe: 0, haber: 420.0 },
]

/**
 * Importar Libro Diario — wizard de 3 pasos.
 * Paso 1: Subir archivo (drag & drop)
 * Paso 2: Vista previa de datos
 * Paso 3: Confirmacion e importacion
 */
export function Importar() {
  const [paso, setPaso] = useState<PasoImportar>(1)
  const [archivoNombre, setArchivoNombre] = useState<string | null>(null)
  const [arrastrando, setArrastrando] = useState(false)

  /** Nombres de los pasos */
  const nombresPasos = ['Subir archivo', 'Vista previa', 'Confirmar']

  /** Simula seleccion de archivo */
  const simularSeleccion = (nombre: string) => {
    setArchivoNombre(nombre)
  }

  /** Manejo de drag and drop (solo UI) */
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
      simularSeleccion(archivos[0].name)
    }
  }

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const archivos = e.target.files
    if (archivos && archivos.length > 0 && archivos[0]) {
      simularSeleccion(archivos[0].name)
    }
  }

  /** Confirmar importacion (placeholder) */
  const confirmarImportacion = () => {
    alert(
      `Se importaria el archivo "${archivoNombre}".\n` +
      'Esta funcionalidad se conectara al backend en una version futura.'
    )
  }

  /** Formatear numero como moneda */
  const formatearImporte = (valor: number): string => {
    return valor.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
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
              {archivoNombre ? (
                <div>
                  <p className="text-green-700 font-medium">{archivoNombre}</p>
                  <p className="text-sm text-green-600 mt-1">Archivo seleccionado</p>
                  <button
                    onClick={() => setArchivoNombre(null)}
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
                  {DATOS_PREVIEW.map((fila, idx) => (
                    <tr key={idx} className="hover:bg-gray-50">
                      <td className="px-4 py-2 text-gray-700">{fila.fecha}</td>
                      <td className="px-4 py-2 text-gray-700">{fila.concepto}</td>
                      <td className="px-4 py-2 font-mono text-gray-600">{fila.subcuenta}</td>
                      <td className="px-4 py-2 text-right text-gray-700">
                        {fila.debe > 0 ? formatearImporte(fila.debe) : ''}
                      </td>
                      <td className="px-4 py-2 text-right text-gray-700">
                        {fila.haber > 0 ? formatearImporte(fila.haber) : ''}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <p className="text-xs text-gray-400 mt-4">
              Mostrando 6 de 6 registros de ejemplo
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
                  <dd className="text-gray-800 font-medium">6 partidas (2 asientos)</dd>
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
              onClick={confirmarImportacion}
              className="px-6 py-2.5 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors"
            >
              Importar
            </button>
          </div>
        )}
      </div>

      {/* Botones de navegacion */}
      <div className="flex justify-between mt-6">
        <button
          onClick={() => setPaso((prev) => (prev > 1 ? ((prev - 1) as PasoImportar) : prev))}
          disabled={paso === 1}
          className="px-4 py-2 text-sm text-gray-600 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Anterior
        </button>
        <button
          onClick={() => setPaso((prev) => (prev < 3 ? ((prev + 1) as PasoImportar) : prev))}
          disabled={paso === 3 || (paso === 1 && !archivoNombre)}
          className="px-4 py-2 text-sm text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Siguiente
        </button>
      </div>
    </div>
  )
}
