import { contextBridge, ipcRenderer } from "electron";
const certsAPI = {
  seleccionarArchivo: (password) => ipcRenderer.invoke("certs:seleccionarArchivo", password),
  leerP12: (ruta, password) => ipcRenderer.invoke("certs:leerP12", ruta, password),
  listarLocales: () => ipcRenderer.invoke("certs:listarLocales"),
  instalarEnWindows: (rutaPfx, password) => ipcRenderer.invoke("certs:instalarEnWindows", rutaPfx, password),
  desinstalarDeWindows: (thumbprint) => ipcRenderer.invoke("certs:desinstalarDeWindows", thumbprint),
  listarInstalados: () => ipcRenderer.invoke("certs:listarInstalados"),
  activar: (numeroSerie) => ipcRenderer.invoke("certs:activar", numeroSerie),
  desactivar: () => ipcRenderer.invoke("certs:desactivar"),
  obtenerActivo: () => ipcRenderer.invoke("certs:obtenerActivo"),
  exportarPfx: (thumbprint, password) => ipcRenderer.invoke("certs:exportarPfx", thumbprint, password),
  sincronizarConCloud: (ruta, password, apiUrl, token) => ipcRenderer.invoke("certs:sincronizarConCloud", ruta, password, apiUrl, token),
  sincronizarDesdeCloud: (apiUrl, token) => ipcRenderer.invoke("certs:sincronizarDesdeCloud", apiUrl, token),
  aislar: (thumbprint) => ipcRenderer.invoke("certs:aislar", thumbprint),
  restaurar: (thumbprint) => ipcRenderer.invoke("certs:restaurar", thumbprint),
  iniciarWatcher: (carpeta) => ipcRenderer.invoke("certs:iniciarWatcher", carpeta),
  detenerWatcher: () => ipcRenderer.invoke("certs:detenerWatcher"),
  obtenerCarpeta: () => ipcRenderer.invoke("certs:obtenerCarpeta"),
  onNuevoCertificado: (callback) => {
    ipcRenderer.on("certs:nuevoArchivo", (_event, ruta) => {
      callback(ruta);
    });
  }
};
const scrapingAPI = {
  obtenerEstado: () => ipcRenderer.invoke("scraping:obtenerEstado"),
  configurar: (config) => ipcRenderer.invoke("scraping:configurar", config),
  obtenerConfig: () => ipcRenderer.invoke("scraping:obtenerConfig"),
  iniciar: () => ipcRenderer.invoke("scraping:iniciar"),
  detener: () => ipcRenderer.invoke("scraping:detener"),
  limpiar: () => ipcRenderer.invoke("scraping:limpiar"),
  onProgreso: (callback) => {
    ipcRenderer.on("scraping:progreso", (_event, estado) => {
      callback(estado);
    });
  },
  onNotificacionesNuevas: (callback) => {
    ipcRenderer.on("notificaciones:nuevas", (_event, datos) => {
      callback(datos);
    });
  }
};
const dehuAPI = {
  consultarNotificaciones: (config, apiUrl, token) => ipcRenderer.invoke("dehu:consultarNotificaciones", config, apiUrl, token),
  descargarNotificacion: (config, notificacion) => ipcRenderer.invoke("dehu:descargarNotificacion", config, notificacion),
  sincronizarCloud: (notificaciones, certificadoId, apiUrl, token) => ipcRenderer.invoke("dehu:sincronizarCloud", notificaciones, certificadoId, apiUrl, token),
  consultarYSincronizar: (configs, apiUrl, token) => ipcRenderer.invoke("dehu:consultarYSincronizar", configs, apiUrl, token),
  verificarAlta: (config) => ipcRenderer.invoke("dehu:verificarAlta", config),
  verificarPdfDescargado: (idDehu, certificadoSerial) => ipcRenderer.invoke("dehu:verificarPdfDescargado", idDehu, certificadoSerial),
  verificarPdfsBatch: (items) => ipcRenderer.invoke("dehu:verificarPdfsBatch", items),
  abrirPdf: (rutaLocal) => ipcRenderer.invoke("dehu:abrirPdf", rutaLocal),
  descargarPdfBatch: (config, notificaciones) => ipcRenderer.invoke("dehu:descargarPdfBatch", config, notificaciones),
  onProgresoBatch: (callback) => {
    ipcRenderer.on("dehu:progresoBatch", (_event, progreso) => {
      callback(progreso);
    });
  }
};
const documentalesAPI = {
  obtenerCatalogo: () => ipcRenderer.invoke("docs:obtenerCatalogo"),
  obtenerConfig: (certificadoSerial) => ipcRenderer.invoke("docs:obtenerConfig", certificadoSerial),
  guardarConfig: (certificadoSerial, documentosActivos, datosExtra) => ipcRenderer.invoke("docs:guardarConfig", certificadoSerial, documentosActivos, datosExtra),
  descargarDocumento: (tipo, certificadoSerial, datosExtra) => ipcRenderer.invoke("docs:descargarDocumento", tipo, certificadoSerial, datosExtra),
  descargarBatch: (configs) => ipcRenderer.invoke("docs:descargarBatch", configs),
  obtenerHistorial: (certificadoSerial) => ipcRenderer.invoke("docs:obtenerHistorial", certificadoSerial),
  abrirCarpeta: (certificadoSerial) => ipcRenderer.invoke("docs:abrirCarpeta", certificadoSerial),
  limpiarHistorial: () => ipcRenderer.invoke("docs:limpiarHistorial"),
  listarArchivos: (serialNumber) => ipcRenderer.invoke("docs:listarArchivos", serialNumber),
  eliminarArchivo: (ruta) => ipcRenderer.invoke("docs:eliminarArchivo", ruta),
  limpiarDebug: (serialNumber) => ipcRenderer.invoke("docs:limpiarDebug", serialNumber),
  estadisticasCarpeta: (serialNumber) => ipcRenderer.invoke("docs:estadisticasCarpeta", serialNumber),
  abrirArchivo: (ruta) => ipcRenderer.invoke("docs:abrirArchivo", ruta),
  ultimosResultados: (certificadoSerial) => ipcRenderer.invoke("docs:ultimosResultados", certificadoSerial),
  sincronizarCloud: (apiUrl, token) => ipcRenderer.invoke("docs:sincronizarCloud", apiUrl, token),
  sincronizarConfigCloud: (apiUrl, token) => ipcRenderer.invoke("docs:sincronizarConfigCloud", apiUrl, token),
  recuperarConfigCloud: (apiUrl, token) => ipcRenderer.invoke("docs:recuperarConfigCloud", apiUrl, token)
};
const notificacionesAPI = {
  obtenerConfigPortales: (certificadoSerial) => ipcRenderer.invoke("notif:obtenerConfigPortales", certificadoSerial),
  guardarConfigPortales: (certificadoSerial, portalesActivos, datosPortal) => ipcRenderer.invoke("notif:guardarConfigPortales", certificadoSerial, portalesActivos, datosPortal),
  obtenerPortalesDisponibles: () => ipcRenderer.invoke("notif:obtenerPortalesDisponibles"),
  consultarPortal: (portal, serialNumber, apiUrl, token, configDehu) => ipcRenderer.invoke("notif:consultarPortal", portal, serialNumber, apiUrl, token, configDehu),
  consultarMultiPortal: (serialNumber, apiUrl, token, configDehu) => ipcRenderer.invoke("notif:consultarMultiPortal", serialNumber, apiUrl, token, configDehu),
  consultarYSincronizarBatch: (configs, apiUrl, token) => ipcRenderer.invoke("notif:consultarYSincronizarBatch", configs, apiUrl, token),
  descargarPdf: (idExterno, portal, configDehu, estadoNotificacion, titularNotificacion) => ipcRenderer.invoke("notif:descargarPdf", idExterno, portal, configDehu, estadoNotificacion, titularNotificacion)
};
const firmaAPI = {
  modosDisponibles: () => ipcRenderer.invoke("firma:modosDisponibles"),
  validarCertificado: (ruta, password) => ipcRenderer.invoke("firma:validarCertificado", ruta, password),
  firmarLocal: (opciones, certificadoSerial) => ipcRenderer.invoke("firma:firmarLocal", opciones, certificadoSerial),
  firmarAutoFirma: (opciones, certificadoSerial) => ipcRenderer.invoke("firma:firmarAutoFirma", opciones, certificadoSerial),
  firmarBatch: (opciones) => ipcRenderer.invoke("firma:firmarBatch", opciones),
  obtenerHistorial: () => ipcRenderer.invoke("firma:obtenerHistorial"),
  sincronizarCloud: (apiUrl, token, mapaCertificados) => ipcRenderer.invoke("firma:sincronizarCloud", apiUrl, token, mapaCertificados),
  detectarAutoFirma: () => ipcRenderer.invoke("firma:detectarAutoFirma"),
  onProgreso: (callback) => {
    ipcRenderer.on("firma:progreso", (_event, progreso) => {
      callback(progreso);
    });
  }
};
const workflowsDesktopAPI = {
  listar: () => ipcRenderer.invoke("workflows:listar"),
  obtener: (id) => ipcRenderer.invoke("workflows:obtener", id),
  guardar: (workflow) => ipcRenderer.invoke("workflows:guardar", workflow),
  eliminar: (id) => ipcRenderer.invoke("workflows:eliminar", id),
  duplicar: (id) => ipcRenderer.invoke("workflows:duplicar", id),
  ejecutar: (id, contexto) => ipcRenderer.invoke("workflows:ejecutar", id, contexto),
  historial: (limite) => ipcRenderer.invoke("workflows:historial", limite),
  limpiarHistorial: (mantener) => ipcRenderer.invoke("workflows:limpiarHistorial", mantener),
  categorias: () => ipcRenderer.invoke("workflows:categorias"),
  obtenerSmtp: () => ipcRenderer.invoke("workflows:obtenerSmtp"),
  guardarSmtp: (config) => ipcRenderer.invoke("workflows:guardarSmtp", config),
  procesarDisparador: (disparador, contexto) => ipcRenderer.invoke("workflows:procesarDisparador", disparador, contexto),
  onProgreso: (callback) => {
    ipcRenderer.on("workflows:progreso", (_event, progreso) => {
      callback(progreso);
    });
  }
};
const schedulerAPI = {
  obtenerEstado: () => ipcRenderer.invoke("scheduler:obtenerEstado"),
  listarTareas: () => ipcRenderer.invoke("scheduler:listarTareas"),
  obtenerTarea: (id) => ipcRenderer.invoke("scheduler:obtenerTarea", id),
  crearTarea: (datos) => ipcRenderer.invoke("scheduler:crearTarea", datos),
  actualizarTarea: (id, datos) => ipcRenderer.invoke("scheduler:actualizarTarea", id, datos),
  eliminarTarea: (id) => ipcRenderer.invoke("scheduler:eliminarTarea", id),
  toggleTarea: (id) => ipcRenderer.invoke("scheduler:toggleTarea", id),
  ejecutarAhora: (id) => ipcRenderer.invoke("scheduler:ejecutarAhora", id),
  historial: (limite) => ipcRenderer.invoke("scheduler:historial", limite),
  limpiarHistorial: (mantener) => ipcRenderer.invoke("scheduler:limpiarHistorial", mantener),
  onProgreso: (callback) => {
    ipcRenderer.on("scheduler:progreso", (_event, estado) => {
      callback(estado);
    });
  }
};
const trayAPI = {
  obtenerEstado: () => ipcRenderer.invoke("tray:obtenerEstado"),
  listarNotificaciones: (limite) => ipcRenderer.invoke("tray:listarNotificaciones", limite),
  marcarLeida: (id) => ipcRenderer.invoke("tray:marcarLeida", id),
  marcarTodasLeidas: () => ipcRenderer.invoke("tray:marcarTodasLeidas"),
  obtenerConfig: () => ipcRenderer.invoke("tray:obtenerConfig"),
  guardarConfig: (config) => ipcRenderer.invoke("tray:guardarConfig", config),
  limpiarAntiguas: (mantener) => ipcRenderer.invoke("tray:limpiarAntiguas", mantener),
  ejecutarChequeo: () => ipcRenderer.invoke("tray:ejecutarChequeo"),
  onNuevaNotificacion: (callback) => {
    ipcRenderer.on("tray:nuevaNotificacion", (_event, notificacion) => {
      callback(notificacion);
    });
  }
};
const analyticsAPI = {
  metricas: () => ipcRenderer.invoke("analytics:metricas"),
  metricasCerts: () => ipcRenderer.invoke("analytics:metricasCerts"),
  actividadTemporal: (dias) => ipcRenderer.invoke("analytics:actividadTemporal", dias)
};
const backupAPI = {
  exportar: (opciones) => ipcRenderer.invoke("backup:exportar", opciones),
  importar: (opciones) => ipcRenderer.invoke("backup:importar", opciones),
  previsualizar: (opciones) => ipcRenderer.invoke("backup:previsualizar", opciones)
};
const multicertAPI = {
  iniciar: (configs, apiUrl, token) => ipcRenderer.invoke("multicert:iniciar", configs, apiUrl, token),
  detener: () => ipcRenderer.invoke("multicert:detener"),
  obtenerEstado: () => ipcRenderer.invoke("multicert:obtenerEstado"),
  obtenerHistorial: (limite) => ipcRenderer.invoke("multicert:obtenerHistorial", limite),
  limpiarHistorial: () => ipcRenderer.invoke("multicert:limpiarHistorial")
};
const ocrAPI = {
  extraerTexto: (rutaPdf) => ipcRenderer.invoke("ocr:extraerTexto", rutaPdf),
  estado: () => ipcRenderer.invoke("ocr:estado")
};
const offlineAPI = {
  estado: () => ipcRenderer.invoke("offline:estado"),
  forzarSync: (apiUrl, token, organizacionId) => ipcRenderer.invoke("offline:forzarSync", apiUrl, token, organizacionId),
  listarCertificados: (organizacionId, filtros) => ipcRenderer.invoke("offline:listarCertificados", organizacionId, filtros),
  listarNotificaciones: (organizacionId, filtros) => ipcRenderer.invoke("offline:listarNotificaciones", organizacionId, filtros),
  listarEtiquetas: (organizacionId) => ipcRenderer.invoke("offline:listarEtiquetas", organizacionId),
  encolarCambio: (recurso, recursoId, operacion, payload) => ipcRenderer.invoke("offline:encolarCambio", recurso, recursoId, operacion, payload),
  actualizarToken: (apiUrl, token, organizacionId) => ipcRenderer.invoke("offline:actualizarToken", apiUrl, token, organizacionId),
  iniciarDetector: (apiUrl) => ipcRenderer.invoke("offline:iniciarDetector", apiUrl),
  onCambioEstado: (callback) => {
    ipcRenderer.on("offline:cambioEstado", (_event, conectado) => {
      callback(conectado);
    });
  },
  onSyncCompletada: (callback) => {
    ipcRenderer.on("offline:syncCompletada", () => {
      callback();
    });
  }
};
const telemetriaAPI = {
  optOut: () => ipcRenderer.invoke("telemetria:optOut"),
  optIn: () => ipcRenderer.invoke("telemetria:optIn"),
  estaActiva: () => ipcRenderer.invoke("telemetria:estaActiva"),
  estado: () => ipcRenderer.invoke("telemetria:estado"),
  registrar: (evento, propiedades) => ipcRenderer.invoke("telemetria:registrar", evento, propiedades)
};
const updaterAPI = {
  checkNow: () => ipcRenderer.invoke("updater:checkNow"),
  onChecking: (callback) => {
    ipcRenderer.on("update:checking", () => callback());
  },
  onAvailable: (callback) => {
    ipcRenderer.on("update:available", (_event, info) => callback(info));
  },
  onNotAvailable: (callback) => {
    ipcRenderer.on("update:not-available", () => callback());
  },
  onProgress: (callback) => {
    ipcRenderer.on("update:progress", (_event, progreso) => callback(progreso));
  },
  onDownloaded: (callback) => {
    ipcRenderer.on("update:downloaded", (_event, info) => callback(info));
  },
  onError: (callback) => {
    ipcRenderer.on("update:error", (_event, error) => callback(error));
  }
};
const electronAPI = {
  isDesktop: true,
  getVersion: () => ipcRenderer.invoke("app:getVersion"),
  getPlatform: () => ipcRenderer.invoke("app:getPlatform"),
  installUpdate: () => ipcRenderer.invoke("app:installUpdate"),
  onUpdateAvailable: (callback) => {
    ipcRenderer.on("update:available", (_event, version) => {
      callback(typeof version === "string" ? version : version.version);
    });
  },
  onUpdateDownloaded: (callback) => {
    ipcRenderer.on("update:downloaded", (_event, version) => {
      callback(typeof version === "string" ? version : version.version);
    });
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
  offline: offlineAPI
};
contextBridge.exposeInMainWorld("electronAPI", electronAPI);
