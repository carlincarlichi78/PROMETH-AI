import { ipcMain, shell, type BrowserWindow } from 'electron'
import { join } from 'path'
import { existsSync, mkdirSync } from 'fs'
import { readdir, stat, unlink, rm } from 'fs/promises'
import { app } from 'electron'
import log from 'electron-log'
import { CATALOGO_DOCUMENTOS } from '../scraping/documentales/catalogo'
import { OrquestadorDocumentales } from '../scraping/documentales/orquestador-documentales'
import {
  obtenerHistorial,
  obtenerUltimosResultados,
  limpiarHistorial,
  obtenerConfig,
  guardarConfig,
} from '../scraping/documentales/historial-descargas'
import {
  sincronizarDocsConCloud,
  sincronizarConfigConCloud,
  recuperarConfigDesdeCloud,
} from '../scraping/documentales/sincronizar-docs'
import { factory } from './scraping'
import type {
  ConfigDocumentosCertificado,
  TipoDocumento,
  ResultadoDescarga,
  DefinicionDocumento,
  RegistroHistorialDescarga,
} from '../scraping/documentales/tipos-documentales'
import { resolverNombreCarpeta } from '../certs/nombre-carpeta'

/** Resuelve la ruta completa de la carpeta de un certificado */
async function resolverCarpetaCertificado(serialNumber: string): Promise<string> {
  const baseDescargas = join(app.getPath('documents'), 'CertiGestor', 'descargas')
  const nombreCarpeta = await resolverNombreCarpeta(serialNumber)
  const subcarpeta = nombreCarpeta ?? serialNumber
  let carpeta = join(baseDescargas, subcarpeta)
  // Fallback: si no existe con nombre titular, probar con serial
  if (!existsSync(carpeta) && nombreCarpeta) {
    const carpetaSerial = join(baseDescargas, serialNumber)
    if (existsSync(carpetaSerial)) {
      carpeta = carpetaSerial
    }
  }
  return carpeta
}

/** Info de un archivo descargado */
interface ArchivoDescargado {
  nombre: string
  ruta: string
  fecha: string
  tamano: number
}

/** Estadisticas de carpeta */
interface EstadisticasCarpeta {
  totalArchivos: number
  tamanoTotal: number
  debugCount: number
}

/**
 * Registra los IPC handlers de documentales.
 */
