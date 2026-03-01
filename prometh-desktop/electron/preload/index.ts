import { contextBridge, ipcRenderer } from 'electron'

export interface CertsAPI {
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
  sincronizarDesdeCloud: (apiUrl: string, token: string) => Promise<{
    instalados: string[]
    yaExistentes: number
    errores: Array<{ id: string; error: string }>
  }>
  aislar: (thumbprint: string) => Promise<unknown>
  restaurar: (thumbprint: string) => Promise<unknown>
  iniciarWatcher: (carpeta?: string) => Promise<unknown>
  detenerWatcher: () => Promise<unknown>
  obtenerCarpeta: () => Promise<string>
  onNuevoCertificado: (callback: (ruta: string) => void) => void
}

export interface ScrapingAPI {
  obtenerEstado: () => Promise<unknown>
  configurar: (config: Record<string, unknown>) => Promise<unknown>
  obtenerConfig: () => Promise<unknown>
  iniciar: () => Promise<{ exito: boolean; error?: string }>
  detener: () => Promise<{ exito: boolean }>
  limpiar: () => Promise<{ exito: boolean }>
  onProgreso: (callback: (estado: unknown) => void) => void
  onNotificacionesNuevas: (callback: (datos: { portal: string; nuevas: number }) => void) => void
}

export interface DehuAPI {
  consultarNotificaciones: (config: unknown, apiUrl: string, token: string) => Promise<unknown>
  descargarNotificacion: (config: unknown, notificacion: unknown) => Promise<unknown>
  sincronizarCloud: (notificaciones: unknown[], certificadoId: string, apiUrl: string, token: string) => Promise<unknown>
  consultarYSincronizar: (configs: unknown[], apiUrl: string, token: string) => Promise<unknown>
  verificarAlta: (config: unknown) => Promise<unknown>
  verificarPdfDescargado: (idDehu: string, certificadoSerial: string) => Promise<{ descargado: boolean; rutaLocal?: string }>
  verificarPdfsBatch: (items: Array<{ idDehu: string; certificadoSerial: string }>) => Promise<Record<string, { descargado: boolean; rutaLocal?: string }>>
  abrirPdf: (rutaLocal: string) => Promise<{ exito: boolean; error?: string }>
  descargarPdfBatch: (config: unknown, notificaciones: unknown[]) => Promise<{ exitosos: number; errores: number; resultados: Array<{ idDehu: string; exito: boolean; error?: string }> }>
  onProgresoBatch: (callback: (progreso: { actual: number; total: number; idDehu: string }) => void) => void
}

export interface DocumentalesAPI {
  obtenerCatalogo: () => Promise<unknown[]>
  obtenerConfig: (certificadoSerial: string) => Promise<unknown>
  guardarConfig: (certificadoSerial: string, documentosActivos: string[], datosExtra?: Record<string, unknown>) => Promise<void>
  descargarDocumento: (tipo: string, certificadoSerial: string, datosExtra?: Record<string, unknown>) => Promise<unknown>
  descargarBatch: (configs: unknown[]) => Promise<{ exito: boolean; error?: string }>
  obtenerHistorial: (certificadoSerial?: string) => Promise<unknown[]>
  abrirCarpeta: (certificadoSerial?: string) => Promise<{ exito: boolean; error?: string }>
  limpiarHistorial: () => Promise<void>
  listarArchivos: (serialNumber: string) => Promise<{ nombre: string; ruta: string; fecha: string; tamano: number }[]>
  eliminarArchivo: (ruta: string) => Promise<{ exito: boolean; error?: string }>
  limpiarDebug: (serialNumber: string) => Promise<{ exito: boolean; eliminados: number }>
  estadisticasCarpeta: (serialNumber: string) => Promise<{ totalArchivos: number; tamanoTotal: number; debugCount: number }>
  abrirArchivo: (ruta: string) => Promise<{ exito: boolean; error?: string }>
  ultimosResultados: (certificadoSerial?: string) => Promise<Record<string, { exito: boolean; fecha: string; error?: string }>>
  sincronizarCloud: (apiUrl: string, token: string) => Promise<{ sincronizados: number; errores: number }>
  sincronizarConfigCloud: (apiUrl: string, token: string) => Promise<{ sincronizados: number; errores: number }>
  recuperarConfigCloud: (apiUrl: string, token: string) => Promise<{ recuperados: number }>
}

