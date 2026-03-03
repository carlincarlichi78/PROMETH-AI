import { Outlet, Navigate } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'

export default function PortalLayout() {
  const { token, cargando } = useAuth()
  if (cargando) return null
  if (!token) return <Navigate to="/login" replace />
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b bg-white px-6 py-3 flex items-center gap-3 shadow-sm">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-900 text-white font-bold text-sm select-none">
          P
        </div>
        <div>
          <span className="font-semibold text-sm text-slate-900">PROMETH-AI</span>
          <span className="text-slate-400 text-sm"> — Portal Cliente</span>
        </div>
      </header>
      <main className="container max-w-4xl mx-auto py-8 px-4">
        <Outlet />
      </main>
    </div>
  )
}
