import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

/**
 * Guarda de ruta — redirige a /login si no hay token.
 * Los clientes (rol="cliente") son redirigidos al portal en lugar del dashboard.
 * Preserva la URL original para redirigir despues del login.
 */
export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { token, usuario, cargando } = useAuth()
  const location = useLocation()

  if (cargando) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-gray-500 text-lg">Cargando...</div>
      </div>
    )
  }

  if (!token) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  // Los clientes no tienen acceso al dashboard de contabilidad
  if (usuario?.rol === 'cliente') {
    return <Navigate to="/portal" replace />
  }

  return <>{children}</>
}