export interface NotificacionesAPI {
  obtenerConfigPortales: (certificadoSerial: string) => Promise<unknown>
  guardarConfigPortales: (
    certificadoSerial: string,
    portalesActivos: string[],
    datosPortal?: Record<string, unknown>,
  ) => Promise<void>
  obtenerPortalesDisponibles: () => Promise<string[]>
  consultarPortal: (
    portal: string,
    serialNumber: string,
    apiUrl: string,
    token: string,
    configDehu?: unknown,
  ) => Promise<unknown>
  consultarMultiPortal: (
    serialNumber: string,
    apiUrl: string,
    token: string,
    configDehu?: unknown,
  ) => Promise<unknown>
  consultarYSincronizarBatch: (
    configs: unknown[],
    apiUrl: string,
    token: string,
  ) => Promise<{ exito: boolean; error?: string }>
  descargarPdf: (
    idExterno: string,
    portal: string,
    configDehu?: unknown,
    estadoNotificacion?: string,
    titularNotificacion?: string,
  ) => Promise<{ exito: boolean; rutaLocal?: string; error?: string }>
}

export interface FirmaAPI {
  modosDisponibles: () => Promise<string[]>
  validarCertificado: (ruta: string, password: string) => Promise<unknown>
  firmarLocal: (opciones: unknown, certificadoSerial: string) => Promise<unknown>
  firmarAutoFirma: (opciones: unknown, certificadoSerial: string) => Promise<unknown>
  firmarBatch: (opciones: unknown) => Promise<unknown[]>
  obtenerHistorial: () => Promise<unknown>
  sincronizarCloud: (
    apiUrl: string,
    token: string,
    mapaCertificados?: Record<string, string>,
  ) => Promise<unknown>
  detectarAutoFirma: () => Promise<boolean>
  onProgreso: (callback: (progreso: unknown) => void) => void
}

