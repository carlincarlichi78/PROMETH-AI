import { ipcMain, type BrowserWindow } from 'electron'
import log from 'electron-log'
import { Factory } from '../scraping/factory'
import type { ConfigScraping, EstadoCola } from '../scraping/tipos'

const factory = new Factory()

/**
 * Registra los IPC handlers de scraping.
 * Conecta el callback de progreso al renderer via webContents.send.
 */
export function registrarHandlersScraping(ventana: BrowserWindow): void {
  // Callback de progreso → envia eventos al renderer
  factory.onProgreso((estado: EstadoCola) => {
    if (!ventana.isDestroyed()) {
      ventana.webContents.send('scraping:progreso', estado)
    }
  })

  /** Obtener estado actual de la cola */
  ipcMain.handle('scraping:obtenerEstado', () => {
    return factory.obtenerEstado()
  })

  /** Configurar parametros de scraping */
  ipcMain.handle(
    'scraping:configurar',
    (_event, config: Partial<ConfigScraping>) => {
      factory.configurar(config)
      log.info('Scraping configurado:', config)
      return factory.obtenerConfig()
    },
  )

  /** Obtener configuracion actual */
  ipcMain.handle('scraping:obtenerConfig', () => {
    return factory.obtenerConfig()
  })

  /**
   * Iniciar la cola de procesamiento.
   * Las cadenas se agregan externamente (D4-D6 implementaran scrapers concretos
   * que construyen cadenas y las agregan a la factory).
   */
  ipcMain.handle('scraping:iniciar', async () => {
    try {
      await factory.iniciar()
      return { exito: true }
    } catch (error) {
      const mensaje =
        error instanceof Error ? error.message : 'Error desconocido'
      log.error('Error al iniciar scraping:', mensaje)
      return { exito: false, error: mensaje }
    }
  })

  /** Detener la cola de procesamiento */
  ipcMain.handle('scraping:detener', () => {
    factory.detener()
    return { exito: true }
  })

  /** Limpiar cadenas de la cola */
  ipcMain.handle('scraping:limpiar', () => {
    factory.limpiar()
    return { exito: true }
  })

  log.info('Handlers scraping registrados')
}

/** Exportar factory para que los scrapers concretos (D4-D6) puedan agregar cadenas */
export { factory }
