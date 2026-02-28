import { useState, useEffect } from 'react'
import { Bell, BellOff } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuLabel,
} from '@/components/ui/dropdown-menu'
import { Badge } from '@/components/ui/badge'
import {
  notificacionesSoportadas,
  suscribirNotificaciones,
} from './notificaciones-service'
import { useAuth } from '@/context/AuthContext'

interface Notificacion {
  id: string
  tipo: 'modelo_vence' | 'pipeline_error' | 'doc_procesado'
  titulo: string
  cuerpo: string
  leida: boolean
  fecha: Date
}

const NOTIF_DEMO: Notificacion[] = [
  {
    id: '1',
    tipo: 'modelo_vence',
    titulo: 'Modelo 303 vence en 3 dias',
    cuerpo: 'Plazo limite: 20 enero 2026',
    leida: false,
    fecha: new Date(),
  },
  {
    id: '2',
    tipo: 'doc_procesado',
    titulo: 'Documento procesado',
    cuerpo: 'Factura_enero.pdf procesada correctamente',
    leida: false,
    fecha: new Date(Date.now() - 3_600_000),
  },
]

function iconoTipo(tipo: Notificacion['tipo']): string {
  if (tipo === 'modelo_vence') return '📅'
  if (tipo === 'pipeline_error') return '⚠️'
  return '✅'
}

export function NotificacionesPanel() {
  const { token } = useAuth()
  const [notificaciones, setNotificaciones] = useState<Notificacion[]>(NOTIF_DEMO)
  const [permiso, setPermiso] = useState<NotificationPermission>('default')
  const soportadas = notificacionesSoportadas()

  useEffect(() => {
    if ('Notification' in window) setPermiso(Notification.permission)
  }, [])

  const noLeidas = notificaciones.filter(n => !n.leida).length

  const activarPush = async () => {
    if (!token) return
    await suscribirNotificaciones(token)
    if ('Notification' in window) setPermiso(Notification.permission)
  }

  const marcarLeida = (id: string) =>
    setNotificaciones(prev => prev.map(n => (n.id === id ? { ...n, leida: true } : n)))

  const marcarTodasLeidas = () =>
    setNotificaciones(prev => prev.map(n => ({ ...n, leida: true })))

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="relative h-8 w-8">
          <Bell className="h-4 w-4" />
          {noLeidas > 0 && (
            <Badge className="absolute -top-0.5 -right-0.5 h-4 w-4 p-0 flex items-center justify-center text-[10px] leading-none">
              {noLeidas}
            </Badge>
          )}
          <span className="sr-only">Notificaciones</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80">
        <DropdownMenuLabel className="flex items-center justify-between py-2">
          <span>Notificaciones</span>
          {noLeidas > 0 && (
            <Button
              variant="ghost"
              size="sm"
              className="h-auto p-0 text-xs text-muted-foreground hover:text-foreground"
              onClick={marcarTodasLeidas}
            >
              Marcar todas leidas
            </Button>
          )}
        </DropdownMenuLabel>
        <DropdownMenuSeparator />

        {notificaciones.length === 0 && (
          <div className="py-6 text-center text-sm text-muted-foreground">
            Sin notificaciones
          </div>
        )}

        {notificaciones.map(n => (
          <DropdownMenuItem
            key={n.id}
            className={`flex flex-col items-start gap-0.5 py-2 cursor-pointer ${n.leida ? 'opacity-60' : ''}`}
            onClick={() => marcarLeida(n.id)}
          >
            <div className="flex w-full items-center gap-2">
              <span className="text-base leading-none">{iconoTipo(n.tipo)}</span>
              <span className="flex-1 text-sm font-medium leading-tight">{n.titulo}</span>
              {!n.leida && (
                <span className="h-2 w-2 rounded-full bg-primary shrink-0" />
              )}
            </div>
            <p className="text-xs text-muted-foreground pl-6 leading-tight">{n.cuerpo}</p>
          </DropdownMenuItem>
        ))}

        {soportadas && permiso !== 'granted' && (
          <>
            <DropdownMenuSeparator />
            <div className="p-2">
              <Button
                size="sm"
                variant="outline"
                className="w-full gap-2"
                onClick={activarPush}
              >
                <Bell className="h-3 w-3" />
                Activar notificaciones push
              </Button>
            </div>
          </>
        )}

        {!soportadas && (
          <div className="px-2 pb-2 text-xs text-center text-muted-foreground flex items-center justify-center gap-1">
            <BellOff className="h-3 w-3" />
            Push no disponible en este navegador
          </div>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
