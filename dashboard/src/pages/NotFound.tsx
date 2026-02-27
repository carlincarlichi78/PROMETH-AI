import { Link } from 'react-router-dom'

/** Pagina 404 */
export function NotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <div className="text-center">
        <h1 className="text-6xl font-bold text-gray-300 mb-4">404</h1>
        <p className="text-xl text-gray-600 mb-6">Pagina no encontrada</p>
        <Link
          to="/"
          className="px-6 py-2.5 bg-[var(--color-primary)] hover:bg-[var(--color-primary-dark)] text-white rounded-md transition-colors"
        >
          Volver al inicio
        </Link>
      </div>
    </div>
  )
}
