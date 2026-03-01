import { ipcMain, BrowserWindow } from 'electron'
import log from 'electron-log'
import { estaOnline, iniciarDetectorConexion, detenerDetectorConexion } from '../offline/detector-conexion'
import { contarPendientes } from '../offline/cola-cambios'
import { obtenerUltimaSync, sincronizarCompleto } from '../offline/sincronizador'
import { listarCertificadosCache } from '../offline/repositorio-certificados'
import { listarNotificacionesCache, actualizarNotificacionLocal } from '../offline/repositorio-notificaciones'
import { listarEtiquetasCache } from '../offline/repositorio-etiquetas'
import { encolarCambio } from '../offline/cola-cambios'
import type { FiltrosCertificadosCache, FiltrosNotificacionesCache } from '../offline/tipos-offline'

// Token en memoria para sync periódica
let tokenEnMemoria: string | null = null
let apiUrlEnMemoria: string | null = null
let orgIdEnMemoria: string | null = null
let intervaloSync: ReturnType<typeof setInterval> | null = null

const INTERVALO_SYNC_MS = 5 * 60 * 1000 // 5 minutos

export function registrarHandlersOffline(ventana: BrowserWindow): void {
  // Estado de conexión y sync
  ipcMain.handle('offline:estado', () => ({
    conectado: estaOnline(),
    pendientes: contarPendientes(),
    ultimaSync: obtenerUltimaSync(),
  }))

  // Forzar sync manual
  ipcMain.handle('offline:forzarSync', async (_event, apiUrl: string, token: string, organizacionId: string) => {
    try {
      const resultado = await sincronizarCompleto(apiUrl, token, organizacionId)
      return { exito: true, resultado }
    } catch (err) {
      log.error('[Offline] Error en sync forzada:', err)
      return { exito: false, error: String(err) }
    }
  })

  // Consultar cache local
  ipcMain.handle('offline:listarCertificados', (_event, organizacionId: string, filtros?: FiltrosCertificadosCache) => {
    return listarCertificadosCache(organizacionId, filtros)
  })

  ipcMain.handle('offline:listarNotificaciones', (_event, organizacionId: string, filtros?: FiltrosNotificacionesCache) => {
    return listarNotificacionesCache(organizacionId, filtros)
  })

  ipcMain.handle('offline:listarEtiquetas', (_event, organizacionId: string) => {
    return listarEtiquetasCache(organizacionId)
  })

  // Encolar cambio offline
  ipcMain.handle('offline:encolarCambio', (_event, recurso: string, recursoId: string, operacion: string, payload: unknown) => {
    encolarCambio(recurso, recursoId, operacion, payload)
    // También actualizar local si es notificación
    if (recurso === 'notificacion' && operacion === 'patch') {
      actualizarNotificacionLocal(recursoId, payload as Record<string, unknown>)
    }
  })

  // Actualizar token para sync periódica
  ipcMain.handle('offline:actualizarToken', (_event, apiUrl: string, token: string, organizacionId: string) => {
    tokenEnMemoria = token
    apiUrlEnMemoria = apiUrl
    orgIdEnMemoria = organizacionId
  })

  // Iniciar detector de conexión con URL del API
  ipcMain.handle('offline:iniciarDetector', (_event, apiUrl: string) => {
    const urlPing = `${apiUrl}/health`
    iniciarDetectorConexion(urlPing, (conectado) => {
      ventana.webContents.send('offline:cambioEstado', conectado)
      // Al reconectar: sync automática
      if (conectado && tokenEnMemoria && apiUrlEnMemoria && orgIdEnMemoria) {
        sincronizarCompleto(apiUrlEnMemoria, tokenEnMemoria, orgIdEnMemoria)
          .then(() => ventana.webContents.send('offline:syncCompletada'))
          .catch(err => log.error('[Offline] Error sync auto:', err))
      }
    })
  })

  // Iniciar sync periódica (cada 5 min)
  iniciarSyncPeriodica(ventana)

  log.info('[Offline] Handlers registrados (7 IPC)')
}

function iniciarSyncPeriodica(ventana: BrowserWindow): void {
  if (intervaloSync) return

  intervaloSync = setInterval(async () => {
    if (!estaOnline() || !tokenEnMemoria || !apiUrlEnMemoria || !orgIdEnMemoria) return

    try {
      await sincronizarCompleto(apiUrlEnMemoria, tokenEnMemoria, orgIdEnMemoria)
      ventana.webContents.send('offline:syncCompletada')
    } catch (err) {
      log.error('[Offline] Error sync periódica:', err)
    }
  }, INTERVALO_SYNC_MS)
}

export function detenerOffline(): void {
  detenerDetectorConexion()
  if (intervaloSync) {
    clearInterval(intervaloSync)
    intervaloSync = null
  }
  tokenEnMemoria = null
  apiUrlEnMemoria = null
  orgIdEnMemoria = null
}
