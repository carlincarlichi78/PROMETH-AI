import { ipcMain, type BrowserWindow } from 'electron'
import log from 'electron-log'
import { randomUUID } from 'crypto'
import { MotorScheduler } from '../scheduler/motor-scheduler'
import {
  obtenerTareas,
  obtenerTarea,
  guardarTarea,
  eliminarTarea,
  toggleTarea,
  obtenerEjecuciones,
  limpiarEjecucionesAntiguas,
} from '../scheduler/persistencia-scheduler'
import type { TareaProgramada } from '../scheduler/tipos-scheduler'

let motor: MotorScheduler | null = null

/**
 * Registra los 10 IPC handlers para el scheduler desktop.
 * Inicia el motor automaticamente.
 */
export function registrarHandlersScheduler(ventana: BrowserWindow): void {
  motor = new MotorScheduler(ventana)
  motor.iniciar()

  // 1. Obtener estado del scheduler
  ipcMain.handle('scheduler:obtenerEstado', () => {
    try {
      return motor!.obtenerEstado()
    } catch (error) {
      log.error('[Handler:scheduler] Error obteniendo estado:', error)
      return { activo: false, tareasActivas: 0 }
    }
  })

  // 2. Listar todas las tareas
  ipcMain.handle('scheduler:listarTareas', () => {
    try {
      return obtenerTareas()
    } catch (error) {
      log.error('[Handler:scheduler] Error listando tareas:', error)
      return []
    }
  })

  // 3. Obtener una tarea por id
  ipcMain.handle('scheduler:obtenerTarea', (_event, id: string) => {
    try {
      return obtenerTarea(id)
    } catch (error) {
      log.error('[Handler:scheduler] Error obteniendo tarea:', error)
      return null
    }
  })

  // 4. Crear tarea nueva
  ipcMain.handle('scheduler:crearTarea', (_event, datos: Omit<TareaProgramada, 'id' | 'creadoEn' | 'actualizadoEn'>) => {
    try {
      const ahora = new Date().toISOString()
      const tarea: TareaProgramada = {
        ...datos,
        id: randomUUID(),
        creadoEn: ahora,
        actualizadoEn: ahora,
      }
      // Calcular proxima ejecucion
      tarea.proximaEjecucion = motor!.calcularProximaEjecucion(tarea)
      guardarTarea(tarea)
      return { exito: true, tarea }
    } catch (error) {
      const mensaje = error instanceof Error ? error.message : 'Error creando tarea'
      log.error('[Handler:scheduler] Error creando tarea:', error)
      return { exito: false, error: mensaje }
    }
  })

  // 5. Actualizar tarea
  ipcMain.handle('scheduler:actualizarTarea', (_event, id: string, datos: Partial<TareaProgramada>) => {
    try {
      const existente = obtenerTarea(id)
      if (!existente) return { exito: false, error: 'Tarea no encontrada' }

      const actualizada: TareaProgramada = {
        ...existente,
        ...datos,
        id, // no permitir cambiar id
        actualizadoEn: new Date().toISOString(),
      }
      // Recalcular proxima ejecucion si cambio frecuencia/hora
      if (datos.frecuencia || datos.horaEjecucion || datos.diaSemana) {
        actualizada.proximaEjecucion = motor!.calcularProximaEjecucion(actualizada)
      }
      guardarTarea(actualizada)
      return { exito: true }
    } catch (error) {
      log.error('[Handler:scheduler] Error actualizando tarea:', error)
      return { exito: false, error: 'Error actualizando tarea' }
    }
  })

  // 6. Eliminar tarea
  ipcMain.handle('scheduler:eliminarTarea', (_event, id: string) => {
    try {
      const eliminada = eliminarTarea(id)
      return { exito: eliminada, error: eliminada ? undefined : 'Tarea no encontrada' }
    } catch (error) {
      log.error('[Handler:scheduler] Error eliminando tarea:', error)
      return { exito: false, error: 'Error eliminando tarea' }
    }
  })

  // 7. Toggle activar/desactivar tarea
  ipcMain.handle('scheduler:toggleTarea', (_event, id: string) => {
    try {
      const resultado = toggleTarea(id)
      if (!resultado) return { exito: false, error: 'Tarea no encontrada' }
      return { exito: true, activa: resultado.activa }
    } catch (error) {
      log.error('[Handler:scheduler] Error toggling tarea:', error)
      return { exito: false, error: 'Error cambiando estado de tarea' }
    }
  })

  // 8. Ejecutar tarea ahora (manualmente)
  ipcMain.handle('scheduler:ejecutarAhora', async (_event, id: string) => {
    try {
      return await motor!.ejecutarManual(id)
    } catch (error) {
      log.error('[Handler:scheduler] Error ejecutando tarea:', error)
      return { exito: false, error: 'Error ejecutando tarea' }
    }
  })

  // 9. Historial de ejecuciones
  ipcMain.handle('scheduler:historial', (_event, limite?: number) => {
    try {
      return obtenerEjecuciones(limite)
    } catch (error) {
      log.error('[Handler:scheduler] Error obteniendo historial:', error)
      return []
    }
  })

  // 10. Limpiar historial antiguo
  ipcMain.handle('scheduler:limpiarHistorial', (_event, mantener?: number) => {
    try {
      const eliminadas = limpiarEjecucionesAntiguas(mantener)
      return { exito: true, eliminadas }
    } catch (error) {
      log.error('[Handler:scheduler] Error limpiando historial:', error)
      return { exito: false, eliminadas: 0 }
    }
  })

  log.info('[Handlers] Scheduler: 10 handlers registrados, motor iniciado')
}

/** Detiene el motor del scheduler */
export function detenerScheduler(): void {
  motor?.detener()
}
