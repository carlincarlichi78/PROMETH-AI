/// <reference types="vite/client" />

interface CertsAPI {
  seleccionarArchivo: (password: string) => Promise<unknown>
  leerP12: (ruta: string, password: string) => Promise<unknown>
  listarLocales: () => Promise<string[]>
  instalarEnWindows: (rutaPfx: string, password: string) => Promise<unknown>
  desinstalarDeWindows: (thumbprint: string) => Promise<unknown>
  listarInstalados: () => Promise<unknown>
  activar: (numeroSerie: string) => Promise<unknown>
  desactivar: () => Promise<unknown>
  obtenerActivo: () => Promise<string | null>
  exportarPfx: (thumbprint: string, password: string) => Promise<unknown>
  sincronizarConCloud: (ruta: string, password: string, apiUrl: string, token: string) => Promise<unknown>
  aislar: (thumbprint: string) => Promise<unknown>
  restaurar: (thumbprint: string) => Promise<unknown>
  iniciarWatcher: (carpeta?: string) => Promise<unknown>
  detenerWatcher: () => Promise<unknown>
  obtenerCarpeta: () => Promise<string>
  onNuevoCertificado: (callback: (ruta: string) => void) => void
}

interface ScrapingAPI {
  obtenerEstado: () => Promise<unknown>
  configurar: (config: Record<string, unknown>) => Promise<unknown>
  obtenerConfig: () => Promise<unknown>
  iniciar: () => Promise<{ exito: boolean; error?: string }>
  detener: () => Promise<{ exito: boolean }>
  limpiar: () => Promise<{ exito: boolean }>
  onProgreso: (callback: (estado: unknown) => void) => void
}

interface DehuAPI {
  consultarNotificaciones: (config: unknown, apiUrl: string, token: string) => Promise<unknown>
  descargarNotificacion: (config: unknown, notificacion: unknown) => Promise<unknown>
  sincronizarCloud: (notificaciones: unknown[], certificadoId: string, apiUrl: string, token: string) => Promise<unknown>
  consultarYSincronizar: (configs: unknown[], apiUrl: string, token: string) => Promise<unknown>
  verificarAlta: (config: unknown) => Promise<unknown>
}

interface DocumentalesAPI {
  obtenerCatalogo: () => Promise<unknown[]>
  obtenerConfig: (certificadoSerial: string) => Promise<unknown>
  guardarConfig: (certificadoSerial: string, documentosActivos: string[], datosExtra?: Record<string, unknown>) => Promise<void>
  descargarDocumento: (tipo: string, certificadoSerial: string, datosExtra?: Record<string, unknown>) => Promise<unknown>
  descargarBatch: (configs: unknown[]) => Promise<{ exito: boolean; error?: string }>
  obtenerHistorial: (certificadoSerial?: string) => Promise<unknown[]>
  abrirCarpeta: (certificadoSerial?: string) => Promise<{ exito: boolean; error?: string }>
  limpiarHistorial: () => Promise<void>
}

interface NotificacionesDesktopAPI {
  obtenerConfigPortales: (certificadoSerial: string) => Promise<unknown>
  guardarConfigPortales: (certificadoSerial: string, portalesActivos: string[], datosPortal?: Record<string, unknown>) => Promise<void>
  obtenerPortalesDisponibles: () => Promise<string[]>
  consultarPortal: (portal: string, serialNumber: string, apiUrl: string, token: string, configDehu?: unknown) => Promise<unknown>
  consultarMultiPortal: (serialNumber: string, apiUrl: string, token: string, configDehu?: unknown) => Promise<unknown>
  consultarYSincronizarBatch: (configs: unknown[], apiUrl: string, token: string) => Promise<{ exito: boolean; error?: string }>
}

interface FirmaDesktopAPI {
  modosDisponibles: () => Promise<string[]>
  validarCertificado: (ruta: string, password: string) => Promise<unknown>
  firmarLocal: (opciones: unknown, certificadoSerial: string) => Promise<unknown>
  firmarAutoFirma: (opciones: unknown, certificadoSerial: string) => Promise<unknown>
  firmarBatch: (opciones: unknown) => Promise<unknown[]>
  obtenerHistorial: () => Promise<unknown>
  sincronizarCloud: (apiUrl: string, token: string, mapaCertificados?: Record<string, string>) => Promise<unknown>
  detectarAutoFirma: () => Promise<boolean>
  onProgreso: (callback: (progreso: unknown) => void) => void
}

interface WorkflowsDesktopAPI {
  listar: () => Promise<unknown[]>
  obtener: (id: string) => Promise<unknown>
  guardar: (workflow: unknown) => Promise<{ exito: boolean; error?: string }>
  eliminar: (id: string) => Promise<{ exito: boolean; error?: string }>
  duplicar: (id: string) => Promise<{ exito: boolean; workflow?: unknown; error?: string }>
  ejecutar: (id: string, contexto: Record<string, unknown>) => Promise<unknown>
  historial: (limite?: number) => Promise<unknown[]>
  limpiarHistorial: (mantener?: number) => Promise<{ exito: boolean; eliminadas: number }>
  categorias: () => Promise<string[]>
  obtenerSmtp: () => Promise<unknown>
  guardarSmtp: (config: unknown) => Promise<{ exito: boolean; error?: string }>
  procesarDisparador: (disparador: string, contexto: Record<string, unknown>) => Promise<{ exito: boolean }>
  onProgreso: (callback: (progreso: unknown) => void) => void
}

interface UpdaterAPI {
  checkNow: () => Promise<void>
  onChecking: (callback: () => void) => void
  onAvailable: (callback: (info: unknown) => void) => void
  onNotAvailable: (callback: () => void) => void
  onProgress: (callback: (progreso: unknown) => void) => void
  onDownloaded: (callback: (info: unknown) => void) => void
  onError: (callback: (error: string) => void) => void
}

interface TelemetriaAPI {
  optOut: () => Promise<void>
  optIn: () => Promise<void>
  estaActiva: () => Promise<boolean>
  estado: () => Promise<{ activa: boolean; eventosEnCola: number; ultimoEnvio: string | null }>
  registrar: (evento: string, propiedades?: Record<string, unknown>) => Promise<void>
}

interface ElectronAPI {
  readonly isDesktop: true
  getVersion: () => Promise<string>
  getPlatform: () => Promise<string>
  installUpdate: () => Promise<void>
  onUpdateAvailable: (callback: (version: string) => void) => void
  onUpdateDownloaded: (callback: (version: string) => void) => void
  updater: UpdaterAPI
  telemetria: TelemetriaAPI
  certs: CertsAPI
  scraping: ScrapingAPI
  dehu: DehuAPI
  documentales: DocumentalesAPI
  notificaciones: NotificacionesDesktopAPI
  firma: FirmaDesktopAPI
  workflows: WorkflowsDesktopAPI
}

interface Window {
  electronAPI?: ElectronAPI
}
