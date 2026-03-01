/** Datos extraidos de un certificado P12/PFX local */
export interface CertificadoLocal {
  ruta: string
  nombreTitular: string
  dniCif: string
  emisor: string | null
  organizacion: string | null
  numeroSerie: string | null
  fechaExpedicion: string | null // ISO string
  fechaVencimiento: string // ISO string
  instaladoEnWindows: boolean
}

/** Certificado listado del almacen de Windows */
export interface CertInstaladoWindows {
  thumbprint: string
  subject: string
  emisor: string
  fechaVencimiento: string // ISO string
  numeroSerie: string
}

/** Resultado generico de operacion */
export interface ResultadoOperacion {
  exito: boolean
  error?: string
}

/** Configuracion del watcher de carpeta */
export interface ConfigWatcher {
  carpeta: string
  activo: boolean
}
