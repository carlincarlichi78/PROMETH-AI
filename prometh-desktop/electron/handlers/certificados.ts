import { ipcMain, dialog, app, type BrowserWindow } from 'electron'
import { join } from 'path'
import { existsSync, mkdirSync, readdirSync, readFileSync } from 'fs'
import log from 'electron-log'
import { leerCertificadoP12 } from '../certs/lector'
import {
  instalarCertificado,
  desinstalarCertificado,
  listarCertificadosInstalados,
  exportarCertificadoPfx,
} from '../certs/almacen'
import { iniciarWatcher, detenerWatcher } from '../certs/watcher'
import { aislarCertificado, restaurarCertificado } from '../certs/aislamiento'
import { sincronizarCertificadosDesdeCloud } from '../certs/sincronizador-cloud'
import type { CertificadoLocal } from '../certs/tipos'

// Estado local: certificado activo
let certificadoActivo: string | null = null // numeroSerie del cert activo

/**
 * Carpeta por defecto donde se buscan certificados P12/PFX.
 */
function carpetaCertificados(): string {
  const docs = app.getPath('documents')
  const carpeta = join(docs, 'CertiGestor', 'certificados')
  if (!existsSync(carpeta)) {
    mkdirSync(carpeta, { recursive: true })
  }
  return carpeta
}

/**
 * Registra todos los IPC handlers de certificados.
 * Debe llamarse una vez desde main/index.ts.
 */
