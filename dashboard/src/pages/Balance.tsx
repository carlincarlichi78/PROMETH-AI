import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import type { Balance as BalanceType } from '../types'

/** Formatea un numero con locale espanol */
function formatearImporte(valor: number): string {
  return valor.toLocaleString('es-ES', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }) + ' EUR'
}

/** Pagina de Balance de Situacion */
export function Balance() {
  const { id } = useParams()
  const { fetchConAuth } = useApi()
  const empresaId = Number(id)

  const [datos, setDatos] = useState<BalanceType | null>(null)
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const cargarDatos = async () => {
    setCargando(true)
    setError(null)
    try {
      const balance = await fetchConAuth<BalanceType>(`/api/contabilidad/${empresaId}/balance`)
      setDatos(balance)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al cargar balance')
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
        <div className="grid grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => <div key={i} className="bg-white rounded-lg shadow p-6 h-32" />)}
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

  // Verificar ecuacion fundamental: activo == pasivo + patrimonio_neto
  const sumaPasivoPatrimonio = datos.pasivo + datos.patrimonio_neto
  const diferencia = Math.abs(datos.activo - sumaPasivoPatrimonio)
  const cuadra = diferencia < 0.01

  return (
    <div>
      <Link to={`/empresa/${id}`} className="text-sm text-[var(--color-primary)] hover:underline mb-2 inline-block">
        Volver al resumen
      </Link>
      <h1 className="text-2xl font-bold text-gray-800 mb-6">Balance de Situacion</h1>

      {/* Indicador de cuadre */}
      <div className={`mb-6 p-3 rounded-lg border text-sm ${
        cuadra
          ? 'bg-green-50 border-green-200 text-green-800'
          : 'bg-red-50 border-red-200 text-red-800'
      }`}>
        {cuadra
          ? 'Balance cuadrado: Activo = Pasivo + Patrimonio Neto'
          : `Balance NO cuadra: diferencia de ${formatearImporte(diferencia)}`
        }
      </div>

      {/* Tres tarjetas principales */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        {/* Activo */}
        <div className="bg-white rounded-lg shadow border-t-4 border-blue-500">
          <div className="p-6">
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-2">Activo</h2>
            <p className="text-3xl font-bold text-blue-700">{formatearImporte(datos.activo)}</p>
            <p className="text-xs text-gray-400 mt-2">Bienes y derechos</p>
          </div>
        </div>

        {/* Pasivo */}
        <div className="bg-white rounded-lg shadow border-t-4 border-red-500">
          <div className="p-6">
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-2">Pasivo</h2>
            <p className="text-3xl font-bold text-red-700">{formatearImporte(datos.pasivo)}</p>
            <p className="text-xs text-gray-400 mt-2">Deudas y obligaciones</p>
          </div>
        </div>

        {/* Patrimonio Neto */}
        <div className="bg-white rounded-lg shadow border-t-4 border-green-500">
          <div className="p-6">
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-2">Patrimonio Neto</h2>
            <p className="text-3xl font-bold text-green-700">{formatearImporte(datos.patrimonio_neto)}</p>
            <p className="text-xs text-gray-400 mt-2">Capital y reservas</p>
          </div>
        </div>
      </div>

      {/* Ecuacion fundamental */}
      <div className="bg-white rounded-lg shadow p-5">
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">Ecuacion fundamental</h3>
        <div className="flex flex-wrap items-center gap-3 text-lg">
          <span className="font-mono text-blue-700 font-semibold">{formatearImporte(datos.activo)}</span>
          <span className="text-gray-400">=</span>
          <span className="font-mono text-red-700 font-semibold">{formatearImporte(datos.pasivo)}</span>
          <span className="text-gray-400">+</span>
          <span className="font-mono text-green-700 font-semibold">{formatearImporte(datos.patrimonio_neto)}</span>
        </div>
        <p className="text-xs text-gray-400 mt-2">
          Activo = Pasivo + Patrimonio Neto
        </p>
      </div>
    </div>
  )
}
