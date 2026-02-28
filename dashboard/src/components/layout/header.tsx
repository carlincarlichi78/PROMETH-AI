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

export function Header() {
  const { usuario, logout } = useAuth()
  const { tema, setTema, toggleCopilot } = useUIStore()

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
        {/* Busqueda global — placeholder visual */}
        <Button
          variant="outline"
          size="sm"
          className="hidden md:flex gap-2 text-muted-foreground h-8 px-3"
        >
          <Search className="h-3.5 w-3.5" />
          <span className="text-xs">Buscar...</span>
          <kbd className="ml-1 rounded bg-muted px-1 py-0.5 text-[10px] font-mono">
            Ctrl+K
          </kbd>
        </Button>

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
