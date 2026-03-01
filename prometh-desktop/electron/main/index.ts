import { app, BrowserWindow, ipcMain, shell } from 'electron'
import { join } from 'path'
import { is } from '@electron-toolkit/utils'
import log from 'electron-log'
import electronUpdater from 'electron-updater'
const { autoUpdater } = electronUpdater
import { registrarHandlersCertificados } from '../handlers/certificados'
import { registrarHandlersScraping } from '../handlers/scraping'
import { registrarHandlersDehu } from '../handlers/dehu'
import { registrarHandlersDocumentales } from '../handlers/documentales'
import { registrarHandlersNotificaciones } from '../handlers/notificaciones'
import { registrarHandlersFirma } from '../handlers/firma'
import { registrarHandlersWorkflows } from '../handlers/workflows'
import { registrarHandlersScheduler, detenerScheduler } from '../handlers/scheduler'
import { registrarHandlersTray, destruirTray } from '../handlers/tray'
import { registrarHandlersAnalytics } from '../handlers/analytics'
import { registrarHandlersBackup } from '../handlers/backup'
import { registrarHandlersMultiCert } from '../handlers/multi-cert'
import { registrarHandlersOcr } from '../handlers/ocr'
import { registrarHandlersOffline, detenerOffline } from '../handlers/offline'
import { inicializarEsquemaLocal } from '../offline/migrador-local'
import { cerrarBd } from '../offline/bd-local'
import { terminarWorkerOcr } from '../ocr/ocr-imagen'
import { configurarUpdater, verificarActualizacionManual } from '../updater/configurar-updater'
import { clienteTelemetria } from '../telemetria/cliente-telemetria'

// Configurar logger
log.transports.file.level = 'info'
log.transports.file.maxSize = 5 * 1024 * 1024 // 5 MB max por archivo
autoUpdater.logger = log

let ventanaPrincipal: BrowserWindow | null = null

function crearVentana(): void {
  ventanaPrincipal = new BrowserWindow({
    width: 1280,
    height: 860,
    minWidth: 1024,
    minHeight: 700,
    show: false,
    title: 'PROMETH-AI Desktop',
    webPreferences: {
      preload: join(__dirname, '../preload/index.mjs'),
      contextIsolation: true,
      sandbox: false,
      nodeIntegration: false,
    },
  })

  // Mostrar cuando este listo (evita flash blanco)
  ventanaPrincipal.on('ready-to-show', () => {
    ventanaPrincipal?.show()
  })

  // Abrir enlaces externos en el navegador del SO
  ventanaPrincipal.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('https:') || url.startsWith('http:')) {
      shell.openExternal(url)
    }
    return { action: 'deny' }
  })

  // En desarrollo: cargar desde dev server de electron-vite
  if (is.dev && process.env['ELECTRON_RENDERER_URL']) {
    ventanaPrincipal.loadURL(process.env['ELECTRON_RENDERER_URL'])
  } else {
    ventanaPrincipal.loadFile(join(__dirname, '../renderer/index.html'))
  }
}

// ── IPC handlers globales ──

ipcMain.handle('app:getVersion', () => app.getVersion())
ipcMain.handle('app:getPlatform', () => process.platform)

ipcMain.handle('app:installUpdate', () => {
  autoUpdater.quitAndInstall()
})

ipcMain.handle('updater:checkNow', async () => {
  await verificarActualizacionManual()
})

// ── Telemetria ──
ipcMain.handle('telemetria:optOut', () => { clienteTelemetria.optOut() })
ipcMain.handle('telemetria:optIn', () => { clienteTelemetria.optIn() })
ipcMain.handle('telemetria:estaActiva', () => clienteTelemetria.estaActiva())
ipcMain.handle('telemetria:estado', () => clienteTelemetria.obtenerEstado())
ipcMain.handle('telemetria:registrar', (_event, evento: string, propiedades?: Record<string, unknown>) => {
  clienteTelemetria.registrar(evento, propiedades)
})

// ── Single instance lock ──

const lockObtenido = app.requestSingleInstanceLock()

if (!lockObtenido) {
  app.quit()
} else {
  app.on('second-instance', () => {
    if (ventanaPrincipal) {
      if (ventanaPrincipal.isMinimized()) ventanaPrincipal.restore()
      ventanaPrincipal.focus()
    }
  })

  app.whenReady().then(() => {
    crearVentana()
    if (ventanaPrincipal) {
      // Registrar handlers IPC de cada modulo
      registrarHandlersCertificados(ventanaPrincipal)
      registrarHandlersScraping(ventanaPrincipal)
      registrarHandlersDehu(ventanaPrincipal)
      registrarHandlersDocumentales(ventanaPrincipal)
      registrarHandlersNotificaciones(ventanaPrincipal)
      registrarHandlersFirma(ventanaPrincipal)
      registrarHandlersWorkflows(ventanaPrincipal)
      registrarHandlersScheduler(ventanaPrincipal)
      registrarHandlersTray(ventanaPrincipal)
      registrarHandlersAnalytics(ventanaPrincipal)
      registrarHandlersBackup(ventanaPrincipal)
      registrarHandlersMultiCert(ventanaPrincipal)
      registrarHandlersOcr()

      // Offline: inicializar SQLite + handlers
      inicializarEsquemaLocal()
      registrarHandlersOffline(ventanaPrincipal)

      // Auto-updater con servidor propio
      configurarUpdater(ventanaPrincipal)

      // Telemetria anonimizada
      clienteTelemetria.iniciar()
    }

    log.info(`[app] PROMETH-AI Desktop v${app.getVersion()} iniciado`)
  })
}

app.on('window-all-closed', () => {
  log.info('[app] Ventanas cerradas — saliendo')
  detenerScheduler()
  destruirTray()
  detenerOffline()
  cerrarBd()
  terminarWorkerOcr().catch(() => {})
  clienteTelemetria.registrar('app:cierre')
  clienteTelemetria.detener().catch(() => {}).finally(() => {
    app.quit()
  })
})
