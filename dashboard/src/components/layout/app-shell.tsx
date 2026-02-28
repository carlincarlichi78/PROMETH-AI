import { Outlet, useLocation } from 'react-router-dom'
import { useEffect } from 'react'
import { SidebarProvider, SidebarInset } from '@/components/ui/sidebar'
import { AppSidebar } from './app-sidebar'
import { Header } from './header'
import { Toaster } from '@/components/ui/sonner'
import { useUIStore } from '@/stores/ui-store'
import { useThemeEffect } from '@/hooks/use-theme'
import { useEmpresaStore } from '@/stores/empresa-store'

export function AppShell() {
  const sidebarColapsado = useUIStore((s) => s.sidebarColapsado)
  const { empresaActiva, setEmpresaActiva } = useEmpresaStore()
  const location = useLocation()
  useThemeEffect()

  // Auto-hidratar empresaActiva desde la URL cuando se accede directamente a /empresa/:id/...
  useEffect(() => {
    const match = location.pathname.match(/^\/empresa\/(\d+)/)
    if (!match) return
    const id = Number(match[1])
    if (empresaActiva?.id === id) return
    const token = sessionStorage.getItem('sfce_token')
    fetch(`/api/empresas/${id}`, {
      headers: { Authorization: token ? `Bearer ${token}` : '' },
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => { if (data) setEmpresaActiva(data) })
      .catch(() => {})
  }, [location.pathname])

  return (
    <SidebarProvider defaultOpen={!sidebarColapsado}>
      <AppSidebar />
      <SidebarInset>
        <Header />
        <main className="flex-1 p-6 overflow-auto min-h-[calc(100vh-3.5rem)]">
          <Outlet />
        </main>
      </SidebarInset>
      <Toaster richColors position="bottom-right" />
    </SidebarProvider>
  )
}
