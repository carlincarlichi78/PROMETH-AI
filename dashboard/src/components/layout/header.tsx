import * as React from 'react'
import { Search, Moon, Sun, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { SidebarTrigger } from '@/components/ui/sidebar'
import { Separator } from '@/components/ui/separator'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { useAuth } from '@/context/AuthContext'
import { useUIStore } from '@/stores/ui-store'
import { Breadcrumbs } from './breadcrumbs'
import { NotificacionesPanel } from '@/features/notificaciones'
import { OmniSearch } from '@/features/omnisearch/omnisearch'

export function Header() {
  const { usuario, logout } = useAuth()
  const { tema, setTema, toggleCopilot } = useUIStore()
  const [omniAbierto, setOmniAbierto] = React.useState(false)

  // Keyboard shortcut global ⌘K / Ctrl+K
  React.useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setOmniAbierto(true)
      }
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [])

  const iniciales =
    usuario?.nombre
      ?.split(' ')
      .map((n) => n[0])
      .join('')
      .slice(0, 2)
      .toUpperCase() ?? '??'

  const esDark = tema === 'dark'

  return (
    <header className="flex h-14 items-center gap-3 border-b px-4 bg-background sticky top-0 z-10">
      <SidebarTrigger />
      <Separator orientation="vertical" className="h-6" />
      <div className="flex-1 overflow-hidden">
        <Breadcrumbs />
      </div>

      <div className="flex items-center gap-1">
        {/* OmniSearch — ⌘K */}
        <button
          type="button"
          onClick={() => setOmniAbierto(true)}
          className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg
                     bg-[var(--surface-1)] border border-border/50 text-muted-foreground
                     hover:bg-[var(--surface-2)] hover:text-foreground transition-all duration-150
                     text-[13px] min-w-[180px]"
        >
          <Search className="h-3.5 w-3.5" />
          <span className="flex-1 text-left">Buscar...</span>
          <kbd className="text-[11px] bg-[var(--surface-2)] px-1.5 py-0.5 rounded border border-border/50">
            ⌘K
          </kbd>
        </button>

        <OmniSearch abierto={omniAbierto} onCerrar={() => setOmniAbierto(false)} />

        {/* Notificaciones */}
        <NotificacionesPanel />

        {/* Copiloto IA */}
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={toggleCopilot}
          title="Copiloto IA"
        >
          <Sparkles className="h-4 w-4" />
        </Button>

        {/* Toggle tema */}
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={() => setTema(esDark ? 'light' : 'dark')}
          title={esDark ? 'Modo claro' : 'Modo oscuro'}
        >
          {esDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </Button>

        {/* Avatar usuario */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="h-8 w-8 rounded-full">
              <Avatar className="h-7 w-7">
                <AvatarFallback className="text-xs bg-primary text-primary-foreground">
                  {iniciales}
                </AvatarFallback>
              </Avatar>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48">
            <div className="px-2 py-1.5">
              <p className="text-sm font-medium">{usuario?.nombre}</p>
              <p className="text-xs text-muted-foreground">{usuario?.email}</p>
            </div>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={logout}>Cerrar sesion</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  )
}
