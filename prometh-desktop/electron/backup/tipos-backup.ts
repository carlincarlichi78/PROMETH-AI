/** Secciones disponibles para backup */
export type SeccionBackup =
  | 'scheduler'
  | 'tray_config'
  | 'workflows'
  | 'config_portales'
  | 'config_docs'
  | 'historial_docs'

/** Descripcion de cada seccion para la UI */
export const DESCRIPCIONES_SECCIONES: Record<SeccionBackup, string> = {
  scheduler: 'Tareas programadas del scheduler',
  tray_config: 'Configuración de alertas desktop',
  workflows: 'Workflows personalizados y config SMTP',
  config_portales: 'Configuración de portales de notificaciones',
  config_docs: 'Configuración de documentos por certificado',
  historial_docs: 'Historial de descargas documentales',
}

export interface OpcionesExportar {
  secciones: SeccionBackup[]
  password: string
}

export interface OpcionesImportar {
  password: string
}

export interface DatosBackup {
  version: 1
  fecha: string
  secciones: Partial<Record<SeccionBackup, unknown>>
}

export interface ResultadoImportar {
  exito: boolean
  seccionesImportadas: SeccionBackup[]
  error?: string
}

export interface ResultadoExportar {
  exito: boolean
  ruta?: string
  error?: string
}

export interface PreviewBackup {
  exito: boolean
  secciones?: SeccionBackup[]
  fecha?: string
  version?: number
  error?: string
}
