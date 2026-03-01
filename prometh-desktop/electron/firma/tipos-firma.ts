/** Modo de firma disponible en desktop */
export type ModoFirma = 'local' | 'autofirma'

/** Opciones de stamp visual para firma */
export interface OpcionesStampLocal {
  nombreFirmante: string
  razon?: string
  logoBase64?: string
  colorHex?: string
  posicion?: 'inferior-derecha' | 'inferior-izquierda' | 'superior-derecha' | 'superior-izquierda'
}

/** Opciones para firma PAdES local con P12/PFX */
export interface OpcionesFirmaLocal {
  /** Ruta absoluta al PDF a firmar */
  rutaPdf: string
  /** Ruta absoluta al certificado P12/PFX */
  rutaCertificado: string
  /** Password del P12 en texto plano */
  passwordCertificado: string
  /** Motivo de la firma (default: "Firmado digitalmente con CertiGestor") */
  razon?: string
  /** Ubicacion del firmante (default: "ES") */
  ubicacion?: string
  /** Ruta de salida del PDF firmado (default: original + "-firmado") */
  rutaSalida?: string
  /** Activar stamp visual en primera pagina */
  firmaVisible?: boolean
  /** Opciones del stamp visual */
  opcionesStamp?: OpcionesStampLocal
}

/** Opciones para firma via AutoFirma (protocolo afirma://) */
export interface OpcionesFirmaAutoFirma {
  /** Ruta absoluta al PDF a firmar */
  rutaPdf: string
  /** Thumbprint del certificado en almacen Windows */
  thumbprint: string
  /** Ruta de salida del PDF firmado */
  rutaSalida?: string
}

/** Resultado de una operacion de firma */
export interface ResultadoFirma {
  exito: boolean
  modo: ModoFirma
  /** Ruta al PDF firmado si exito */
  rutaPdfFirmado?: string
  /** Mensaje de error si fallo */
  error?: string
  /** Tiempo total en milisegundos */
  tiempoMs?: number
}

/** Documento firmado almacenado en historial local */
export interface DocumentoFirmadoLocal {
  /** UUID generado localmente */
  id: string
  rutaPdfOriginal: string
  rutaPdfFirmado: string
  /** Serial del certificado usado */
  certificadoSerial: string
  modo: ModoFirma
  /** Fecha ISO de la firma */
  fechaFirma: string
  razon: string
  /** Si ya se sincronizo con la API cloud */
  sincronizadoCloud: boolean
}

/** Estructura del archivo JSON de historial de firmas */
export interface HistorialFirmasLocal {
  documentos: DocumentoFirmadoLocal[]
}

/** Resultado de sincronizacion de firmas con cloud */
export interface ResultadoSincFirma {
  sincronizados: number
  errores: number
}

/** Opciones para firma batch */
export interface OpcionesFirmaBatch {
  rutasPdf: string[]
  rutaCertificado: string
  passwordCertificado: string
  certificadoSerial: string
  modo: ModoFirma
  /** Thumbprint (requerido solo si modo === 'autofirma') */
  thumbprint?: string
  razon?: string
  ubicacion?: string
  /** Activar stamp visual en primera pagina */
  firmaVisible?: boolean
  /** Opciones del stamp visual */
  opcionesStamp?: OpcionesStampLocal
}

/** Progreso de firma batch emitido via IPC */
export interface ProgresoFirmaBatch {
  total: number
  completados: number
  actual: string
  errores: number
}
