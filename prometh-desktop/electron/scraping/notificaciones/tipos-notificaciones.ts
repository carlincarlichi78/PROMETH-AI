/** Portales de notificaciones electronicas soportados */
export enum PortalNotificaciones {
  DEHU = 'DEHU',
  DGT = 'DGT',
  E_NOTUM = 'E_NOTUM',
  JUNTA_ANDALUCIA = 'JUNTA_ANDALUCIA',
  AEAT_DIRECTA = 'AEAT_DIRECTA',
  SEGURIDAD_SOCIAL = 'SEGURIDAD_SOCIAL',
}

/** Estado de autenticacion en un portal */
export enum EstadoAutenticacion {
  AUTENTICADO = 'AUTENTICADO',
  NO_AUTENTICADO = 'NO_AUTENTICADO',
  ERROR = 'ERROR',
}

/** Una notificacion generica de cualquier portal */
export interface NotificacionPortal {
  /** ID unico: `${portal}-${serialNumber}-${idInterno}` */
  idExterno: string
  portal: PortalNotificaciones
  tipo: 'Notificacion' | 'Comunicacion' | 'Aviso'
  titulo: string
  organismo: string
  fechaDisposicion: string
  fechaCaducidad: string | null
  estado: string
  /** URL del detalle en el portal original */
  urlDetalle?: string
  /** Ruta local del PDF si fue descargado */
  rutaPdfLocal: string | null
  /** Texto extraido del PDF via pdf-parse o OCR */
  contenidoExtraido?: string | null
}

/** Resultado de consultar un portal concreto */
export interface ResultadoConsultaPortal {
  exito: boolean
  portal: PortalNotificaciones
  certificadoSerial: string
  estadoAutenticacion: EstadoAutenticacion
  notificaciones: NotificacionPortal[]
  error?: string
  fechaConsulta: string
}

/** Resultado de consulta multi-portal (N portales x 1 certificado) */
export interface ResultadoConsultaMultiPortal {
  certificadoSerial: string
  portalesConsultados: PortalNotificaciones[]
  resultados: ResultadoConsultaPortal[]
  totalNotificaciones: number
  portalesConError: PortalNotificaciones[]
  fechaConsulta: string
}

/** Config de portales activos para un certificado */
export interface ConfigPortalesCertificado {
  portalesActivos: PortalNotificaciones[]
  /** Datos adicionales por portal (ej: NIF para DGT, provincia para Junta) */
  datosPortal?: Partial<Record<PortalNotificaciones, Record<string, unknown>>>
}

/** Mapa serializado en JSON: serialNumber → ConfigPortalesCertificado */
export interface ConfigPortalesLocal {
  [certificadoSerial: string]: ConfigPortalesCertificado
}

/** Resultado de sincronizacion cloud multi-portal */
export interface ResultadoSincronizacionPortal {
  portal: PortalNotificaciones
  nuevas: number
  actualizadas: number
  errores: number
}
