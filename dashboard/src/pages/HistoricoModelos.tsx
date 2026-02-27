import { useEffect, useState, useMemo } from 'react'
import { useParams, Link } from 'react-router-dom'

/** Registro de un modelo generado en el historico */
interface RegistroHistorico {
  id: number
  modelo: string
  nombre_modelo: string
  ejercicio: number
  periodo: string
  fecha_generacion: string
  estado: 'generado' | 'presentado'
  tiene_boe: boolean
  tiene_pdf: boolean
}

/** Respuesta de la API del historico */
interface RespuestaHistorico {
  total: number
  registros: RegistroHistorico[]
}

/** Datos mock para desarrollo */
const MOCK_HISTORICO: RegistroHistorico[] = [
  { id: 1, modelo: '303', nombre_modelo: 'IVA trimestral', ejercicio: 2025, periodo: 'T1', fecha_generacion: '2025-04-15T10:30:00', estado: 'presentado', tiene_boe: true, tiene_pdf: true },
  { id: 2, modelo: '111', nombre_modelo: 'Retenciones IRPF', ejercicio: 2025, periodo: 'T1', fecha_generacion: '2025-04-15T11:00:00', estado: 'presentado', tiene_boe: true, tiene_pdf: true },
  { id: 3, modelo: '130', nombre_modelo: 'Pago fraccionado IRPF', ejercicio: 2025, periodo: 'T1', fecha_generacion: '2025-04-16T09:15:00', estado: 'presentado', tiene_boe: true, tiene_pdf: false },
  { id: 4, modelo: '303', nombre_modelo: 'IVA trimestral', ejercicio: 2025, periodo: 'T2', fecha_generacion: '2025-07-18T14:20:00', estado: 'presentado', tiene_boe: true, tiene_pdf: true },
  { id: 5, modelo: '111', nombre_modelo: 'Retenciones IRPF', ejercicio: 2025, periodo: 'T2', fecha_generacion: '2025-07-18T14:45:00', estado: 'generado', tiene_boe: true, tiene_pdf: true },
  { id: 6, modelo: '303', nombre_modelo: 'IVA trimestral', ejercicio: 2024, periodo: 'T4', fecha_generacion: '2025-01-22T16:00:00', estado: 'presentado', tiene_boe: true, tiene_pdf: true },
  { id: 7, modelo: '390', nombre_modelo: 'Resumen anual IVA', ejercicio: 2024, periodo: '0A', fecha_generacion: '2025-01-25T10:00:00', estado: 'presentado', tiene_boe: true, tiene_pdf: true },
  { id: 8, modelo: '190', nombre_modelo: 'Resumen anual retenciones', ejercicio: 2024, periodo: '0A', fecha_generacion: '2025-01-25T11:30:00', estado: 'presentado', tiene_boe: true, tiene_pdf: false },
  { id: 9, modelo: '347', nombre_modelo: 'Operaciones con terceros', ejercicio: 2024, periodo: '0A', fecha_generacion: '2025-02-20T09:00:00', estado: 'presentado', tiene_boe: true, tiene_pdf: false },
  { id: 10, modelo: '115', nombre_modelo: 'Retenciones alquileres', ejercicio: 2025, periodo: 'T1', fecha_generacion: '2025-04-16T10:00:00', estado: 'presentado', tiene_boe: true, tiene_pdf: true },
  { id: 11, modelo: '115', nombre_modelo: 'Retenciones alquileres', ejercicio: 2025, periodo: 'T2', fecha_generacion: '2025-07-19T09:30:00', estado: 'generado', tiene_boe: false, tiene_pdf: false },
]

/** Modelos disponibles para filtrar */
const MODELOS_FILTRO = [
  { valor: 'todos', etiqueta: 'Todos los modelos' },
  { valor: '303', etiqueta: '303 — IVA trimestral' },
  { valor: '111', etiqueta: '111 — Retenciones IRPF' },
  { valor: '130', etiqueta: '130 — Pago fraccionado' },
  { valor: '115', etiqueta: '115 — Retenciones alquileres' },
  { valor: '347', etiqueta: '347 — Terceros' },
  { valor: '390', etiqueta: '390 — Resumen anual IVA' },
  { valor: '190', etiqueta: '190 — Resumen anual retenciones' },
  { valor: '200', etiqueta: '200 — Impuesto Sociedades' },
]

const REGISTROS_POR_PAGINA = 10

/** Formatea fecha ISO a DD/MM/YYYY HH:mm */
function formatearFechaHora(iso: string): string {
  const fecha = new Date(iso)
  const dia = String(fecha.getDate()).padStart(2, '0')
  const mes = String(fecha.getMonth() + 1).padStart(2, '0')
  const ano = fecha.getFullYear()
  const horas = String(fecha.getHours()).padStart(2, '0')
  const minutos = String(fecha.getMinutes()).padStart(2, '0')
  return `${dia}/${mes}/${ano} ${horas}:${minutos}`
}

