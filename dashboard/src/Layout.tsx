import { Outlet } from 'react-router-dom'
import { Sidebar } from './components/Sidebar'

/**
 * Layout principal — sidebar + area de contenido.
 * Envuelve todas las rutas protegidas.
 */
export function Layout() {
  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      <main className="flex-1 p-6 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}
