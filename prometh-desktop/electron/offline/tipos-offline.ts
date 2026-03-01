export interface EstadoOffline {
  conectado: boolean
  pendientes: number
  ultimaSync: {
    certificados: string | null
    notificaciones: string | null
    etiquetas: string | null
  }
}

export interface ResultadoSync {
  certificados: number
  notificaciones: number
  etiquetas: number
  errores: string[]
}

export interface CertificadoCache {
  id: string
  organizacionId: string
  nombreTitular: string
  dniCif: string
  numeroSerie: string | null
  emisor: string | null
  organizacion: string | null
  fechaExpedicion: string | null
  fechaVencimiento: string
  activo: number // SQLite no tiene boolean
  creadoEn: string
  actualizadoEn: string | null
  sincronizadoEn: string
  etiquetasJson: string // JSON stringified
}

export interface NotificacionCache {
  id: string
  organizacionId: string
  certificadoId: string
  administracion: string
  tipo: string | null
  estado: string
  contenido: string | null
  fechaDeteccion: string
  asignadoA: string | null
  notas: string | null
  urgencia: string | null
  categoria: string | null
  idExterno: string | null
  creadoEn: string
  sincronizadoEn: string
  pendientePush: number
}

export interface EtiquetaCache {
  id: string
  organizacionId: string
  nombre: string
  color: string
  sincronizadoEn: string
}

export interface CambioPendiente {
  id: number
  recurso: string
  recursoId: string
  operacion: string
  payloadJson: string
  intentos: number
  ultimoIntento: string | null
  creadoEn: string
  errorUltimo: string | null
}

export interface FiltrosCertificadosCache {
  busqueda?: string
  pagina?: number
  limite?: number
}

export interface FiltrosNotificacionesCache {
  busqueda?: string
  estado?: string
  urgencia?: string
  categoria?: string
  pagina?: number
  limite?: number
}
