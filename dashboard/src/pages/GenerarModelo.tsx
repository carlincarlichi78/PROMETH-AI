import { useEffect, useState } from 'react'
import { useParams, useSearchParams, Link } from 'react-router-dom'
import { useApi } from '../hooks/useApi'

/** Casilla de un modelo fiscal */
interface Casilla {
  numero: string
  descripcion: string
  valor: number
  editable: boolean
}

/** Resultado del calculo de un modelo */
interface ResultadoCalculo {
  modelo: string
  periodo: string
  ejercicio: number
  casillas: Casilla[]
  validacion: {
    estado: 'ok' | 'error' | 'advertencia'
    mensajes: string[]
  }
}

/** Modelos disponibles en el sistema */
const MODELOS_DISPONIBLES = [
  { codigo: '303', nombre: '303 — IVA trimestral' },
  { codigo: '111', nombre: '111 — Retenciones IRPF' },
  { codigo: '130', nombre: '130 — Pago fraccionado IRPF' },
  { codigo: '115', nombre: '115 — Retenciones alquileres' },
  { codigo: '347', nombre: '347 — Operaciones con terceros' },
  { codigo: '390', nombre: '390 — Resumen anual IVA' },
  { codigo: '190', nombre: '190 — Resumen anual retenciones' },
  { codigo: '200', nombre: '200 — Impuesto Sociedades' },
]

/** Periodos disponibles */
const PERIODOS = [
  { valor: 'T1', etiqueta: 'T1 — Enero/Marzo' },
  { valor: 'T2', etiqueta: 'T2 — Abril/Junio' },
  { valor: 'T3', etiqueta: 'T3 — Julio/Septiembre' },
  { valor: 'T4', etiqueta: 'T4 — Octubre/Diciembre' },
  { valor: '0A', etiqueta: '0A — Anual' },
]


/** Badge de estado de validacion */
function BadgeValidacion({ estado, mensajes }: { estado: 'ok' | 'error' | 'advertencia'; mensajes: string[] }) {
  const clases = {
    ok: 'bg-green-100 text-green-800 border-green-200',
    error: 'bg-red-100 text-red-800 border-red-200',
    advertencia: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  }
  const etiqueta = {
    ok: 'OK',
    error: 'Error',
    advertencia: 'Advertencia',
  }

  return (
    <div className={`border rounded-lg p-3 ${clases[estado]}`}>
      <div className="flex items-center gap-2 mb-1">
        <span className="font-semibold text-sm">{etiqueta[estado]}</span>
      </div>
      <ul className="text-xs space-y-0.5">
        {mensajes.map((msg, i) => (
          <li key={i}>{msg}</li>
        ))}
      </ul>
    </div>
  )
}

