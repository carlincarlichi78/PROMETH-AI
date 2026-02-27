import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

/**
 * Guarda de ruta — redirige a /login si no hay token.
 * Preserva la URL original para redirigir despues del login.
 */
export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { token, cargando } = useAuth()
  const location = useLocation()

  // Mientras valida el token, mostrar indicador de carga
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

  return <>{children}</>
}
