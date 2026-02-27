import { Outlet } from 'react-router-dom'
import { SidebarProvider, SidebarInset } from '@/components/ui/sidebar'
import { AppSidebar } from './app-sidebar'
import { Header } from './header'
import { Toaster } from '@/components/ui/sonner'
import { useUIStore } from '@/stores/ui-store'

export function AppShell() {
  const sidebarColapsado = useUIStore((s) => s.sidebarColapsado)

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
