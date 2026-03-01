/** Tipo de consulta LEMA */
export enum TipoConsultaLema {
  PENDIENTES_NOTIFICACIONES = 'PENDIENTES_NOTIFICACIONES',
  PENDIENTES_COMUNICACIONES = 'PENDIENTES_COMUNICACIONES',
  HISTORICO_REALIZADAS = 'HISTORICO_REALIZADAS',
}

/** Estado de alta en DEHU/LEMA */
export enum EstadoAltaDehu {
  ALTA = 'ALTA',
  NO_ALTA = 'NO_ALTA',
  DESCONOCIDO = 'DESCONOCIDO',
}

/** Metodo utilizado para obtener notificaciones */
export enum MetodoConsulta {
  LEMA_API = 'LEMA_API',
  PUPPETEER = 'PUPPETEER',
}

/** Una notificacion extraida de DEHU */
export interface NotificacionDEHU {
  /** ID unico de la notificacion en DEHU (codigoOrigen) */
  idDehu: string
  tipo: 'Notificacion' | 'Comunicacion'
  titulo: string
  titular: string
  ambito: string
  organismo: string
  fechaDisposicion: string
  fechaCaducidad: string | null
  estado: string
  tipoEnvio?: string
  /** Ruta local del PDF descargado (null si no descargado) */
  rutaPdfLocal: string | null
}

/** Resultado de una consulta DEHU completa */
export interface ResultadoConsultaDEHU {
  exito: boolean
  metodo: MetodoConsulta
  certificadoSerial: string
  estadoAlta: EstadoAltaDehu
  notificaciones: NotificacionDEHU[]
  comunicaciones: NotificacionDEHU[]
  error?: string
  fechaConsulta: string
}

/** Configuracion DEHU por certificado */
export interface ConfigCertificadoDehu {
  certificadoSerial: string
  /** Ruta PFX — requerido para LEMA API, no para Puppeteer */
  rutaPfx?: string
  /** Password PFX — requerido para LEMA API, no para Puppeteer */
  passwordPfx?: string
  /** Si ya se verifico que tiene alta en LEMA */
  estadoAlta?: EstadoAltaDehu
  /** NIF personal del titular del certificado (ej: 37329873E) */
  titularNif?: string
  /** Nombre del titular */
  titularNombre?: string
  /** CIF de la empresa representada (ej: B93587418). Extraido de OID 2.5.4.97 */
  nifEmpresa?: string
  /** Thumbprint del certificado en almacen Windows */
  thumbprint?: string
  /** Timeout global personalizado */
  timeoutGlobal?: number
}

/** Resultado de sincronizacion con cloud */
export interface ResultadoSincronizacion {
  nuevas: number
  actualizadas: number
  errores: number
  detalle: Array<{
    idDehu: string
    accion: 'creada' | 'actualizada' | 'error'
    error?: string
  }>
}