/** Badge de estado del registro */
function BadgeEstadoRegistro({ estado }: { estado: 'generado' | 'presentado' }) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
        estado === 'presentado'
          ? 'bg-green-100 text-green-800'
          : 'bg-blue-100 text-blue-800'
      }`}
    >
      {estado === 'presentado' ? 'Presentado' : 'Generado'}
    </span>
  )
}

/**
 * HistoricoModelos — tabla paginada de modelos fiscales generados.
 * Ruta: /empresa/:id/modelos-fiscales/historico
 */
export function HistoricoModelos() {
  const { id } = useParams<{ id: string }>()
  const empresaId = id ?? ''
  const anoActual = new Date().getFullYear()

  const [registros, setRegistros] = useState<RegistroHistorico[]>([])
  const [total, setTotal] = useState(0)
  const [cargando, setCargando] = useState(true)
  const [filtroEjercicio, setFiltroEjercicio] = useState('todos')
  const [filtroModelo, setFiltroModelo] = useState('todos')
  const [pagina, setPagina] = useState(1)
  const [descargando, setDescargando] = useState<{ id: number; tipo: 'boe' | 'pdf' } | null>(null)

  /** Carga el historico desde la API o mock */
  useEffect(() => {
    const cargar = async () => {
      setCargando(true)
      setPagina(1)
      try {
        const params = new URLSearchParams()
        if (filtroEjercicio !== 'todos') params.set('ejercicio', filtroEjercicio)
        if (filtroModelo !== 'todos') params.set('modelo', filtroModelo)
        const url = `/api/modelos/historico/${empresaId}?${params.toString()}`
        const resp = await fetch(url, {
          headers: { Authorization: `Bearer ${localStorage.getItem('sfce_token') ?? ''}` },
        })
        if (!resp.ok) throw new Error('API no disponible')
        const datos = (await resp.json()) as RespuestaHistorico
        setRegistros(datos.registros)
        setTotal(datos.total)
      } catch {
        // Fallback mock con filtrado local
        let filtrados = [...MOCK_HISTORICO]
        if (filtroEjercicio !== 'todos') {
          filtrados = filtrados.filter((r) => r.ejercicio === Number(filtroEjercicio))
        }
        if (filtroModelo !== 'todos') {
          filtrados = filtrados.filter((r) => r.modelo === filtroModelo)
        }
        setRegistros(filtrados)
        setTotal(filtrados.length)
      } finally {
        setCargando(false)
      }
    }
    void cargar()
  }, [empresaId, filtroEjercicio, filtroModelo])

  /** Registros de la pagina actual */
  const registrosPagina = useMemo(() => {
    const inicio = (pagina - 1) * REGISTROS_POR_PAGINA
    return registros.slice(inicio, inicio + REGISTROS_POR_PAGINA)
  }, [registros, pagina])

  /** Total de paginas */
  const totalPaginas = Math.max(1, Math.ceil(registros.length / REGISTROS_POR_PAGINA))

  /** Descarga un archivo de un registro especifico */
  const descargar = async (registro: RegistroHistorico, tipo: 'boe' | 'pdf') => {
    setDescargando({ id: registro.id, tipo })
    try {
      const endpoint = tipo === 'boe' ? `/api/modelos/${registro.id}/descargar-boe` : `/api/modelos/${registro.id}/descargar-pdf`
      const resp = await fetch(endpoint, {
        headers: { Authorization: `Bearer ${localStorage.getItem('sfce_token') ?? ''}` },
      })
      if (!resp.ok) throw new Error('API no disponible')
      const blob = await resp.blob()
      const extension = tipo === 'boe' ? 'txt' : 'pdf'
      const nombreArchivo = `Mod${registro.modelo}_${registro.periodo}_${registro.ejercicio}.${extension}`
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = nombreArchivo
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      alert(`[MOCK] Descarga ${tipo.toUpperCase()} simulada — API no disponible`)
    } finally {
      setDescargando(null)
    }
  }

  /** Anos disponibles para el filtro */
  const anosDisponibles = [anoActual - 1, anoActual]

  return (
    <div>
      {/* Cabecera */}
      <Link
        to={`/empresa/${empresaId}/modelos-fiscales`}
        className="text-sm text-[var(--color-primary)] hover:underline mb-2 inline-block"
      >
        Volver al calendario
      </Link>
      <div className="mb-6 flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Historico de Modelos</h1>
          <p className="text-sm text-gray-500 mt-1">
            {!cargando && `${total} modelo${total !== 1 ? 's' : ''} generado${total !== 1 ? 's' : ''}`}
          </p>
        </div>
        <Link
          to={`/empresa/${empresaId}/modelos-fiscales/generar`}
          className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded hover:bg-blue-700 transition-colors"
        >
          + Generar modelo
        </Link>
      </div>

      {/* Filtros */}
      <div className="bg-white rounded-lg shadow p-4 mb-4 flex flex-wrap gap-4 items-center">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Ejercicio</label>
          <select
            value={filtroEjercicio}
            onChange={(e) => setFiltroEjercicio(e.target.value)}
            className="border border-gray-300 rounded px-3 py-1.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="todos">Todos</option>
            {anosDisponibles.map((ano) => (
              <option key={ano} value={String(ano)}>
                {ano}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Modelo</label>
          <select
            value={filtroModelo}
            onChange={(e) => setFiltroModelo(e.target.value)}
            className="border border-gray-300 rounded px-3 py-1.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {MODELOS_FILTRO.map((m) => (
              <option key={m.valor} value={m.valor}>
                {m.etiqueta}
              </option>
            ))}
          </select>
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
      ) : registrosPagina.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <div className="text-gray-300 text-5xl mb-4">📄</div>
          <p className="text-gray-500 text-lg mb-2">Sin modelos generados</p>
          <p className="text-gray-400 text-sm mb-6">
            {filtroEjercicio !== 'todos' || filtroModelo !== 'todos'
              ? 'No hay registros con los filtros seleccionados'
              : 'Aun no se ha generado ningun modelo fiscal para esta empresa'}
          </p>
          <Link
            to={`/empresa/${empresaId}/modelos-fiscales/generar`}
            className="inline-block px-5 py-2 bg-blue-600 text-white text-sm font-medium rounded hover:bg-blue-700 transition-colors"
          >
            Generar primer modelo
          </Link>
        </div>
      ) : (
        <>
          <div className="bg-white rounded-lg shadow overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-500 uppercase border-b bg-gray-50">
                  <th className="px-5 py-3">Modelo</th>
                  <th className="px-5 py-3">Periodo</th>
                  <th className="px-5 py-3">Ejercicio</th>
                  <th className="px-5 py-3">Generado</th>
                  <th className="px-5 py-3 text-center">Estado</th>
                  <th className="px-5 py-3 text-center">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {registrosPagina.map((registro, i) => (
                  <tr key={registro.id} className={i % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                    <td className="px-5 py-3">
                      <div className="font-semibold text-gray-800">Mod. {registro.modelo}</div>
                      <div className="text-xs text-gray-400">{registro.nombre_modelo}</div>
                    </td>
                    <td className="px-5 py-3 text-gray-700 font-mono">{registro.periodo}</td>
                    <td className="px-5 py-3 text-gray-700">{registro.ejercicio}</td>
                    <td className="px-5 py-3 text-gray-500 text-xs whitespace-nowrap">
                      {formatearFechaHora(registro.fecha_generacion)}
                    </td>
                    <td className="px-5 py-3 text-center">
                      <BadgeEstadoRegistro estado={registro.estado} />
                    </td>
                    <td className="px-5 py-3">
                      <div className="flex items-center justify-center gap-2">
                        {registro.tiene_boe ? (
                          <button
                            onClick={() => void descargar(registro, 'boe')}
                            disabled={descargando?.id === registro.id}
                            className="px-3 py-1 text-xs bg-gray-800 text-white rounded hover:bg-gray-900 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors whitespace-nowrap"
                          >
                            {descargando?.id === registro.id && descargando.tipo === 'boe'
                              ? '...'
                              : 'BOE'}
                          </button>
                        ) : (
                          <span className="px-3 py-1 text-xs text-gray-300 border border-gray-200 rounded whitespace-nowrap">
                            BOE
                          </span>
                        )}
                        {registro.tiene_pdf ? (
                          <button
                            onClick={() => void descargar(registro, 'pdf')}
                            disabled={descargando?.id === registro.id}
                            className="px-3 py-1 text-xs bg-red-600 text-white rounded hover:bg-red-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors whitespace-nowrap"
                          >
                            {descargando?.id === registro.id && descargando.tipo === 'pdf'
                              ? '...'
                              : 'PDF'}
                          </button>
                        ) : (
                          <span className="px-3 py-1 text-xs text-gray-300 border border-gray-200 rounded whitespace-nowrap">
                            PDF
                          </span>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Paginacion */}
          {totalPaginas > 1 && (
            <div className="mt-4 flex items-center justify-between">
              <p className="text-sm text-gray-500">
                Pagina {pagina} de {totalPaginas} &middot; {registros.length} registros
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => setPagina((p) => Math.max(1, p - 1))}
                  disabled={pagina === 1}
                  className="px-3 py-1.5 text-sm border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  Anterior
                </button>
                {Array.from({ length: totalPaginas }, (_, idx) => idx + 1)
                  .filter((p) => p === 1 || p === totalPaginas || Math.abs(p - pagina) <= 1)
                  .map((p, idx, arr) => (
                    <span key={p}>
                      {idx > 0 && arr[idx - 1] !== undefined && (arr[idx - 1] as number) < p - 1 && (
                        <span className="px-1 text-gray-400 self-center">…</span>
                      )}
                      <button
                        onClick={() => setPagina(p)}
                        className={`px-3 py-1.5 text-sm border rounded transition-colors ${
                          p === pagina
                            ? 'bg-blue-600 text-white border-blue-600'
                            : 'border-gray-300 hover:bg-gray-50'
                        }`}
                      >
                        {p}
                      </button>
                    </span>
                  ))}
                <button
                  onClick={() => setPagina((p) => Math.min(totalPaginas, p + 1))}
                  disabled={pagina === totalPaginas}
                  className="px-3 py-1.5 text-sm border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  Siguiente
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
