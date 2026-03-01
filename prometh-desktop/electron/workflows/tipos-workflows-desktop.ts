/** Tipos de accion disponibles en desktop (complementan las del API) */
export type TipoAccionDesktop =
  | 'split_pdf'
  | 'send_mail'
  | 'protect_pdf'
  | 'send_to_repository'

/** Todos los tipos de accion (API + desktop) */
export type TipoAccionCompleta =
  | 'crear_tarea'
  | 'crear_recordatorio'
  | 'cambiar_etiqueta'
  | TipoAccionDesktop

/** Disparadores adicionales desktop (complementan los del API) */
export type DisparadorDesktop =
  | 'certificado_vence'
  | 'notificacion_recibida'
  | 'tarea_creada'
  | 'tarea_completada'
  | 'manual'
  | 'documento_descargado'
  | 'firma_completada'

// --- Configuracion de cada accion ---

/** Split PDF por NIF o por numero de paginas */
export interface ConfigSplitPdf {
  carpetaOrigen: string
  carpetaDestino: string
  /** 'nif' = dividir buscando NIF en cada pagina, 'paginas' = dividir cada N paginas */
  modoCorte: 'nif' | 'paginas'
  /** Numero de paginas por fragmento (solo si modoCorte === 'paginas') */
  numeroPaginas?: number
  /** Regex para identificar NIF en el PDF (default: patron NIF/NIE espanol) */
  nifRegex?: string
  /** Nombre archivo destino con templates: {nif}, {fecha}, {original}, {indice} */
  nombreArchivoDestino?: string
}

/** Enviar email con adjuntos via SMTP */
export interface ConfigSendMail {
  /** Direccion remitente */
  emailOrigen: string
  /** Direccion(es) destinatario (separadas por ;) */
  emailDestino: string
  asunto: string
  cuerpo: string
  /** Ruta carpeta con archivos a adjuntar */
  carpetaAdjuntos?: string
  /** Extensiones a adjuntar (ej: ['.pdf', '.xlsx']). Todas si vacio */
  extensiones?: string[]
  /** Config SMTP */
  smtpHost: string
  smtpPort: number
  smtpUser: string
  smtpPass: string
  smtpSecure: boolean
}

/** Proteger PDF con password */
export interface ConfigProtectPdf {
  carpetaOrigen: string
  carpetaDestino: string
  /** 'maestra' = misma password para todos, 'cliente' = usa NIF como password */
  modoPassword: 'maestra' | 'cliente'
  /** Password fija (solo si modoPassword === 'maestra') */
  passwordMaestra?: string
  /** Regex para extraer NIF del nombre de archivo (solo si modoPassword === 'cliente') */
  nifRegexArchivo?: string
}

/** Organizar archivos en estructura de carpetas */
export interface ConfigSendToRepository {
  /** Ruta raiz del repositorio */
  repositorioRaiz: string
  /** Estructura de carpetas con templates: {nif}, {fecha}, {modelo}, {tipo}, {anio} */
  estructuraCarpetas: string
  /** Si true, sobreescribe archivos existentes */
  sobreescribir?: boolean
  /** Carpeta origen de los archivos a organizar */
  carpetaOrigen: string
}

/** Union de configs de accion */
export type ConfigAccionDesktop =
  | ConfigSplitPdf
  | ConfigSendMail
  | ConfigProtectPdf
  | ConfigSendToRepository

// --- Accion y Workflow desktop ---

/** Accion de un workflow desktop */
export interface AccionWorkflowDesktop {
  tipo: TipoAccionDesktop
  config: ConfigAccionDesktop
}

/** Condicion de workflow (reutiliza del API) */
export interface CondicionWorkflowDesktop {
  campo: string
  operador: 'igual' | 'distinto' | 'contiene' | 'no_contiene' | 'mayor_que' | 'menor_que' | 'mayor_igual' | 'menor_igual'
  valor: string | number | boolean
}

/** Workflow desktop completo */
export interface WorkflowDesktop {
  id: string
  nombre: string
  descripcion: string
  activo: boolean
  disparador: DisparadorDesktop
  condiciones: CondicionWorkflowDesktop[]
  acciones: AccionWorkflowDesktop[]
  /** Si es un workflow predefinido (no editable) */
  predefinido: boolean
  /** Categoria para agrupar en UI */
  categoria: string
  creadoEn: string
  actualizadoEn: string
}

// --- Contexto de ejecucion ---

/** Contexto que se pasa al motor al ejecutar un workflow */
export interface ContextoEjecucionDesktop {
  /** Carpeta temporal de trabajo para esta ejecucion */
  carpetaTrabajo: string
  /** NIF/CIF del certificado activo */
  nif?: string
  /** Serial del certificado activo */
  certificadoSerial?: string
  /** Ruta del archivo que disparo el workflow */
  archivoOrigen?: string
  /** Modelo tributario (130, 180, etc.) */
  modelo?: string
  /** Anio fiscal */
  anio?: string
  /** Datos extra del disparador */
  [clave: string]: unknown
}

/** Resultado de una accion individual */
export interface ResultadoAccionDesktop {
  tipo: TipoAccionDesktop
  exito: boolean
  mensaje: string
  /** Archivos generados/modificados por esta accion */
  archivosResultado?: string[]
  /** Datos extra para el contexto de la siguiente accion (pipeline) */
  datosExtra?: Record<string, unknown>
  tiempoMs: number
}

/** Resultado de ejecutar un workflow completo */
export interface ResultadoWorkflowDesktop {
  workflowId: string
  exito: boolean
  acciones: ResultadoAccionDesktop[]
  tiempoTotalMs: number
  error?: string
}

/** Registro de ejecucion para historial local */
export interface EjecucionWorkflowLocal {
  id: string
  workflowId: string
  workflowNombre: string
  resultado: 'exito' | 'error'
  detalles: ResultadoWorkflowDesktop
  ejecutadoEn: string
}

/** Estructura del archivo JSON de historial */
export interface HistorialWorkflowsLocal {
  ejecuciones: EjecucionWorkflowLocal[]
  workflowsPersonalizados: WorkflowDesktop[]
  /** Config SMTP global para acciones de email */
  configSmtp?: ConfigSmtpGlobal
}

/** Config SMTP global reutilizable */
export interface ConfigSmtpGlobal {
  host: string
  port: number
  user: string
  pass: string
  secure: boolean
}

/** Progreso de ejecucion emitido via IPC */
export interface ProgresoWorkflowDesktop {
  workflowId: string
  workflowNombre: string
  totalAcciones: number
  accionActual: number
  accionNombre: string
  estado: 'ejecutando' | 'completado' | 'error'
  porcentaje: number
}
