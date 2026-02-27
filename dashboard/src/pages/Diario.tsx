import { useEffect, useState, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import type { Asiento } from '../types'

/** Formatea un numero con locale espanol */
function formatearImporte(valor: number): string {
  return valor.toLocaleString('es-ES', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

/** Formatea fecha ISO a DD/MM/YYYY */
function formatearFecha(fecha: string): string {
  const partes = fecha.split('-')
  if (partes.length === 3) {
    return `${partes[2]}/${partes[1]}/${partes[0]}`
  }
  return fecha
}

const LIMITE = 50

/** Pagina del Libro Diario — asientos con partidas expandibles */
export function Diario() {
  const { id } = useParams()
  const { fetchConAuth } = useApi()
  const empresaId = Number(id)

  const [asientos, setAsientos] = useState<Asiento[]>([])
  const [expandidos, setExpandidos] = useState<Set<number>>(new Set())
  const [cargando, setCargando] = useState(true)
  const [cargandoMas, setCargandoMas] = useState(false)
  const [hayMas, setHayMas] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const cargarDatos = useCallback(async (offset: number = 0, acumular: boolean = false) => {
    if (offset === 0) {
      setCargando(true)
    } else {
      setCargandoMas(true)
    }
    setError(null)
    try {
      const nuevos = await fetchConAuth<Asiento[]>(
        `/api/contabilidad/${empresaId}/diario?limit=${LIMITE}&offset=${offset}`
      )
      if (acumular) {
        setAsientos((prev) => [...prev, ...nuevos])
      } else {
        setAsientos(nuevos)
      }
      setHayMas(nuevos.length === LIMITE)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al cargar diario')
    } finally {
      setCargando(false)
      setCargandoMas(false)
    }
  }, [empresaId, fetchConAuth])

  useEffect(() => {
    if (empresaId) {
      void cargarDatos(0)
    }
  }, [empresaId, cargarDatos])

  const cargarMas = () => {
    void cargarDatos(asientos.length, true)
  }

  const alternarExpansion = (asientoId: number) => {
    setExpandidos((prev) => {
      const nuevo = new Set(prev)
      if (nuevo.has(asientoId)) {
        nuevo.delete(asientoId)
      } else {
        nuevo.add(asientoId)
      }
      return nuevo
    })
  }

  if (cargando) {
    return (
      <div className="animate-pulse">
        <div className="h-8 bg-gray-200 rounded w-1/4 mb-6" />
        <div className="bg-white rounded-lg shadow">
          {[1, 2, 3, 4, 5].map((i) => (
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
            onClick={() => void cargarDatos(0)}
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
      <h1 className="text-2xl font-bold text-gray-800 mb-6">Libro Diario</h1>

      {asientos.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-6 text-center">
          <p className="text-gray-500">No se encontraron asientos contables.</p>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-gray-500 uppercase border-b bg-gray-50">
                <th className="px-5 py-3 w-8" />
                <th className="px-5 py-3">Fecha</th>
                <th className="px-5 py-3">Num.</th>
                <th className="px-5 py-3">Concepto</th>
                <th className="px-5 py-3">Origen</th>
                <th className="px-5 py-3 text-right">Importe</th>
              </tr>
            </thead>
            <tbody>
              {asientos.map((asiento, i) => {
                const expandido = expandidos.has(asiento.id)
                const totalDebe = asiento.partidas.reduce((s, p) => s + p.debe, 0)

                return (
                  <AsientoFila
                    key={asiento.id}
                    asiento={asiento}
                    indice={i}
                    expandido={expandido}
                    totalDebe={totalDebe}
                    onAlternar={() => alternarExpansion(asiento.id)}
                  />
                )
              })}
            </tbody>
          </table>

          {/* Boton cargar mas */}
          {hayMas && (
            <div className="px-5 py-4 border-t border-gray-100 text-center">
              <button
                onClick={cargarMas}
                disabled={cargandoMas}
                className="px-6 py-2 text-sm bg-[var(--color-primary)] text-white rounded hover:bg-[var(--color-primary-dark)] transition-colors disabled:opacity-50"
              >
                {cargandoMas ? 'Cargando...' : 'Cargar mas'}
              </button>
            </div>
          )}
        </div>
      )}

      <p className="text-xs text-gray-400 mt-3">
        Mostrando {asientos.length} asiento{asientos.length !== 1 ? 's' : ''}
      </p>
    </div>
  )
}

/** Fila de asiento con expansion para partidas */
function AsientoFila({ asiento, indice, expandido, totalDebe, onAlternar }: {
  asiento: Asiento
  indice: number
  expandido: boolean
  totalDebe: number
  onAlternar: () => void
}) {
  const filaClase = indice % 2 === 0 ? 'bg-white' : 'bg-gray-50'

  return (
    <>
      <tr
        className={`${filaClase} cursor-pointer hover:bg-blue-50 transition-colors`}
        onClick={onAlternar}
      >
        <td className="px-5 py-3 text-gray-400">
          <span className="text-xs">{expandido ? '\u25BC' : '\u25B6'}</span>
        </td>
        <td className="px-5 py-3 text-gray-700 whitespace-nowrap">
          {formatearFecha(asiento.fecha)}
        </td>
        <td className="px-5 py-3 text-gray-700 font-mono">
          {asiento.numero ?? '-'}
        </td>
        <td className="px-5 py-3 text-gray-800 max-w-md truncate">
          {asiento.concepto ?? '-'}
        </td>
        <td className="px-5 py-3 text-gray-500 text-xs">
          {asiento.origen ?? '-'}
        </td>
        <td className="px-5 py-3 text-right font-mono text-gray-800">
          {formatearImporte(totalDebe)}
        </td>
      </tr>

      {/* Partidas expandidas */}
      {expandido && asiento.partidas.length > 0 && (
        <tr>
          <td colSpan={6} className="px-0 py-0">
            <div className="bg-slate-50 border-y border-slate-200">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-left text-gray-500 uppercase">
                    <th className="pl-14 pr-4 py-2">Subcuenta</th>
                    <th className="px-4 py-2">Concepto</th>
                    <th className="px-4 py-2 text-right">Debe</th>
                    <th className="px-4 py-2 text-right">Haber</th>
                  </tr>
                </thead>
                <tbody>
                  {asiento.partidas.map((partida) => (
                    <tr key={partida.id} className="border-t border-slate-100">
                      <td className="pl-14 pr-4 py-1.5 font-mono text-gray-700">{partida.subcuenta}</td>
                      <td className="px-4 py-1.5 text-gray-600 max-w-sm truncate">{partida.concepto ?? '-'}</td>
                      <td className="px-4 py-1.5 text-right font-mono text-gray-800">
                        {partida.debe > 0 ? formatearImporte(partida.debe) : ''}
                      </td>
                      <td className="px-4 py-1.5 text-right font-mono text-gray-800">
                        {partida.haber > 0 ? formatearImporte(partida.haber) : ''}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </td>
        </tr>
      )}
    </>
  )
}
