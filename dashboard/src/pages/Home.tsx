import { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { useApi } from '../hooks/useApi'
import { EmpresaCard } from '../components/EmpresaCard'
import type { Empresa } from '../types'

/** Pagina principal — cuadricula de empresas del usuario */
export function Home() {
  const { usuario } = useAuth()
  const { fetchConAuth } = useApi()

  const [empresas, setEmpresas] = useState<Empresa[]>([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const cargarEmpresas = async () => {
    setCargando(true)
    setError(null)
    try {
      const datos = await fetchConAuth<Empresa[]>('/api/empresas')
      setEmpresas(datos)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al cargar empresas')
    } finally {
      setCargando(false)
    }
  }

  useEffect(() => {
    void cargarEmpresas()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-800 mb-1">
        Panel de Control
      </h1>
      <p className="text-gray-500 mb-6">
        Bienvenido, {usuario?.nombre ?? 'usuario'}
      </p>

      {/* Estado de carga */}
      {cargando && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-white rounded-lg shadow border border-gray-200 p-5 animate-pulse">
              <div className="h-5 bg-gray-200 rounded w-3/4 mb-3" />
              <div className="h-4 bg-gray-200 rounded w-1/3 mb-3" />
              <div className="h-4 bg-gray-200 rounded w-1/2" />
            </div>
          ))}
        </div>
      )}

      {/* Error */}
      {error && !cargando && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-700 mb-2">{error}</p>
          <button
            onClick={() => void cargarEmpresas()}
            className="px-4 py-2 text-sm bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
          >
            Reintentar
          </button>
        </div>
      )}

      {/* Lista de empresas */}
      {!cargando && !error && empresas.length === 0 && (
        <div className="bg-white rounded-lg shadow p-6 text-center">
          <p className="text-gray-500">No se encontraron empresas.</p>
        </div>
      )}

      {!cargando && !error && empresas.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {empresas.map((empresa) => (
            <EmpresaCard key={empresa.id} empresa={empresa} />
          ))}
        </div>
      )}
    </div>
  )
}
