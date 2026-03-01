import { BrowserWindow } from 'electron'
import pkg from 'electron-updater'
const { autoUpdater } = pkg
import log from 'electron-log'
import { is } from '@electron-toolkit/utils'
import type { InfoActualizacion, ProgresoDescarga } from './tipos-updater'

/** URL del servidor de actualizaciones en Hetzner */
const URL_ACTUALIZACIONES = 'https://www.carloscanetegomez.dev/certigestor/desktop/'

/** Intervalo de verificacion: 1 hora */
const INTERVALO_CHECK_MS = 60 * 60 * 1000

/**
 * Configura el auto-updater con servidor propio generico.
 * Emite eventos IPC al renderer para mostrar progreso.
 */
export function configurarUpdater(ventana: BrowserWindow): void {
  if (is.dev) {
    log.info('[updater] Modo desarrollo — auto-updates desactivados')
    return
  }

  autoUpdater.logger = log
  autoUpdater.autoDownload = true
  autoUpdater.autoInstallOnAppQuit = true

  // Servidor propio en Hetzner (archivos estaticos: latest.yml + .exe + .blockmap)
  autoUpdater.setFeedURL({
    provider: 'generic',
    url: URL_ACTUALIZACIONES,
  })

  // ── Eventos ──

  autoUpdater.on('checking-for-update', () => {
    log.info('[updater] Verificando actualizaciones...')
    ventana.webContents.send('update:checking')
  })

  autoUpdater.on('update-available', (info) => {
    const datos: InfoActualizacion = {
      version: info.version,
      fechaPublicacion: info.releaseDate ?? new Date().toISOString(),
      notasCambios: typeof info.releaseNotes === 'string' ? info.releaseNotes : undefined,
    }
    log.info(`[updater] Actualizacion disponible: v${datos.version}`)
    ventana.webContents.send('update:available', datos)
  })

  autoUpdater.on('update-not-available', () => {
    log.info('[updater] No hay actualizaciones disponibles')
    ventana.webContents.send('update:not-available')
  })

  autoUpdater.on('download-progress', (progreso) => {
    const datos: ProgresoDescarga = {
      porcentaje: Math.round(progreso.percent),
      bytesTransferidos: progreso.transferred,
      bytesTotal: progreso.total,
      velocidadBps: progreso.bytesPerSecond,
    }
    ventana.webContents.send('update:progress', datos)
  })

  autoUpdater.on('update-downloaded', (info) => {
    const datos: InfoActualizacion = {
      version: info.version,
      fechaPublicacion: info.releaseDate ?? new Date().toISOString(),
      notasCambios: typeof info.releaseNotes === 'string' ? info.releaseNotes : undefined,
    }
    log.info(`[updater] Actualizacion descargada: v${datos.version}`)
    ventana.webContents.send('update:downloaded', datos)
  })

  autoUpdater.on('error', (err) => {
    log.error('[updater] Error:', err.message)
    ventana.webContents.send('update:error', err.message)
  })

  // Verificacion inicial
  autoUpdater.checkForUpdatesAndNotify()

  // Verificacion periodica
  setInterval(() => {
    autoUpdater.checkForUpdates().catch((err: Error) => {
      log.error('[updater] Error en check periodico:', err.message)
    })
  }, INTERVALO_CHECK_MS)
}

/** Fuerza una verificacion manual (invocada via IPC) */
export async function verificarActualizacionManual(): Promise<void> {
  await autoUpdater.checkForUpdates()
}
