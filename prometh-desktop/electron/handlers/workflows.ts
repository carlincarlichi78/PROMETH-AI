import { ipcMain, BrowserWindow } from 'electron'
import log from 'electron-log'
import { OrquestadorWorkflows } from '../workflows/orquestador-workflows'
import { obtenerCategorias } from '../workflows/workflows-predefinidos'
import type {
  WorkflowDesktop,
  ContextoEjecucionDesktop,
  ConfigSmtpGlobal,
} from '../workflows/tipos-workflows-desktop'

let orquestador: OrquestadorWorkflows | null = null

/**
 * Registra los 12 IPC handlers para workflows desktop.
 * Se invoca desde main/index.ts al iniciar la app.
 */
export function registrarHandlersWorkflows(ventana: BrowserWindow): void {
  orquestador = new OrquestadorWorkflows(ventana)

  // 1. Listar todos los workflows (predefinidos + personalizados)
  ipcMain.handle('workflows:listar', () => {
    try {
      return orquestador!.listarWorkflows()
    } catch (error) {
      log.error('[Handler:workflows] Error listando:', error)
      return []
    }
  })

  // 2. Obtener un workflow por id
  ipcMain.handle('workflows:obtener', (_event, id: string) => {
    try {
      return orquestador!.obtenerWorkflow(id)
    } catch (error) {
      log.error('[Handler:workflows] Error obteniendo workflow:', error)
      return null
    }
  })

  // 3. Guardar workflow personalizado (crear o actualizar)
  ipcMain.handle('workflows:guardar', (_event, workflow: WorkflowDesktop) => {
    try {
      orquestador!.guardarWorkflow(workflow)
      return { exito: true }
    } catch (error) {
      const mensaje = error instanceof Error ? error.message : 'Error guardando workflow'
      log.error('[Handler:workflows] Error guardando:', error)
      return { exito: false, error: mensaje }
    }
  })

  // 4. Eliminar workflow personalizado
  ipcMain.handle('workflows:eliminar', (_event, id: string) => {
    try {
      const eliminado = orquestador!.eliminarWorkflow(id)
      return { exito: eliminado, error: eliminado ? undefined : 'Workflow no encontrado' }
    } catch (error) {
      log.error('[Handler:workflows] Error eliminando:', error)
      return { exito: false, error: 'Error eliminando workflow' }
    }
  })

  // 5. Duplicar workflow
  ipcMain.handle('workflows:duplicar', (_event, id: string) => {
    try {
      const duplicado = orquestador!.duplicarWorkflow(id)
      return duplicado
        ? { exito: true, workflow: duplicado }
        : { exito: false, error: 'Workflow no encontrado' }
    } catch (error) {
      log.error('[Handler:workflows] Error duplicando:', error)
      return { exito: false, error: 'Error duplicando workflow' }
    }
  })

  // 6. Ejecutar workflow
  ipcMain.handle(
    'workflows:ejecutar',
    async (_event, id: string, contexto: Partial<ContextoEjecucionDesktop>) => {
      try {
        return await orquestador!.ejecutarWorkflow(id, contexto)
      } catch (error) {
        log.error('[Handler:workflows] Error ejecutando:', error)
        return {
          workflowId: id,
          exito: false,
          acciones: [],
          tiempoTotalMs: 0,
          error: 'Error interno al ejecutar workflow',
        }
      }
    }
  )

  // 7. Obtener historial de ejecuciones
  ipcMain.handle('workflows:historial', (_event, limite?: number) => {
    try {
      return orquestador!.obtenerHistorial(limite)
    } catch (error) {
      log.error('[Handler:workflows] Error obteniendo historial:', error)
      return []
    }
  })

  // 8. Limpiar historial antiguo
  ipcMain.handle('workflows:limpiarHistorial', (_event, mantener?: number) => {
    try {
      const eliminadas = orquestador!.limpiarHistorial(mantener)
      return { exito: true, eliminadas }
    } catch (error) {
      log.error('[Handler:workflows] Error limpiando historial:', error)
      return { exito: false, eliminadas: 0 }
    }
  })

  // 9. Obtener categorias de workflows predefinidos
  ipcMain.handle('workflows:categorias', () => {
    try {
      return obtenerCategorias()
    } catch (error) {
      log.error('[Handler:workflows] Error obteniendo categorias:', error)
      return []
    }
  })

  // 10. Obtener config SMTP global
  ipcMain.handle('workflows:obtenerSmtp', () => {
    try {
      return orquestador!.obtenerConfigSmtp() ?? null
    } catch (error) {
      log.error('[Handler:workflows] Error obteniendo SMTP:', error)
      return null
    }
  })

  // 11. Guardar config SMTP global
  ipcMain.handle('workflows:guardarSmtp', (_event, config: ConfigSmtpGlobal) => {
    try {
      orquestador!.guardarConfigSmtp(config)
      return { exito: true }
    } catch (error) {
      log.error('[Handler:workflows] Error guardando SMTP:', error)
      return { exito: false, error: 'Error guardando configuracion SMTP' }
    }
  })

  // 12. Procesar disparador (fire-and-forget, invocado internamente)
  ipcMain.handle(
    'workflows:procesarDisparador',
    async (_event, disparador: string, contexto: Partial<ContextoEjecucionDesktop>) => {
      try {
        await orquestador!.procesarDisparador(disparador, contexto)
        return { exito: true }
      } catch (error) {
        log.error('[Handler:workflows] Error procesando disparador:', error)
        return { exito: false }
      }
    }
  )

  log.info('[Handlers] Workflows: 12 handlers registrados')
}
