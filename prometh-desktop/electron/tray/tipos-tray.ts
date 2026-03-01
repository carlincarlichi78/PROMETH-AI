/** Tipo de notificacion desktop */
export type TipoNotificacionDesktop =
  | 'certificado_caduca'
  | 'scraping_completado'
  | 'scraping_error'
  | 'workflow_completado'
  | 'workflow_error'
  | 'sync_completada'
  | 'descarga_completada'
  | 'tarea_scheduler'

/** Prioridad de notificacion */
export type PrioridadNotificacion = 'alta' | 'media' | 'baja'

/** Notificacion pendiente */
export interface NotificacionDesktop {
  id: string
  tipo: TipoNotificacionDesktop
  titulo: string
  mensaje: string
  prioridad: PrioridadNotificacion
  leida: boolean
  fechaCreacion: string
  datosExtra?: Record<string, unknown>
}

/** Config de notificaciones desktop */
export interface ConfigNotificacionesDesktop {
  nativasActivas: boolean
  diasAvisoCaducidad: number
  notificarScraping: boolean
  notificarWorkflows: boolean
  notificarSync: boolean
  sonido: boolean
}

/** Estructura JSON persistida */
export interface DatosNotificacionesDesktop {
  notificaciones: NotificacionDesktop[]
  config: ConfigNotificacionesDesktop
}

/** Estado para badge del tray */
export interface EstadoTray {
  pendientes: number
  ultimaNotificacion?: string
}
