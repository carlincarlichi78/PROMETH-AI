import { ipcMain, type BrowserWindow } from 'electron'
import log from 'electron-log'
import { GestorTray } from '../tray/gestor-tray'
import { setGestorTray, ejecutarChequeosPeriodicos } from '../tray/servicio-notificaciones'
import {
  obtenerEstadoTray,
  obtenerNotificaciones,
  marcarLeida,
  marcarTodasLeidas,
  obtenerConfig,
  guardarConfig,
  limpiarAntiguas,
} from '../tray/persistencia-tray'
import type { ConfigNotificacionesDesktop } from '../tray/tipos-tray'

let gestor: GestorTray | null = null

/**
 * Registra los 8 IPC handlers para el tray y notificaciones desktop.
 * Inicia el tray icon automaticamente.
 */
export function registrarHandlersTray(ventana: BrowserWindow): void {
  gestor = new GestorTray(ventana)
  gestor.iniciar()
  setGestorTray(gestor)

  // Actualizar badge al iniciar
  const estadoInicial = obtenerEstadoTray()
  gestor.actualizarBadge(estadoInicial.pendientes)

  // 1. Obtener estado del tray (pendientes + ultima)
  ipcMain.handle('tray:obtenerEstado', () => {
    try {
      return obtenerEstadoTray()
    } catch (error) {
      log.error('[Handler:tray] Error obteniendo estado:', error)
      return { pendientes: 0 }
    }
  })

  // 2. Listar notificaciones
  ipcMain.handle('tray:listarNotificaciones', (_event, limite?: number) => {
    try {
      return obtenerNotificaciones(limite)
    } catch (error) {
      log.error('[Handler:tray] Error listando notificaciones:', error)
      return []
    }
  })

  // 3. Marcar una como leida
  ipcMain.handle('tray:marcarLeida', (_event, id: string) => {
    try {
      const marcada = marcarLeida(id)
      if (marcada && gestor) {
        const estado = obtenerEstadoTray()
        gestor.actualizarBadge(estado.pendientes)
      }
      return { exito: marcada }
    } catch (error) {
      log.error('[Handler:tray] Error marcando leida:', error)
      return { exito: false }
    }
  })

  // 4. Marcar todas como leidas
  ipcMain.handle('tray:marcarTodasLeidas', () => {
    try {
      const marcadas = marcarTodasLeidas()
      if (gestor) {
        gestor.actualizarBadge(0)
      }
      return { exito: true, marcadas }
    } catch (error) {
      log.error('[Handler:tray] Error marcando todas leidas:', error)
      return { exito: false, marcadas: 0 }
    }
  })

  // 5. Obtener config
  ipcMain.handle('tray:obtenerConfig', () => {
    try {
      return obtenerConfig()
    } catch (error) {
      log.error('[Handler:tray] Error obteniendo config:', error)
      return null
    }
  })

  // 6. Guardar config
  ipcMain.handle('tray:guardarConfig', (_event, config: ConfigNotificacionesDesktop) => {
    try {
      guardarConfig(config)
      return { exito: true }
    } catch (error) {
      log.error('[Handler:tray] Error guardando config:', error)
      return { exito: false }
    }
  })

  // 7. Limpiar antiguas
  ipcMain.handle('tray:limpiarAntiguas', (_event, mantener?: number) => {
    try {
      const eliminadas = limpiarAntiguas(mantener)
      return { exito: true, eliminadas }
    } catch (error) {
      log.error('[Handler:tray] Error limpiando antiguas:', error)
      return { exito: false, eliminadas: 0 }
    }
  })

  // 8. Ejecutar chequeo manual
  ipcMain.handle('tray:ejecutarChequeo', async () => {
    try {
      const nuevas = await ejecutarChequeosPeriodicos()
      return { exito: true, nuevas }
    } catch (error) {
      log.error('[Handler:tray] Error ejecutando chequeo:', error)
      return { exito: false, nuevas: 0 }
    }
  })

  log.info('[Handlers] Tray: 8 handlers registrados, tray icon iniciado')
}

/** Destruye el tray (al cerrar la app) */
export function destruirTray(): void {
  gestor?.destruir()
}
