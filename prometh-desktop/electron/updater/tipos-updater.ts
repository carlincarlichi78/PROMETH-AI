/** Informacion de una actualizacion disponible */
export interface InfoActualizacion {
  version: string
  fechaPublicacion: string
  notasCambios?: string
}

/** Progreso de descarga de actualizacion */
export interface ProgresoDescarga {
  porcentaje: number
  bytesTransferidos: number
  bytesTotal: number
  velocidadBps: number
}

/** Estado del updater */
export type EstadoUpdater =
  | 'inactivo'
  | 'verificando'
  | 'disponible'
  | 'descargando'
  | 'descargado'
  | 'error'
