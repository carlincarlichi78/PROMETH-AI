/** Tipo de proceso en la cola */
export enum ProcessType {
  NOTIFICATION_CHECK = 'NOTIFICATION_CHECK',
  DOCUMENT_DOWNLOAD = 'DOCUMENT_DOWNLOAD',
  DATA_SCRAPING = 'DATA_SCRAPING',
}

/** Estado de la factory (gestor global) */
export enum FactoryStatus {
  IDLE = 'IDLE',
  RUNNING = 'RUNNING',
}

/** Estado de una cadena de bloques */
export enum ChainStatus {
  IDLE = 'IDLE',
  RUNNING = 'RUNNING',
  COMPLETED = 'COMPLETED',
  FAILED = 'FAILED',
  PARTIALLY_COMPLETED = 'PARTIALLY_COMPLETED',
}

/** Estado de un bloque individual */
export enum BlockStatus {
  PENDING = 'PENDING',
  RUNNING = 'RUNNING',
  COMPLETED = 'COMPLETED',
  FAILED = 'FAILED',
}

/** Resultado de una operacion de scraping */
export interface ResultadoScraping {
  exito: boolean
  datos?: unknown
  error?: string
  rutaDescarga?: string
}

/** Configuracion global de scraping */
export interface ConfigScraping {
  headless: boolean
  timeoutElemento: number
  timeoutGlobal: number
  maxReintentos: number
  fastMode: boolean
  replicas: number
  carpetaDescargas: string
  /** Nombre legible para la subcarpeta de descargas (ej: "GARCIA_LOPEZ_MARIA_12345678A") */
  nombreCarpeta?: string
}

/** Estado serializable de la cola para IPC */
export interface EstadoCola {
  status: FactoryStatus
  totalCadenas: number
  cadenaActual: number
  bloqueActual: number
  totalBloques: number
  progreso: number // 0-100
  cadenas: EstadoCadena[]
}

/** Estado serializable de una cadena */
export interface EstadoCadena {
  id: string
  estado: ChainStatus
  certificadoSerial: string
  nombreCert?: string
  totalBloques: number
  bloquesCompletados: number
  bloques?: InfoBloque[]
}

/** Info de un bloque para progreso */
export interface InfoBloque {
  id: string
  tipo: ProcessType
  estado: BlockStatus
  descripcion: string
}

/** Configuracion por defecto */
export const CONFIG_DEFAULT: ConfigScraping = {
  headless: true,
  timeoutElemento: 30_000,
  timeoutGlobal: 120_000,
  maxReintentos: 3,
  fastMode: false,
  replicas: 3,
  carpetaDescargas: '',
}
