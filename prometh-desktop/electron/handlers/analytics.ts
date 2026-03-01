import { ipcMain, type BrowserWindow } from 'electron'
import log from 'electron-log'
import {
  recolectarMetricas,
  recolectarMetricasCerts,
  recolectarActividadTemporal,
} from '../analytics/recolector-metricas'

/**
 * Registra los 3 IPC handlers para analytics desktop.
 */
export function registrarHandlersAnalytics(_ventana: BrowserWindow): void {
  // 1. Todas las metricas
  ipcMain.handle('analytics:metricas', async () => {
    try {
      return await recolectarMetricas()
    } catch (error) {
      log.error('[Handler:analytics] Error recolectando metricas:', error)
      return null
    }
  })

  // 2. Solo metricas de certificados (rapido)
  ipcMain.handle('analytics:metricasCerts', async () => {
    try {
      return await recolectarMetricasCerts()
    } catch (error) {
      log.error('[Handler:analytics] Error recolectando metricas certs:', error)
      return null
    }
  })

  // 3. Actividad temporal (serie para graficas)
  ipcMain.handle('analytics:actividadTemporal', (_event, dias?: number) => {
    try {
      return recolectarActividadTemporal(dias)
    } catch (error) {
      log.error('[Handler:analytics] Error recolectando actividad temporal:', error)
      return []
    }
  })

  log.info('[Handlers] Analytics: 3 handlers registrados')
}
