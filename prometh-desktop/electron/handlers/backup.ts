import { ipcMain, dialog, type BrowserWindow } from 'electron'
import { readFileSync, writeFileSync } from 'fs'
import log from 'electron-log'
import { exportarConfiguracion, importarConfiguracion } from '../backup/servicio-backup'
import { cifrarBackup, descifrarBackup } from '../backup/cifrado-backup'
import type { SeccionBackup } from '../backup/tipos-backup'

/**
 * Registra los 3 IPC handlers para backup/restore de configuracion.
 */
export function registrarHandlersBackup(ventana: BrowserWindow): void {
  // 1. Exportar configuracion cifrada
  ipcMain.handle(
    'backup:exportar',
    async (_event, opciones: { secciones: SeccionBackup[]; password: string }) => {
      try {
        const datos = exportarConfiguracion({ secciones: opciones.secciones, password: opciones.password })
        const buffer = cifrarBackup(datos, opciones.password)

        const resultado = await dialog.showSaveDialog(ventana, {
          title: 'Exportar configuración CertiGestor',
          defaultPath: `certigestor-backup-${new Date().toISOString().slice(0, 10)}.certigestor-backup`,
          filters: [{ name: 'CertiGestor Backup', extensions: ['certigestor-backup'] }],
        })

        if (resultado.canceled || !resultado.filePath) {
          return { exito: false, error: 'Exportación cancelada' }
        }

        writeFileSync(resultado.filePath, buffer)
        log.info(`[Backup] Exportado a: ${resultado.filePath} (${opciones.secciones.length} secciones)`)
        return { exito: true, ruta: resultado.filePath }
      } catch (error) {
        log.error('[Backup] Error exportando:', error)
        return { exito: false, error: error instanceof Error ? error.message : 'Error desconocido' }
      }
    },
  )

  // 2. Importar configuracion cifrada
  ipcMain.handle('backup:importar', async (_event, opciones: { password: string }) => {
    try {
      const resultado = await dialog.showOpenDialog(ventana, {
        title: 'Importar configuración CertiGestor',
        filters: [{ name: 'CertiGestor Backup', extensions: ['certigestor-backup'] }],
        properties: ['openFile'],
      })

      if (resultado.canceled || resultado.filePaths.length === 0) {
        return { exito: false, seccionesImportadas: [], error: 'Importación cancelada' }
      }

      const buffer = readFileSync(resultado.filePaths[0])
      const datos = descifrarBackup(buffer, opciones.password)
      const importResult = importarConfiguracion(datos)

      log.info(`[Backup] Importadas ${importResult.seccionesImportadas.length} secciones`)
      return importResult
    } catch (error) {
      log.error('[Backup] Error importando:', error)
      return {
        exito: false,
        seccionesImportadas: [],
        error: error instanceof Error ? error.message : 'Error desconocido',
      }
    }
  })

  // 3. Previsualizar contenido sin importar
  ipcMain.handle('backup:previsualizar', async (_event, opciones: { password: string }) => {
    try {
      const resultado = await dialog.showOpenDialog(ventana, {
        title: 'Previsualizar backup CertiGestor',
        filters: [{ name: 'CertiGestor Backup', extensions: ['certigestor-backup'] }],
        properties: ['openFile'],
      })

      if (resultado.canceled || resultado.filePaths.length === 0) {
        return { exito: false, error: 'Selección cancelada' }
      }

      const buffer = readFileSync(resultado.filePaths[0])
      const datos = descifrarBackup(buffer, opciones.password)

      return {
        exito: true,
        secciones: Object.keys(datos.secciones) as SeccionBackup[],
        fecha: datos.fecha,
        version: datos.version,
      }
    } catch (error) {
      log.error('[Backup] Error previsualizando:', error)
      return { exito: false, error: error instanceof Error ? error.message : 'Error desconocido' }
    }
  })

  log.info('[Handlers] Backup: 3 handlers registrados')
}