export function registrarHandlersCertificados(ventana: BrowserWindow): void {
  // Seleccionar archivo P12/PFX con dialog nativo
  ipcMain.handle('certs:seleccionarArchivo', async (_event, password: string) => {
    const resultado = await dialog.showOpenDialog(ventana, {
      title: 'Seleccionar certificado P12/PFX',
      filters: [
        { name: 'Certificados', extensions: ['p12', 'pfx'] },
      ],
      properties: ['openFile'],
    })

    if (resultado.canceled || resultado.filePaths.length === 0) {
      return null
    }

    const ruta = resultado.filePaths[0]
    try {
      return leerCertificadoP12(ruta, password)
    } catch (error) {
      const mensaje = error instanceof Error ? error.message : 'Error leyendo certificado'
      log.error(`Error leyendo P12: ${mensaje}`)
      return { exito: false, error: mensaje }
    }
  })

  // Leer certificado P12/PFX dado ruta y password
  ipcMain.handle('certs:leerP12', (_event, ruta: string, password: string) => {
    try {
      return { exito: true, datos: leerCertificadoP12(ruta, password) }
    } catch (error) {
      const mensaje = error instanceof Error ? error.message : 'Error leyendo certificado'
      return { exito: false, error: mensaje }
    }
  })

  // Listar archivos P12/PFX en la carpeta de certificados
  ipcMain.handle('certs:listarLocales', () => {
    const carpeta = carpetaCertificados()
    try {
      const archivos = readdirSync(carpeta)
        .filter((f) => /\.(p12|pfx)$/i.test(f))
        .map((f) => join(carpeta, f))
      return archivos
    } catch {
      return []
    }
  })

  // Instalar certificado en almacen de Windows
  ipcMain.handle('certs:instalarEnWindows', async (_event, rutaPfx: string, password: string) => {
    try {
      return await instalarCertificado(rutaPfx, password)
    } catch (error) {
      log.error(`[Certs] Error instalando certificado: ${(error as Error).message}`)
      return { exito: false, error: (error as Error).message }
    }
  })

  // Desinstalar certificado del almacen de Windows
  ipcMain.handle('certs:desinstalarDeWindows', async (_event, thumbprint: string) => {
    try {
      return await desinstalarCertificado(thumbprint)
    } catch (error) {
      log.error(`[Certs] Error desinstalando certificado: ${(error as Error).message}`)
      return { exito: false, error: (error as Error).message }
    }
  })

  // Listar certificados instalados en Windows
  // Mapea al formato que espera la UI (serialNumber, issuer, validTo)
  ipcMain.handle('certs:listarInstalados', async () => {
    try {
      const certs = await listarCertificadosInstalados()
      return certs.map((c) => ({
        thumbprint: c.thumbprint,
        subject: c.subject,
        issuer: c.emisor,
        serialNumber: c.numeroSerie,
        validTo: c.fechaVencimiento,
        hasPrivateKey: true,
      }))
    } catch (error) {
      log.error(`[Certs] Error listando certificados: ${(error as Error).message}`)
      return []
    }
  })

  // Activar un certificado como el activo
  ipcMain.handle('certs:activar', (_event, numeroSerie: string) => {
    certificadoActivo = numeroSerie
    log.info(`Certificado activado: ${numeroSerie}`)
    return { exito: true }
  })

  // Desactivar el certificado activo
  ipcMain.handle('certs:desactivar', () => {
    log.info(`Certificado desactivado: ${certificadoActivo}`)
    certificadoActivo = null
    return { exito: true }
  })

  // Obtener el certificado activo
  ipcMain.handle('certs:obtenerActivo', () => {
    return certificadoActivo
  })

  // Exportar certificado a PFX
  ipcMain.handle(
    'certs:exportarPfx',
    async (_event, thumbprint: string, password: string) => {
      const resultado = await dialog.showSaveDialog(ventana, {
        title: 'Exportar certificado como PFX',
        defaultPath: join(app.getPath('downloads'), 'certificado.pfx'),
        filters: [{ name: 'PFX', extensions: ['pfx'] }],
      })

      if (resultado.canceled || !resultado.filePath) {
        return { exito: false, error: 'Cancelado por el usuario' }
      }

      return exportarCertificadoPfx(thumbprint, resultado.filePath, password)
    },
  )

  // Sincronizar certificado local con API cloud
  ipcMain.handle(
    'certs:sincronizarConCloud',
    async (_event, ruta: string, password: string, apiUrl: string, token: string) => {
      try {
        const buffer = readFileSync(ruta)
        const formData = new FormData()
        formData.append(
          'archivo',
          new Blob([buffer], { type: 'application/x-pkcs12' }),
          ruta.split(/[/\\]/).pop() ?? 'certificado.p12',
        )
        if (password) {
          formData.append('password', password)
        }

        const respuesta = await fetch(`${apiUrl}/certificados/importar`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
          body: formData,
        })

        const datos = await respuesta.json()
        if (!respuesta.ok) {
          return { exito: false, error: datos.error ?? 'Error al sincronizar' }
        }
        return { exito: true, datos }
      } catch (error) {
        const mensaje = error instanceof Error ? error.message : 'Error de conexion'
        log.error(`Error sincronizando con cloud: ${mensaje}`)
        return { exito: false, error: mensaje }
      }
    },
  )

  // Sincronizar certificados desde cloud al Windows Store
  ipcMain.handle(
    'certs:sincronizarDesdeCloud',
    async (_event, apiUrl: string, token: string) => {
      try {
        return await sincronizarCertificadosDesdeCloud(apiUrl, token)
      } catch (error) {
        const mensaje = error instanceof Error ? error.message : 'Error de sincronizacion'
        log.error(`Error sync cloud: ${mensaje}`)
        return { instalados: [], yaExistentes: 0, errores: [{ id: 'general', error: mensaje }] }
      }
    },
  )

  // Aislar certificado para AutoFirma
  ipcMain.handle('certs:aislar', async (_event, thumbprint: string) => {
    return aislarCertificado(thumbprint)
  })

  // Restaurar acceso al certificado
  ipcMain.handle('certs:restaurar', async (_event, thumbprint: string) => {
    return restaurarCertificado(thumbprint)
  })

  // Iniciar file watcher
  ipcMain.handle('certs:iniciarWatcher', (_event, carpeta?: string) => {
    const dir = carpeta ?? carpetaCertificados()
    iniciarWatcher(dir, (ruta) => {
      ventana.webContents.send('certs:nuevoArchivo', ruta)
    })
    return { exito: true }
  })

  // Detener file watcher
  ipcMain.handle('certs:detenerWatcher', () => {
    detenerWatcher()
    return { exito: true }
  })

  // Obtener ruta de la carpeta de certificados
  ipcMain.handle('certs:obtenerCarpeta', () => {
    return carpetaCertificados()
  })

  log.info('Handlers de certificados registrados')
}
