/** Tipo de tarea programable */
export type TipoTareaProgramada =
  | 'scraping'
  | 'workflow'
  | 'sync_cloud'
  | 'descarga_docs'
  | 'consulta_notif'

/** Frecuencia de ejecucion */
export type FrecuenciaScheduler =
  | 'cada_hora'
  | 'cada_2_horas'
  | 'cada_4_horas'
  | 'cada_6_horas'
  | 'cada_12_horas'
  | 'diaria'
  | 'semanal'
  | 'personalizada'

/** Dia de la semana para frecuencia semanal */
export type DiaSemana =
  | 'lunes'
  | 'martes'
  | 'miercoles'
  | 'jueves'
  | 'viernes'
  | 'sabado'
  | 'domingo'

/** Parametros especificos por tipo de tarea */
export interface ParametrosScraping {
  tipo: 'scraping'
  certificadoSerial: string
}

export interface ParametrosWorkflow {
  tipo: 'workflow'
  workflowId: string
  contexto?: Record<string, unknown>
}

export interface ParametrosSyncCloud {
  tipo: 'sync_cloud'
  sincronizar: ('firmas' | 'notificaciones')[]
  apiUrl: string
  token?: string
}

export interface ParametrosDescargaDocs {
  tipo: 'descarga_docs'
  certificadoSerial: string
}

export interface ParametrosConsultaNotif {
  tipo: 'consulta_notif'
  certificadoSerial: string
  apiUrl: string
  token?: string
}

export type ParametrosTarea =
  | ParametrosScraping
  | ParametrosWorkflow
  | ParametrosSyncCloud
  | ParametrosDescargaDocs
  | ParametrosConsultaNotif

/** Tarea programada individual */
export interface TareaProgramada {
  id: string
  nombre: string
  tipo: TipoTareaProgramada
  activa: boolean
  frecuencia: FrecuenciaScheduler
  /** HH:mm (hora del dia para ejecucion) */
  horaEjecucion: string
  /** Solo para frecuencia 'semanal' */
  diaSemana?: DiaSemana
  /** Solo para frecuencia 'personalizada': intervalo en minutos */
  intervaloMinutos?: number
  parametros: ParametrosTarea
  ultimaEjecucion?: string
  proximaEjecucion?: string
  ultimoResultado?: 'exito' | 'error' | 'parcial'
  creadoEn: string
  actualizadoEn: string
}

/** Registro de ejecucion del scheduler */
export interface EjecucionScheduler {
  id: string
  tareaId: string
  tareaNombre: string
  tipo: TipoTareaProgramada
  resultado: 'exito' | 'error' | 'parcial'
  mensaje: string
  ejecutadoEn: string
  duracionMs: number
}

/** Estructura del archivo JSON de persistencia */
export interface DatosScheduler {
  tareas: TareaProgramada[]
  ejecuciones: EjecucionScheduler[]
}

/** Estado del scheduler para IPC */
export interface EstadoScheduler {
  activo: boolean
  tareasActivas: number
  proximaEjecucion?: string
  ejecutandoAhora?: string
}
