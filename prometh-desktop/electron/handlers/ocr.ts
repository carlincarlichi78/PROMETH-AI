import { ipcMain } from 'electron'
import log from 'electron-log'
import { extraerTextoPdf } from '../ocr/extraer-texto-pdf'
import { workerActivo } from '../ocr/ocr-imagen'

/**
 * Registra los IPC handlers de OCR.
 */
export function registrarHandlersOcr(): void {
  /** Extraer texto de un PDF (nativo + OCR fallback) */
  ipcMain.handle(
    'ocr:extraerTexto',
    async (_event, rutaPdf: string): Promise<string | null> => {
      try {
        log.info(`[OCR] Extrayendo texto de: ${rutaPdf}`)
        return await extraerTextoPdf(rutaPdf)
      } catch (error) {
        log.error(`[OCR] Error extrayendo texto: ${(error as Error).message}`)
        return null
      }
    },
  )

  /** Estado del modulo OCR */
  ipcMain.handle('ocr:estado', () => {
    return {
      activo: workerActivo(),
      idioma: 'spa',
    }
  })

  log.info('Handlers OCR registrados')
}