export function registrarHandlersDocumentales(_ventana: BrowserWindow): void {
  /** Retorna el catalogo completo de documentos disponibles */
  ipcMain.handle(
    'docs:obtenerCatalogo',
    (): DefinicionDocumento[] => {
      return CATALOGO_DOCUMENTOS
    },
  )

  /** Obtiene la config de documentos activos para un certificado */
  ipcMain.handle(
    'docs:obtenerConfig',
    (
      _event,
      certificadoSerial: string,
    ): { documentosActivos: TipoDocumento[]; datosExtra?: Record<string, unknown> } => {
      return obtenerConfig(certificadoSerial)
    },
  )

  /** Guarda la config de documentos activos para un certificado */
  ipcMain.handle(
    'docs:guardarConfig',
    (
      _event,
      certificadoSerial: string,
      documentosActivos: TipoDocumento[],
      datosExtra?: Record<string, unknown>,
    ): void => {
      guardarConfig(certificadoSerial, documentosActivos, datosExtra)
    },
  )

  /** Descarga un documento individual */
  ipcMain.handle(
    'docs:descargarDocumento',
    async (
      _event,
      tipo: TipoDocumento,
      certificadoSerial: string,
      datosExtra?: Record<string, unknown>,
    ): Promise<ResultadoDescarga> => {
      log.info(
        `[DOC Handler] Descargando ${tipo} para cert: ${certificadoSerial}`,
      )

      // Resolver nombre legible del titular para la carpeta de descargas
      const nombreCarpeta = await resolverNombreCarpeta(certificadoSerial)
      log.info(`[DOC Handler] Carpeta: ${nombreCarpeta ?? certificadoSerial}`)

      const orquestador = new OrquestadorDocumentales()
      return orquestador.descargarDocumento(
        tipo,
        certificadoSerial,
        nombreCarpeta ? { nombreCarpeta } : undefined,
        datosExtra,
      )
    },
  )

  /** Descarga batch: construye cadenas y ejecuta via Factory */
  ipcMain.handle(
    'docs:descargarBatch',
    async (
      _event,
      configs: ConfigDocumentosCertificado[],
    ): Promise<{ exito: boolean; error?: string }> => {
      log.info(
        `[DOC Handler] Descarga batch para ${configs.length} certificados`,
      )

      try {
        const orquestador = new OrquestadorDocumentales()

        factory.limpiar()
        orquestador.construirCadenasBatch(factory, configs)
        await factory.iniciar()

        return { exito: true }
      } catch (error) {
        const msg = error instanceof Error ? error.message : 'Error desconocido'
        log.error(`[DOC Handler] Error en batch: ${msg}`)
        return { exito: false, error: msg }
      }
    },
  )

  /** Obtiene el historial de descargas (filtrado por certificado opcional) */
  ipcMain.handle(
    'docs:obtenerHistorial',
    (
      _event,
      certificadoSerial?: string,
    ): RegistroHistorialDescarga[] => {
      return obtenerHistorial(certificadoSerial)
    },
  )

  /** Abre la carpeta de descargas (base o por certificado) en el explorador */
  ipcMain.handle(
    'docs:abrirCarpeta',
    async (
      _event,
      certificadoSerial?: string,
    ): Promise<{ exito: boolean; error?: string }> => {
      const baseDescargas = join(
        app.getPath('documents'),
        'CertiGestor',
        'descargas',
      )

      let carpeta = baseDescargas
      if (certificadoSerial) {
        // Intentar usar nombre legible del titular
        const nombreCarpeta = await resolverNombreCarpeta(certificadoSerial)
        const subcarpeta = nombreCarpeta ?? certificadoSerial
        carpeta = join(baseDescargas, subcarpeta)
        // Fallback: si no existe con nombre titular, probar con serial
        if (!existsSync(carpeta) && nombreCarpeta) {
          const carpetaSerial = join(baseDescargas, certificadoSerial)
          if (existsSync(carpetaSerial)) {
            carpeta = carpetaSerial
          }
        }
      }

      try {
        if (!existsSync(carpeta)) {
          mkdirSync(carpeta, { recursive: true })
        }
        const errorMsg = await shell.openPath(carpeta)
        if (errorMsg) {
          log.warn(`Error abriendo carpeta ${carpeta}: ${errorMsg}`)
          return { exito: false, error: errorMsg }
        }
        return { exito: true }
      } catch (error) {
        const msg = error instanceof Error ? error.message : 'Error desconocido'
        return { exito: false, error: msg }
      }
    },
  )

  /** Obtiene el ultimo resultado de cada tipo de documento (estado dinamico) */
  ipcMain.handle(
    'docs:ultimosResultados',
    (
      _event,
      certificadoSerial?: string,
    ): Record<string, { exito: boolean; fecha: string; error?: string }> => {
      return obtenerUltimosResultados(certificadoSerial)
    },
  )

  /** Limpia todo el historial de descargas */
  ipcMain.handle('docs:limpiarHistorial', (): void => {
    limpiarHistorial()
  })

  /** Lista archivos PDF descargados para un certificado */
  ipcMain.handle(
    'docs:listarArchivos',
    async (_event, serialNumber: string): Promise<ArchivoDescargado[]> => {
      const carpeta = await resolverCarpetaCertificado(serialNumber)
      if (!existsSync(carpeta)) return []

      try {
        const entries = await readdir(carpeta)
        const archivos: ArchivoDescargado[] = []

        for (const entry of entries) {
          // Excluir carpeta _debug y archivos debug_ sueltos (legacy)
          if (entry === '_debug' || entry.startsWith('debug_')) continue
          // Solo PDFs
          if (!entry.toLowerCase().endsWith('.pdf')) continue

          const ruta = join(carpeta, entry)
          const info = await stat(ruta)
          if (!info.isFile()) continue

          archivos.push({
            nombre: entry,
            ruta,
            fecha: info.mtime.toISOString(),
            tamano: info.size,
          })
        }

        // Ordenar por fecha descendente
        return archivos.sort((a, b) => new Date(b.fecha).getTime() - new Date(a.fecha).getTime())
      } catch (err) {
        log.warn(`[DOC Handler] Error listando archivos: ${(err as Error).message}`)
        return []
      }
    },
  )

  /** Elimina un archivo descargado (validando ruta dentro de carpeta base) */
  ipcMain.handle(
    'docs:eliminarArchivo',
    async (_event, ruta: string): Promise<{ exito: boolean; error?: string }> => {
      const baseDescargas = join(app.getPath('documents'), 'CertiGestor', 'descargas')
      // Seguridad: validar que la ruta esta dentro de la carpeta base
      const rutaNormalizada = join(ruta)
      if (!rutaNormalizada.startsWith(baseDescargas)) {
        return { exito: false, error: 'Ruta fuera de la carpeta de descargas' }
      }

      try {
        await unlink(ruta)
        return { exito: true }
      } catch (err) {
        return { exito: false, error: (err as Error).message }
      }
    },
  )

  /** Limpia archivos de debug (subcarpeta _debug/ + archivos debug_* legacy) */
  ipcMain.handle(
    'docs:limpiarDebug',
    async (_event, serialNumber: string): Promise<{ exito: boolean; eliminados: number }> => {
      const carpeta = await resolverCarpetaCertificado(serialNumber)
      if (!existsSync(carpeta)) return { exito: true, eliminados: 0 }

      let eliminados = 0
      try {
        // Eliminar subcarpeta _debug/ completa
        const carpetaDebug = join(carpeta, '_debug')
        if (existsSync(carpetaDebug)) {
          const debugFiles = await readdir(carpetaDebug)
          eliminados += debugFiles.length
          await rm(carpetaDebug, { recursive: true })
        }

        // Eliminar archivos debug_*.png sueltos (compatibilidad pre-cambio)
        const entries = await readdir(carpeta)
        for (const entry of entries) {
          if (entry.startsWith('debug_') && entry.endsWith('.png')) {
            await unlink(join(carpeta, entry))
            eliminados++
          }
        }

        return { exito: true, eliminados }
      } catch (err) {
        log.warn(`[DOC Handler] Error limpiando debug: ${(err as Error).message}`)
        return { exito: false, eliminados }
      }
    },
  )

  /** Obtiene estadisticas de la carpeta de un certificado */
  ipcMain.handle(
    'docs:estadisticasCarpeta',
    async (_event, serialNumber: string): Promise<EstadisticasCarpeta> => {
      const carpeta = await resolverCarpetaCertificado(serialNumber)
      if (!existsSync(carpeta)) return { totalArchivos: 0, tamanoTotal: 0, debugCount: 0 }

      try {
        const entries = await readdir(carpeta)
        let totalArchivos = 0
        let tamanoTotal = 0
        let debugCount = 0

        for (const entry of entries) {
          if (entry === '_debug') {
            // Contar archivos dentro de _debug/
            const debugDir = join(carpeta, '_debug')
            const debugEntries = await readdir(debugDir)
            debugCount += debugEntries.length
            continue
          }
          if (entry.startsWith('debug_') && entry.endsWith('.png')) {
            debugCount++
            continue
          }
          if (!entry.toLowerCase().endsWith('.pdf')) continue

          const ruta = join(carpeta, entry)
          const info = await stat(ruta)
          if (!info.isFile()) continue

          totalArchivos++
          tamanoTotal += info.size
        }

        return { totalArchivos, tamanoTotal, debugCount }
      } catch (err) {
        log.warn(`[DOC Handler] Error estadisticas: ${(err as Error).message}`)
        return { totalArchivos: 0, tamanoTotal: 0, debugCount: 0 }
      }
    },
  )

  /** Abre un archivo descargado con la aplicacion por defecto */
  ipcMain.handle(
    'docs:abrirArchivo',
    async (_event, ruta: string): Promise<{ exito: boolean; error?: string }> => {
      const baseDescargas = join(app.getPath('documents'), 'CertiGestor', 'descargas')
      const rutaNormalizada = join(ruta)
      if (!rutaNormalizada.startsWith(baseDescargas)) {
        return { exito: false, error: 'Ruta fuera de la carpeta de descargas' }
      }

      try {
        const errorMsg = await shell.openPath(ruta)
        if (errorMsg) return { exito: false, error: errorMsg }
        return { exito: true }
      } catch (err) {
        return { exito: false, error: (err as Error).message }
      }
    },
  )

  /** Sincroniza historial de descargas con el servidor cloud */
  ipcMain.handle(
    'docs:sincronizarCloud',
    async (
      _event,
      apiUrl: string,
      token: string,
    ): Promise<{ sincronizados: number; errores: number }> => {
      log.info('[DOC Handler] Sincronizando documentos con cloud')
      return sincronizarDocsConCloud(apiUrl, token)
    },
  )

  /** Sincroniza config documentos con cloud */
  ipcMain.handle(
    'docs:sincronizarConfigCloud',
    async (
      _event,
      apiUrl: string,
      token: string,
    ): Promise<{ sincronizados: number; errores: number }> => {
      log.info('[DOC Handler] Sincronizando config documentos con cloud')
      return sincronizarConfigConCloud(apiUrl, token)
    },
  )

  /** Recupera config documentos desde cloud */
  ipcMain.handle(
    'docs:recuperarConfigCloud',
    async (
      _event,
      apiUrl: string,
      token: string,
    ): Promise<{ recuperados: number }> => {
      log.info('[DOC Handler] Recuperando config documentos desde cloud')
      return recuperarConfigDesdeCloud(apiUrl, token)
    },
  )

  log.info('Handlers documentales registrados')
}
