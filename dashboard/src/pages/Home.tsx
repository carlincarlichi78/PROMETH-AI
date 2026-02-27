import { useAuth } from '../context/AuthContext'

/** Pagina principal — lista de empresas del usuario */
export function Home() {
  const { usuario } = useAuth()

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-800 mb-4">
        Panel de Control
      </h1>
      <p className="text-gray-600 mb-6">
        Bienvenido, {usuario?.nombre ?? 'usuario'}
      </p>

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-700 mb-3">
          Empresas
        </h2>
        <p className="text-gray-500">
          Selecciona una empresa para ver su contabilidad.
        </p>
        {/* TODO: listar empresas desde API */}
        <p className="text-sm text-amber-600 mt-4">En construccion</p>
      </div>
    </div>
  )
}
