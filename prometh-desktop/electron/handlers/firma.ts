import { ipcMain, BrowserWindow } from 'electron'
import log from 'electron-log'
import { OrquestadorFirma } from '../firma/orquestador-firma'
import { obtenerHistorialFirmas } from '../firma/historial-firmas'
import { detectarAutoFirma } from '../firma/autofirma'
import type { OpcionesFirmaLocal, OpcionesFirmaAutoFirma, OpcionesFirmaBatch } from '../firma/tipos-firma'

let orquestador: OrquestadorFirma | null = null

/**
 * Registra los 8 IPC handlers para firma digital.
 * Se invoca desde main/index.ts al iniciar la app.
 */
export function registrarHandlersFirma(ventana: BrowserWindow): void {
  orquestador = new OrquestadorFirma(ventana)

  // 1. Obtener modos de firma disponibles
  ipcMain.handle('firma:modosDisponibles', async () => {
    try {
      return await orquestador!.obtenerModosDisponibles()
    } catch (error) {
      log.error('[Handler:firma] Error obteniendo modos:', error)
      return ['local']
    }
  })

  // 2. Validar certificado para firma
  ipcMain.handle(
    'firma:validarCertificado',
    async (_event, ruta: string, password: string) => {
      try {
        return orquestador!.validarCertificado(ruta, password)
      } catch (error) {
        log.error('[Handler:firma] Error validando certificado:', error)
        return { valido: false, error: 'Error interno al validar certificado' }
      }
    },
  )

  // 3. Firma PAdES local
  ipcMain.handle(
    'firma:firmarLocal',
    async (_event, opciones: OpcionesFirmaLocal, certificadoSerial: string) => {
      try {
        return await orquestador!.firmar('local', opciones, certificadoSerial)
      } catch (error) {
        log.error('[Handler:firma] Error en firma local:', error)
        return {
          exito: false,
          modo: 'local' as const,
          error: 'Error interno al firmar PDF',
        }
      }
    },
  )

  // 4. Firma via AutoFirma
  ipcMain.handle(
    'firma:firmarAutoFirma',
    async (_event, opciones: OpcionesFirmaAutoFirma, certificadoSerial: string) => {
      try {
        return await orquestador!.firmar('autofirma', opciones, certificadoSerial)
      } catch (error) {
        log.error('[Handler:firma] Error en AutoFirma:', error)
        return {
          exito: false,
          modo: 'autofirma' as const,
          error: 'Error interno al firmar con AutoFirma',
        }
      }
    },
  )

  // 5. Firma batch (multiples PDFs)
  ipcMain.handle(
    'firma:firmarBatch',
    async (_event, opciones: OpcionesFirmaBatch) => {
      try {
        return await orquestador!.firmarBatch(opciones)
      } catch (error) {
        log.error('[Handler:firma] Error en firma batch:', error)
        return []
      }
    },
  )

  // 6. Obtener historial de firmas
  ipcMain.handle('firma:obtenerHistorial', () => {
    try {
      return obtenerHistorialFirmas()
    } catch (error) {
      log.error('[Handler:firma] Error obteniendo historial:', error)
      return { documentos: [] }
    }
  })

  // 7. Sincronizar firmas con cloud
  ipcMain.handle(
    'firma:sincronizarCloud',
    async (
      _event,
      apiUrl: string,
      token: string,
      mapaCertificados?: Record<string, string>,
    ) => {
      try {
        return await orquestador!.sincronizarConCloud(apiUrl, token, mapaCertificados)
      } catch (error) {
        log.error('[Handler:firma] Error sincronizando:', error)
        return { sincronizados: 0, errores: 1 }
      }
    },
  )

  // 8. Detectar si AutoFirma esta instalado
  ipcMain.handle('firma:detectarAutoFirma', async () => {
    try {
      return await detectarAutoFirma()
    } catch (error) {
      log.error('[Handler:firma] Error detectando AutoFirma:', error)
      return false
    }
  })

  log.info('[Handlers] Firma: 8 handlers registrados')
}