/** Formatea numero con locale espanol */
function formatearImporte(valor: number): string {
  return valor.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

/**
 * GenerarModelo — formulario para calcular y descargar un modelo fiscal.
 * Ruta: /empresa/:id/modelos-fiscales/generar
 */
export function GenerarModelo() {
  const { id } = useParams<{ id: string }>()
  const [searchParams] = useSearchParams()
  const { fetchConAuth } = useApi()
  const empresaId = id ?? ''
  const anoActual = new Date().getFullYear()

  const [modeloSeleccionado, setModeloSeleccionado] = useState(searchParams.get('modelo') ?? '303')
  const [periodoSeleccionado, setPeriodoSeleccionado] = useState(searchParams.get('periodo') ?? 'T1')
  const [ejercicio, setEjercicio] = useState(Number(searchParams.get('ejercicio') ?? anoActual))
  const [resultado, setResultado] = useState<ResultadoCalculo | null>(null)
  const [calculando, setCalculando] = useState(false)
  const [descargando, setDescargando] = useState<'boe' | 'pdf' | null>(null)
  const [errorDescarga, setErrorDescarga] = useState<string | null>(null)
  const [casillasEditadas, setCasillasEditadas] = useState<Record<string, number>>({})

  /** Casillas combinando resultado con ediciones del usuario */
  const casillasActuales: Casilla[] = (resultado?.casillas ?? []).map((c) => ({
    ...c,
    valor: c.numero in casillasEditadas ? (casillasEditadas[c.numero] ?? c.valor) : c.valor,
  }))

  const calcular = async () => {
    setCalculando(true)
    setCasillasEditadas({})
    try {
      const datos = await fetchConAuth<ResultadoCalculo>('/api/modelos/calcular', {
        method: 'POST',
        body: {
          empresa_id: Number(empresaId),
          modelo: modeloSeleccionado,
          periodo: periodoSeleccionado,
          ejercicio,
        },
      })
      setResultado(datos)
    } catch (err) {
      setResultado({
        modelo: modeloSeleccionado,
        periodo: periodoSeleccionado,
        ejercicio,
        casillas: [],
        validacion: {
          estado: 'error',
          mensajes: [err instanceof Error ? err.message : 'Error al calcular el modelo'],
        },
      })
    } finally {
      setCalculando(false)
    }
  }

  /** Descarga un archivo desde la API */
  const descargar = async (tipo: 'boe' | 'pdf') => {
    if (!resultado) return
    setDescargando(tipo)
    setErrorDescarga(null)
    try {
      const endpoint = tipo === 'boe' ? '/api/modelos/generar-boe' : '/api/modelos/generar-pdf'
      const token = localStorage.getItem('sfce_token') ?? ''
      const resp = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          empresa_id: Number(empresaId),
          modelo: resultado.modelo,
          periodo: resultado.periodo,
          ejercicio: resultado.ejercicio,
          casillas: casillasActuales,
        }),
      })
      if (!resp.ok) throw new Error(`Error al generar ${tipo.toUpperCase()}`)
      const blob = await resp.blob()
      const extension = tipo === 'boe' ? 'txt' : 'pdf'
      const nombreArchivo = `Mod${resultado.modelo}_${resultado.periodo}_${resultado.ejercicio}.${extension}`
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = nombreArchivo
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      setErrorDescarga(err instanceof Error ? err.message : `Error al descargar ${tipo.toUpperCase()}`)
    } finally {
      setDescargando(null)
    }
  }

  /** Actualiza el valor de una casilla editable */
  const actualizarCasilla = (numero: string, valor: string) => {
    const valorNum = parseFloat(valor.replace(',', '.')) || 0
    setCasillasEditadas((prev) => ({ ...prev, [numero]: valorNum }))
  }

  /** Ejecutar calculo automaticamente si hay parametros en la URL */
  useEffect(() => {
    if (searchParams.get('modelo')) {
      void calcular()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

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
      <h1 className="text-2xl font-bold text-gray-800 mb-6">Generar Modelo Fiscal</h1>

      {/* Formulario de seleccion */}
      <div className="bg-white rounded-lg shadow p-5 mb-6">
        <h2 className="text-sm font-semibold text-gray-700 mb-4 uppercase tracking-wide">
          Parametros del modelo
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Modelo */}
          <div>
            <label className="block text-xs text-gray-500 mb-1">Modelo</label>
            <select
              value={modeloSeleccionado}
              onChange={(e) => {
                setModeloSeleccionado(e.target.value)
                setResultado(null)
              }}
              className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {MODELOS_DISPONIBLES.map((m) => (
                <option key={m.codigo} value={m.codigo}>
                  {m.nombre}
                </option>
              ))}
            </select>
          </div>

          {/* Periodo */}
          <div>
            <label className="block text-xs text-gray-500 mb-1">Periodo</label>
            <select
              value={periodoSeleccionado}
              onChange={(e) => {
                setPeriodoSeleccionado(e.target.value)
                setResultado(null)
              }}
              className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {PERIODOS.map((p) => (
                <option key={p.valor} value={p.valor}>
                  {p.etiqueta}
                </option>
              ))}
            </select>
          </div>

          {/* Ejercicio */}
          <div>
            <label className="block text-xs text-gray-500 mb-1">Ejercicio</label>
            <select
              value={ejercicio}
              onChange={(e) => {
                setEjercicio(Number(e.target.value))
                setResultado(null)
              }}
              className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {anosDisponibles.map((ano) => (
                <option key={ano} value={ano}>
                  {ano}
                </option>
              ))}
            </select>
          </div>

          {/* Boton calcular */}
          <div className="flex items-end">
            <button
              onClick={() => void calcular()}
              disabled={calculando}
              className="w-full px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded hover:bg-blue-700 disabled:bg-blue-300 disabled:cursor-not-allowed transition-colors"
            >
              {calculando ? 'Calculando...' : 'Calcular'}
            </button>
          </div>
        </div>
      </div>

      {/* Resultado */}
      {resultado && (
        <>
          {/* Validacion */}
          <div className="mb-4">
            <BadgeValidacion estado={resultado.validacion.estado} mensajes={resultado.validacion.mensajes} />
          </div>

          {/* Tabla de casillas */}
          <div className="bg-white rounded-lg shadow overflow-hidden mb-4">
            <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
                Casillas — Mod. {resultado.modelo} / {resultado.periodo} / {resultado.ejercicio}
              </h2>
              <span className="text-xs text-gray-400">{casillasActuales.length} casillas</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-gray-500 uppercase border-b bg-gray-50">
                    <th className="px-5 py-3 w-20">Casilla</th>
                    <th className="px-5 py-3">Descripcion</th>
                    <th className="px-5 py-3 text-right w-40">Valor</th>
                    <th className="px-5 py-3 w-16 text-center">Edit.</th>
                  </tr>
                </thead>
                <tbody>
                  {casillasActuales.map((casilla, i) => (
                    <tr key={casilla.numero} className={i % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                      <td className="px-5 py-3 font-mono font-semibold text-gray-700">{casilla.numero}</td>
                      <td className="px-5 py-3 text-gray-700">{casilla.descripcion}</td>
                      <td className="px-5 py-3 text-right">
                        {casilla.editable ? (
                          <input
                            type="number"
                            step="0.01"
                            value={casillasEditadas[casilla.numero] ?? casilla.valor}
                            onChange={(e) => actualizarCasilla(casilla.numero, e.target.value)}
                            className="w-32 text-right border border-blue-300 rounded px-2 py-1 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
                          />
                        ) : (
                          <span className="font-mono text-gray-800">{formatearImporte(casilla.valor)}</span>
                        )}
                      </td>
                      <td className="px-5 py-3 text-center">
                        {casilla.editable && (
                          <span className="inline-block w-2 h-2 rounded-full bg-blue-400" title="Editable" />
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Error de descarga */}
          {errorDescarga && (
            <div className="mb-3 bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-red-700 text-sm">
              {errorDescarga}
            </div>
          )}

          {/* Botones de descarga */}
          <div className="flex flex-wrap gap-3">
            <button
              onClick={() => void descargar('boe')}
              disabled={descargando !== null}
              className="px-5 py-2 bg-gray-800 text-white text-sm font-medium rounded hover:bg-gray-900 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              {descargando === 'boe' ? 'Generando BOE...' : 'Descargar BOE (.txt)'}
            </button>
            <button
              onClick={() => void descargar('pdf')}
              disabled={descargando !== null}
              className="px-5 py-2 bg-red-600 text-white text-sm font-medium rounded hover:bg-red-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              {descargando === 'pdf' ? 'Generando PDF...' : 'Descargar PDF'}
            </button>
            <Link
              to={`/empresa/${empresaId}/modelos-fiscales/historico`}
              className="px-5 py-2 bg-gray-100 text-gray-700 text-sm font-medium rounded hover:bg-gray-200 transition-colors"
            >
              Ver historico
            </Link>
          </div>
        </>
      )}

      {/* Estado vacio antes de calcular */}
      {!resultado && !calculando && (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <p className="text-gray-400 text-lg mb-2">Selecciona los parametros y pulsa Calcular</p>
          <p className="text-gray-300 text-sm">
            Se calcularan las casillas del modelo a partir de los datos contables registrados en el sistema
          </p>
        </div>
      )}
    </div>
  )
}