export interface WorkflowsDesktopAPI {
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

export interface SchedulerDesktopAPI {
  obtenerEstado: () => Promise<unknown>
  listarTareas: () => Promise<unknown[]>
  obtenerTarea: (id: string) => Promise<unknown>
  crearTarea: (datos: Record<string, unknown>) => Promise<{ exito: boolean; tarea?: unknown; error?: string }>
  actualizarTarea: (id: string, datos: Record<string, unknown>) => Promise<{ exito: boolean; error?: string }>
  eliminarTarea: (id: string) => Promise<{ exito: boolean; error?: string }>
  toggleTarea: (id: string) => Promise<{ exito: boolean; activa?: boolean; error?: string }>
  ejecutarAhora: (id: string) => Promise<{ exito: boolean; error?: string }>
  historial: (limite?: number) => Promise<unknown[]>
  limpiarHistorial: (mantener?: number) => Promise<{ exito: boolean; eliminadas: number }>
  onProgreso: (callback: (estado: unknown) => void) => void
}

export interface TrayDesktopAPI {
  obtenerEstado: () => Promise<unknown>
  listarNotificaciones: (limite?: number) => Promise<unknown[]>
  marcarLeida: (id: string) => Promise<{ exito: boolean }>
  marcarTodasLeidas: () => Promise<{ exito: boolean; marcadas: number }>
  obtenerConfig: () => Promise<unknown>
  guardarConfig: (config: Record<string, unknown>) => Promise<{ exito: boolean }>
  limpiarAntiguas: (mantener?: number) => Promise<{ exito: boolean; eliminadas: number }>
  ejecutarChequeo: () => Promise<{ exito: boolean; nuevas: number }>
  onNuevaNotificacion: (callback: (notificacion: unknown) => void) => void
}

export interface AnalyticsDesktopAPI {
  metricas: () => Promise<unknown>
  metricasCerts: () => Promise<unknown>
  actividadTemporal: (dias?: number) => Promise<unknown[]>
}

export interface BackupDesktopAPI {
  exportar: (opciones: { secciones: string[]; password: string }) => Promise<{ exito: boolean; ruta?: string; error?: string }>
  importar: (opciones: { password: string }) => Promise<{ exito: boolean; seccionesImportadas: string[]; error?: string }>
  previsualizar: (opciones: { password: string }) => Promise<{ exito: boolean; secciones?: string[]; fecha?: string; version?: number; error?: string }>
}

export interface OcrAPI {
  extraerTexto: (rutaPdf: string) => Promise<string | null>
  estado: () => Promise<{ activo: boolean; idioma: string }>
}

export interface MultiCertAPI {
  iniciar: (configs: unknown[], apiUrl: string, token: string) => Promise<{ exito: boolean; error?: string }>
  detener: () => Promise<{ exito: boolean }>
  obtenerEstado: () => Promise<unknown>
  obtenerHistorial: (limite?: number) => Promise<unknown[]>
  limpiarHistorial: () => Promise<{ exito: boolean }>
}

export interface UpdaterAPI {
  checkNow: () => Promise<void>
  onChecking: (callback: () => void) => void
  onAvailable: (callback: (info: unknown) => void) => void
  onNotAvailable: (callback: () => void) => void
  onProgress: (callback: (progreso: unknown) => void) => void
  onDownloaded: (callback: (info: unknown) => void) => void
  onError: (callback: (error: string) => void) => void
}

export interface OfflineAPI {
  estado: () => Promise<{ conectado: boolean; pendientes: number; ultimaSync: { certificados: string | null; notificaciones: string | null; etiquetas: string | null } }>
  forzarSync: (apiUrl: string, token: string, organizacionId: string) => Promise<{ exito: boolean; resultado?: unknown; error?: string }>
  listarCertificados: (organizacionId: string, filtros?: unknown) => Promise<{ datos: unknown[]; total: number }>
  listarNotificaciones: (organizacionId: string, filtros?: unknown) => Promise<{ datos: unknown[]; total: number }>
  listarEtiquetas: (organizacionId: string) => Promise<unknown[]>
  encolarCambio: (recurso: string, recursoId: string, operacion: string, payload: unknown) => Promise<void>
  actualizarToken: (apiUrl: string, token: string, organizacionId: string) => Promise<void>
  iniciarDetector: (apiUrl: string) => Promise<void>
  onCambioEstado: (callback: (conectado: boolean) => void) => void
  onSyncCompletada: (callback: () => void) => void
}

export interface ElectronAPI {
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
  notificaciones: NotificacionesAPI
  firma: FirmaAPI
  workflows: WorkflowsDesktopAPI
  scheduler: SchedulerDesktopAPI
  tray: TrayDesktopAPI
  analytics: AnalyticsDesktopAPI
  backup: BackupDesktopAPI
  multicert: MultiCertAPI
  ocr: OcrAPI
  offline: OfflineAPI
}

const certsAPI: CertsAPI = {
  seleccionarArchivo: (password) =>
    ipcRenderer.invoke('certs:seleccionarArchivo', password),
  leerP12: (ruta, password) =>
    ipcRenderer.invoke('certs:leerP12', ruta, password),
  listarLocales: () =>
    ipcRenderer.invoke('certs:listarLocales'),
  instalarEnWindows: (rutaPfx, password) =>
    ipcRenderer.invoke('certs:instalarEnWindows', rutaPfx, password),
  desinstalarDeWindows: (thumbprint) =>
    ipcRenderer.invoke('certs:desinstalarDeWindows', thumbprint),
  listarInstalados: () =>
    ipcRenderer.invoke('certs:listarInstalados'),
  activar: (numeroSerie) =>
    ipcRenderer.invoke('certs:activar', numeroSerie),
  desactivar: () =>
    ipcRenderer.invoke('certs:desactivar'),
  obtenerActivo: () =>
    ipcRenderer.invoke('certs:obtenerActivo'),
  exportarPfx: (thumbprint, password) =>
    ipcRenderer.invoke('certs:exportarPfx', thumbprint, password),
  sincronizarConCloud: (ruta, password, apiUrl, token) =>
    ipcRenderer.invoke('certs:sincronizarConCloud', ruta, password, apiUrl, token),
  sincronizarDesdeCloud: (apiUrl, token) =>
    ipcRenderer.invoke('certs:sincronizarDesdeCloud', apiUrl, token),
  aislar: (thumbprint) =>
    ipcRenderer.invoke('certs:aislar', thumbprint),
  restaurar: (thumbprint) =>
    ipcRenderer.invoke('certs:restaurar', thumbprint),
  iniciarWatcher: (carpeta) =>
    ipcRenderer.invoke('certs:iniciarWatcher', carpeta),
  detenerWatcher: () =>
    ipcRenderer.invoke('certs:detenerWatcher'),
  obtenerCarpeta: () =>
    ipcRenderer.invoke('certs:obtenerCarpeta'),
  onNuevoCertificado: (callback) => {
    ipcRenderer.on('certs:nuevoArchivo', (_event, ruta: string) => {
      callback(ruta)
    })
  },
}

const scrapingAPI: ScrapingAPI = {
  obtenerEstado: () =>
    ipcRenderer.invoke('scraping:obtenerEstado'),
  configurar: (config) =>
    ipcRenderer.invoke('scraping:configurar', config),
  obtenerConfig: () =>
    ipcRenderer.invoke('scraping:obtenerConfig'),
  iniciar: () =>
    ipcRenderer.invoke('scraping:iniciar'),
  detener: () =>
    ipcRenderer.invoke('scraping:detener'),
  limpiar: () =>
    ipcRenderer.invoke('scraping:limpiar'),
  onProgreso: (callback) => {
    ipcRenderer.on('scraping:progreso', (_event, estado: unknown) => {
      callback(estado)
    })
  },
  onNotificacionesNuevas: (callback) => {
    ipcRenderer.on('notificaciones:nuevas', (_event, datos: { portal: string; nuevas: number }) => {
      callback(datos)
    })
  },
}

const dehuAPI: DehuAPI = {
  consultarNotificaciones: (config, apiUrl, token) =>
    ipcRenderer.invoke('dehu:consultarNotificaciones', config, apiUrl, token),
  descargarNotificacion: (config, notificacion) =>
    ipcRenderer.invoke('dehu:descargarNotificacion', config, notificacion),
  sincronizarCloud: (notificaciones, certificadoId, apiUrl, token) =>
    ipcRenderer.invoke('dehu:sincronizarCloud', notificaciones, certificadoId, apiUrl, token),
  consultarYSincronizar: (configs, apiUrl, token) =>
    ipcRenderer.invoke('dehu:consultarYSincronizar', configs, apiUrl, token),
  verificarAlta: (config) =>
    ipcRenderer.invoke('dehu:verificarAlta', config),
  verificarPdfDescargado: (idDehu, certificadoSerial) =>
    ipcRenderer.invoke('dehu:verificarPdfDescargado', idDehu, certificadoSerial),
  verificarPdfsBatch: (items) =>
    ipcRenderer.invoke('dehu:verificarPdfsBatch', items),
  abrirPdf: (rutaLocal) =>
    ipcRenderer.invoke('dehu:abrirPdf', rutaLocal),
  descargarPdfBatch: (config, notificaciones) =>
    ipcRenderer.invoke('dehu:descargarPdfBatch', config, notificaciones),
  onProgresoBatch: (callback) => {
    ipcRenderer.on('dehu:progresoBatch', (_event, progreso: { actual: number; total: number; idDehu: string }) => {
      callback(progreso)
    })
  },
}

const documentalesAPI: DocumentalesAPI = {
  obtenerCatalogo: () =>
    ipcRenderer.invoke('docs:obtenerCatalogo'),
  obtenerConfig: (certificadoSerial) =>
    ipcRenderer.invoke('docs:obtenerConfig', certificadoSerial),
  guardarConfig: (certificadoSerial, documentosActivos, datosExtra) =>
    ipcRenderer.invoke('docs:guardarConfig', certificadoSerial, documentosActivos, datosExtra),
  descargarDocumento: (tipo, certificadoSerial, datosExtra) =>
    ipcRenderer.invoke('docs:descargarDocumento', tipo, certificadoSerial, datosExtra),
  descargarBatch: (configs) =>
    ipcRenderer.invoke('docs:descargarBatch', configs),
  obtenerHistorial: (certificadoSerial) =>
    ipcRenderer.invoke('docs:obtenerHistorial', certificadoSerial),
  abrirCarpeta: (certificadoSerial) =>
    ipcRenderer.invoke('docs:abrirCarpeta', certificadoSerial),
  limpiarHistorial: () =>
    ipcRenderer.invoke('docs:limpiarHistorial'),
  listarArchivos: (serialNumber) =>
    ipcRenderer.invoke('docs:listarArchivos', serialNumber),
  eliminarArchivo: (ruta) =>
    ipcRenderer.invoke('docs:eliminarArchivo', ruta),
  limpiarDebug: (serialNumber) =>
    ipcRenderer.invoke('docs:limpiarDebug', serialNumber),
  estadisticasCarpeta: (serialNumber) =>
    ipcRenderer.invoke('docs:estadisticasCarpeta', serialNumber),
  abrirArchivo: (ruta) =>
    ipcRenderer.invoke('docs:abrirArchivo', ruta),
  ultimosResultados: (certificadoSerial) =>
    ipcRenderer.invoke('docs:ultimosResultados', certificadoSerial),
  sincronizarCloud: (apiUrl, token) =>
    ipcRenderer.invoke('docs:sincronizarCloud', apiUrl, token),
  sincronizarConfigCloud: (apiUrl, token) =>
    ipcRenderer.invoke('docs:sincronizarConfigCloud', apiUrl, token),
  recuperarConfigCloud: (apiUrl, token) =>
    ipcRenderer.invoke('docs:recuperarConfigCloud', apiUrl, token),
}

const notificacionesAPI: NotificacionesAPI = {
  obtenerConfigPortales: (certificadoSerial) =>
    ipcRenderer.invoke('notif:obtenerConfigPortales', certificadoSerial),
  guardarConfigPortales: (certificadoSerial, portalesActivos, datosPortal) =>
    ipcRenderer.invoke('notif:guardarConfigPortales', certificadoSerial, portalesActivos, datosPortal),
  obtenerPortalesDisponibles: () =>
    ipcRenderer.invoke('notif:obtenerPortalesDisponibles'),
  consultarPortal: (portal, serialNumber, apiUrl, token, configDehu) =>
    ipcRenderer.invoke('notif:consultarPortal', portal, serialNumber, apiUrl, token, configDehu),
  consultarMultiPortal: (serialNumber, apiUrl, token, configDehu) =>
    ipcRenderer.invoke('notif:consultarMultiPortal', serialNumber, apiUrl, token, configDehu),
  consultarYSincronizarBatch: (configs, apiUrl, token) =>
    ipcRenderer.invoke('notif:consultarYSincronizarBatch', configs, apiUrl, token),
  descargarPdf: (idExterno, portal, configDehu, estadoNotificacion, titularNotificacion) =>
    ipcRenderer.invoke('notif:descargarPdf', idExterno, portal, configDehu, estadoNotificacion, titularNotificacion),
}

const firmaAPI: FirmaAPI = {
  modosDisponibles: () =>
    ipcRenderer.invoke('firma:modosDisponibles'),
  validarCertificado: (ruta, password) =>
    ipcRenderer.invoke('firma:validarCertificado', ruta, password),
  firmarLocal: (opciones, certificadoSerial) =>
    ipcRenderer.invoke('firma:firmarLocal', opciones, certificadoSerial),
  firmarAutoFirma: (opciones, certificadoSerial) =>
    ipcRenderer.invoke('firma:firmarAutoFirma', opciones, certificadoSerial),
  firmarBatch: (opciones) =>
    ipcRenderer.invoke('firma:firmarBatch', opciones),
  obtenerHistorial: () =>
    ipcRenderer.invoke('firma:obtenerHistorial'),
  sincronizarCloud: (apiUrl, token, mapaCertificados) =>
    ipcRenderer.invoke('firma:sincronizarCloud', apiUrl, token, mapaCertificados),
  detectarAutoFirma: () =>
    ipcRenderer.invoke('firma:detectarAutoFirma'),
  onProgreso: (callback) => {
    ipcRenderer.on('firma:progreso', (_event, progreso: unknown) => {
      callback(progreso)
    })
  },
}

const workflowsDesktopAPI: WorkflowsDesktopAPI = {
  listar: () =>
    ipcRenderer.invoke('workflows:listar'),
  obtener: (id) =>
    ipcRenderer.invoke('workflows:obtener', id),
  guardar: (workflow) =>
    ipcRenderer.invoke('workflows:guardar', workflow),
  eliminar: (id) =>
    ipcRenderer.invoke('workflows:eliminar', id),
  duplicar: (id) =>
    ipcRenderer.invoke('workflows:duplicar', id),
  ejecutar: (id, contexto) =>
    ipcRenderer.invoke('workflows:ejecutar', id, contexto),
  historial: (limite) =>
    ipcRenderer.invoke('workflows:historial', limite),
  limpiarHistorial: (mantener) =>
    ipcRenderer.invoke('workflows:limpiarHistorial', mantener),
  categorias: () =>
    ipcRenderer.invoke('workflows:categorias'),
  obtenerSmtp: () =>
    ipcRenderer.invoke('workflows:obtenerSmtp'),
  guardarSmtp: (config) =>
    ipcRenderer.invoke('workflows:guardarSmtp', config),
  procesarDisparador: (disparador, contexto) =>
    ipcRenderer.invoke('workflows:procesarDisparador', disparador, contexto),
  onProgreso: (callback) => {
    ipcRenderer.on('workflows:progreso', (_event, progreso: unknown) => {
      callback(progreso)
    })
  },
}

const schedulerAPI: SchedulerDesktopAPI = {
  obtenerEstado: () =>
    ipcRenderer.invoke('scheduler:obtenerEstado'),
  listarTareas: () =>
    ipcRenderer.invoke('scheduler:listarTareas'),
  obtenerTarea: (id) =>
    ipcRenderer.invoke('scheduler:obtenerTarea', id),
  crearTarea: (datos) =>
    ipcRenderer.invoke('scheduler:crearTarea', datos),
  actualizarTarea: (id, datos) =>
    ipcRenderer.invoke('scheduler:actualizarTarea', id, datos),
  eliminarTarea: (id) =>
    ipcRenderer.invoke('scheduler:eliminarTarea', id),
  toggleTarea: (id) =>
    ipcRenderer.invoke('scheduler:toggleTarea', id),
  ejecutarAhora: (id) =>
    ipcRenderer.invoke('scheduler:ejecutarAhora', id),
  historial: (limite) =>
    ipcRenderer.invoke('scheduler:historial', limite),
  limpiarHistorial: (mantener) =>
    ipcRenderer.invoke('scheduler:limpiarHistorial', mantener),
  onProgreso: (callback) => {
    ipcRenderer.on('scheduler:progreso', (_event, estado: unknown) => {
      callback(estado)
    })
  },
}

const trayAPI: TrayDesktopAPI = {
  obtenerEstado: () =>
    ipcRenderer.invoke('tray:obtenerEstado'),
  listarNotificaciones: (limite) =>
    ipcRenderer.invoke('tray:listarNotificaciones', limite),
  marcarLeida: (id) =>
    ipcRenderer.invoke('tray:marcarLeida', id),
  marcarTodasLeidas: () =>
    ipcRenderer.invoke('tray:marcarTodasLeidas'),
  obtenerConfig: () =>
    ipcRenderer.invoke('tray:obtenerConfig'),
  guardarConfig: (config) =>
    ipcRenderer.invoke('tray:guardarConfig', config),
  limpiarAntiguas: (mantener) =>
    ipcRenderer.invoke('tray:limpiarAntiguas', mantener),
  ejecutarChequeo: () =>
    ipcRenderer.invoke('tray:ejecutarChequeo'),
  onNuevaNotificacion: (callback) => {
    ipcRenderer.on('tray:nuevaNotificacion', (_event, notificacion: unknown) => {
      callback(notificacion)
    })
  },
}

const analyticsAPI: AnalyticsDesktopAPI = {
  metricas: () =>
    ipcRenderer.invoke('analytics:metricas'),
  metricasCerts: () =>
    ipcRenderer.invoke('analytics:metricasCerts'),
  actividadTemporal: (dias) =>
    ipcRenderer.invoke('analytics:actividadTemporal', dias),
}

const backupAPI: BackupDesktopAPI = {
  exportar: (opciones) =>
    ipcRenderer.invoke('backup:exportar', opciones),
  importar: (opciones) =>
    ipcRenderer.invoke('backup:importar', opciones),
  previsualizar: (opciones) =>
    ipcRenderer.invoke('backup:previsualizar', opciones),
}

const multicertAPI: MultiCertAPI = {
  iniciar: (configs, apiUrl, token) =>
    ipcRenderer.invoke('multicert:iniciar', configs, apiUrl, token),
  detener: () =>
    ipcRenderer.invoke('multicert:detener'),
  obtenerEstado: () =>
    ipcRenderer.invoke('multicert:obtenerEstado'),
  obtenerHistorial: (limite) =>
    ipcRenderer.invoke('multicert:obtenerHistorial', limite),
  limpiarHistorial: () =>
    ipcRenderer.invoke('multicert:limpiarHistorial'),
}

const ocrAPI: OcrAPI = {
  extraerTexto: (rutaPdf) =>
    ipcRenderer.invoke('ocr:extraerTexto', rutaPdf),
  estado: () =>
    ipcRenderer.invoke('ocr:estado'),
}

const offlineAPI: OfflineAPI = {
  estado: () =>
    ipcRenderer.invoke('offline:estado'),
  forzarSync: (apiUrl, token, organizacionId) =>
    ipcRenderer.invoke('offline:forzarSync', apiUrl, token, organizacionId),
  listarCertificados: (organizacionId, filtros) =>
    ipcRenderer.invoke('offline:listarCertificados', organizacionId, filtros),
  listarNotificaciones: (organizacionId, filtros) =>
    ipcRenderer.invoke('offline:listarNotificaciones', organizacionId, filtros),
  listarEtiquetas: (organizacionId) =>
    ipcRenderer.invoke('offline:listarEtiquetas', organizacionId),
  encolarCambio: (recurso, recursoId, operacion, payload) =>
    ipcRenderer.invoke('offline:encolarCambio', recurso, recursoId, operacion, payload),
  actualizarToken: (apiUrl, token, organizacionId) =>
    ipcRenderer.invoke('offline:actualizarToken', apiUrl, token, organizacionId),
  iniciarDetector: (apiUrl) =>
    ipcRenderer.invoke('offline:iniciarDetector', apiUrl),
  onCambioEstado: (callback) => {
    ipcRenderer.on('offline:cambioEstado', (_event, conectado: boolean) => {
      callback(conectado)
    })
  },
  onSyncCompletada: (callback) => {
    ipcRenderer.on('offline:syncCompletada', () => {
      callback()
    })
  },
}

export interface TelemetriaAPI {
  optOut: () => Promise<void>
  optIn: () => Promise<void>
  estaActiva: () => Promise<boolean>
  estado: () => Promise<{ activa: boolean; eventosEnCola: number; ultimoEnvio: string | null }>
  registrar: (evento: string, propiedades?: Record<string, unknown>) => Promise<void>
}

const telemetriaAPI: TelemetriaAPI = {
  optOut: () => ipcRenderer.invoke('telemetria:optOut'),
  optIn: () => ipcRenderer.invoke('telemetria:optIn'),
  estaActiva: () => ipcRenderer.invoke('telemetria:estaActiva'),
  estado: () => ipcRenderer.invoke('telemetria:estado'),
  registrar: (evento, propiedades) => ipcRenderer.invoke('telemetria:registrar', evento, propiedades),
}

const updaterAPI: UpdaterAPI = {
  checkNow: () => ipcRenderer.invoke('updater:checkNow'),
  onChecking: (callback) => {
    ipcRenderer.on('update:checking', () => callback())
  },
  onAvailable: (callback) => {
    ipcRenderer.on('update:available', (_event, info: unknown) => callback(info))
  },
  onNotAvailable: (callback) => {
    ipcRenderer.on('update:not-available', () => callback())
  },
  onProgress: (callback) => {
    ipcRenderer.on('update:progress', (_event, progreso: unknown) => callback(progreso))
  },
  onDownloaded: (callback) => {
    ipcRenderer.on('update:downloaded', (_event, info: unknown) => callback(info))
  },
  onError: (callback) => {
    ipcRenderer.on('update:error', (_event, error: string) => callback(error))
  },
}

const electronAPI: ElectronAPI = {
  isDesktop: true,

  getVersion: () => ipcRenderer.invoke('app:getVersion'),
  getPlatform: () => ipcRenderer.invoke('app:getPlatform'),
  installUpdate: () => ipcRenderer.invoke('app:installUpdate'),

  onUpdateAvailable: (callback) => {
    ipcRenderer.on('update:available', (_event, version: string) => {
      callback(typeof version === 'string' ? version : (version as { version: string }).version)
    })
  },

  onUpdateDownloaded: (callback) => {
    ipcRenderer.on('update:downloaded', (_event, version: string) => {
      callback(typeof version === 'string' ? version : (version as { version: string }).version)
    })
  },

  updater: updaterAPI,
  telemetria: telemetriaAPI,
  certs: certsAPI,
  scraping: scrapingAPI,
  dehu: dehuAPI,
  documentales: documentalesAPI,
  notificaciones: notificacionesAPI,
  firma: firmaAPI,
  workflows: workflowsDesktopAPI,
  scheduler: schedulerAPI,
  tray: trayAPI,
  analytics: analyticsAPI,
  backup: backupAPI,
  multicert: multicertAPI,
  ocr: ocrAPI,
  offline: offlineAPI,
}

contextBridge.exposeInMainWorld('electronAPI', electronAPI)
