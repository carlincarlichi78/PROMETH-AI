/** Tipo de documento descargable de administraciones publicas */
export enum TipoDocumento {
  // AEAT
  DEUDAS_AEAT = 'DEUDAS_AEAT',
  DATOS_FISCALES = 'DATOS_FISCALES',
  CERTIFICADOS_IRPF = 'CERTIFICADOS_IRPF',
  CNAE_AUTONOMO = 'CNAE_AUTONOMO',
  IAE_ACTIVIDADES = 'IAE_ACTIVIDADES',
  // Seguridad Social
  DEUDAS_SS = 'DEUDAS_SS',
  VIDA_LABORAL = 'VIDA_LABORAL',
  CERTIFICADO_INSS = 'CERTIFICADO_INSS',
  // Carpeta Ciudadana
  CONSULTA_VEHICULOS = 'CONSULTA_VEHICULOS',
  CONSULTA_INMUEBLES = 'CONSULTA_INMUEBLES',
  EMPADRONAMIENTO = 'EMPADRONAMIENTO',
  CERTIFICADO_PENALES = 'CERTIFICADO_PENALES',
  // Justicia
  CERTIFICADO_NACIMIENTO = 'CERTIFICADO_NACIMIENTO',
  APUD_ACTA = 'APUD_ACTA',
  // Otros
  CERTIFICADO_SEPE = 'CERTIFICADO_SEPE',
  SOLICITUD_CIRBE = 'SOLICITUD_CIRBE',
  OBTENCION_CIRBE = 'OBTENCION_CIRBE',
  // Hacienda (consulta deudas)
  DEUDAS_HACIENDA = 'DEUDAS_HACIENDA',
  // Justicia — Registro Civil
  CERTIFICADO_MATRIMONIO = 'CERTIFICADO_MATRIMONIO',
  // Licitaciones
  PROC_ABIERTOS_GENERAL = 'PROC_ABIERTOS_GENERAL',
  PROC_ABIERTOS_MADRID = 'PROC_ABIERTOS_MADRID',
  PROC_ABIERTOS_ANDALUCIA = 'PROC_ABIERTOS_ANDALUCIA',
  PROC_ABIERTOS_VALENCIA = 'PROC_ABIERTOS_VALENCIA',
  PROC_ABIERTOS_CATALUNYA = 'PROC_ABIERTOS_CATALUNYA',
}

/** Portal de origen (agrupa scrapers que comparten login) */
export enum Portal {
  AEAT = 'AEAT',
  SEGURIDAD_SOCIAL = 'SEGURIDAD_SOCIAL',
  CARPETA_CIUDADANA = 'CARPETA_CIUDADANA',
  JUSTICIA = 'JUSTICIA',
  SEPE = 'SEPE',
  BANCO_ESPANA = 'BANCO_ESPANA',
  LICITACIONES = 'LICITACIONES',
}

/** Estado de verificacion del scraper (mantenido manualmente) */
export enum EstadoVerificacion {
  /** Probado y funciona correctamente */
  VERIFICADO = 'VERIFICADO',
  /** Probado y no funciona (portal cambio, scraper roto, etc.) */
  NO_FUNCIONA = 'NO_FUNCIONA',
  /** No se ha probado todavia */
  NO_PROBADO = 'NO_PROBADO',
}

/** Metodo de obtencion del documento */
export enum MetodoDescarga {
  /** Descarga directa de PDF via will-download */
  DESCARGA_DIRECTA = 'DESCARGA_DIRECTA',
  /** Genera PDF via webContents.printToPDF */
  PRINT_TO_PDF = 'PRINT_TO_PDF',
  /** Combina ambos metodos */
  MIXTO = 'MIXTO',
}

/** Definicion estatica de un documento descargable */
export interface DefinicionDocumento {
  id: TipoDocumento
  nombre: string
  descripcion: string
  portal: Portal
  url: string
  nombreArchivo: string
  metodo: MetodoDescarga
  /** Activo por defecto al agregar un certificado */
  activoPorDefecto: boolean
  /** Genera multiples archivos (ej: DatosFiscales x3 anios) */
  multiArchivo: boolean
  /** Requiere intervencion del usuario */
  semiAutomatico: boolean
  /** Estado de verificacion del scraper */
  estadoVerificacion: EstadoVerificacion
  /** Nota sobre el estado (por que no funciona, requisitos, etc.) */
  notaVerificacion?: string
}

/** Config de documentos activos por certificado */
export interface ConfigDocumentosCertificado {
  certificadoSerial: string
  /** Solo necesario para operaciones que requieran firma PFX (no usado en scrapers documentales) */
  rutaPfx?: string
  passwordPfx?: string
  documentosActivos: TipoDocumento[]
  datosExtra?: Record<string, unknown>
}

/** Resultado de una descarga individual */
export interface ResultadoDescarga {
  tipo: TipoDocumento
  exito: boolean
  rutasArchivos: string[]
  error?: string
  fechaDescarga: string
  duracionMs: number
}

/** Registro de historial de descargas */
export interface RegistroHistorialDescarga {
  certificadoSerial: string
  tipo: TipoDocumento
  exito: boolean
  rutasArchivos: string[]
  fechaDescarga: string
  error?: string
  sincronizadoCloud?: boolean
}

/** Config local de documentos para un certificado (persistida en JSON) */
export interface ConfigDocumentosLocal {
  [certificadoSerial: string]: {
    documentosActivos: TipoDocumento[]
    datosExtra?: Record<string, unknown>
  }
}
