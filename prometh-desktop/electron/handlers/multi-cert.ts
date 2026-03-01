import { ipcMain, app, type BrowserWindow } from 'electron'
import { join } from 'path'
import { existsSync, mkdirSync, unlinkSync } from 'fs'
import { randomBytes } from 'crypto'
import log from 'electron-log'
import { factory } from './scraping'
import { OrquestadorGlobal } from '../scraping/orquestador-global'
import type { ConfigMultiCert, ResultadoMultiCert } from '../scraping/orquestador-global'
import {
  registrarEjecucion,
  obtenerHistorialMultiCert,
  limpiarHistorialMultiCert,
} from '../scraping/historial-multicert'
import { exportarCertificadoPfx } from '../certs/almacen'
import { ChainStatus } from '../scraping/tipos'
import { notificarSyncCompletada } from '../tray/servicio-notificaciones'

/** Mapa serial → nombre para enriquecer estado en UI */
let mapaNombres: Record<string, string> = {}

/** Carpeta para PFX temporales exportados del almacen Windows */
function carpetaTempPfx(): string {
  const dir = join(app.getPath('temp'), 'certigestor-pfx')
  if (!existsSync(dir)) mkdirSync(dir, { recursive: true })
  return dir
}

/**
 * Resuelve rutaPfx y passwordPfx para configs DEHU que no los tengan.
 * Exporta el certificado del almacen Windows a un PFX temporal.
 * Devuelve las rutas temporales creadas para limpiar despues.
 */
async function resolverPfxParaDehu(configs: ConfigMultiCert[]): Promise<string[]> {
  const rutasTemporales: string[] = []

  for (const config of configs) {
    if (!config.dehu || (config.dehu.rutaPfx && config.dehu.passwordPfx)) continue
    if (!config.thumbprint) {
      log.warn(`[MultiCert] Config DEHU sin thumbprint para cert ${config.certificadoSerial}, saltando LEMA`)
      continue
    }

    const passwordTemp = randomBytes(16).toString('hex')
    const rutaTemp = join(carpetaTempPfx(), `${config.thumbprint}.pfx`)

    const resultado = await exportarCertificadoPfx(config.thumbprint, rutaTemp, passwordTemp)
    if (resultado.exito) {
      config.dehu.rutaPfx = rutaTemp
      config.dehu.passwordPfx = passwordTemp
      rutasTemporales.push(rutaTemp)
      log.info(`[MultiCert] PFX temporal exportado para cert ${config.certificadoSerial}`)
    } else {
      log.error(`[MultiCert] No se pudo exportar PFX para cert ${config.certificadoSerial}: ${resultado.error}`)
    }
  }

  return rutasTemporales
}

/** Limpia PFX temporales */
function limpiarPfxTemporales(rutas: string[]): void {
  for (const ruta of rutas) {
    try {
      if (existsSync(ruta)) unlinkSync(ruta)
    } catch (err) {
      log.warn(`[MultiCert] No se pudo eliminar PFX temporal: ${ruta}`, err)
    }
  }
}

/**
 * Registra los IPC handlers de multi-certificado.
 */
export function registrarHandlersMultiCert(_ventana: BrowserWindow): void {
  /** Iniciar consulta multi-certificado */
  ipcMain.handle(
    'multicert:iniciar',
    async (
      _event,
      configs: ConfigMultiCert[],
      apiUrl: string,
      token: string,
    ): Promise<{ exito: boolean; error?: string }> => {
      log.info(
        `[MultiCert] Iniciando para ${configs.length} certificados`,
      )

      let rutasTemporales: string[] = []
      try {
        // Guardar mapa de nombres para enriquecer progreso
        mapaNombres = {}
        for (const c of configs) {
          if (c.nombreCert) {
            mapaNombres[c.certificadoSerial] = c.nombreCert
          }
        }

        // Resolver PFX para configs DEHU sin rutaPfx
        rutasTemporales = await resolverPfxParaDehu(configs)

        const orquestador = new OrquestadorGlobal(apiUrl, token)

        factory.limpiar()
        orquestador.construirCadenasMultiCert(factory, configs)

        const inicio = Date.now()
        await factory.iniciar()
        const duracionMs = Date.now() - inicio

        // Registrar en historial
        const estado = factory.obtenerEstado()
        const resultado: ResultadoMultiCert = {
          fecha: new Date().toISOString(),
          duracionMs,
          totalCadenas: estado.totalCadenas,
          certificados: configs.map((c) => {
            const cadenasCert = estado.cadenas.filter(
              (ch) =>
                ch.certificadoSerial === c.certificadoSerial ||
                ch.certificadoSerial === `notif-${c.certificadoSerial}`,
            )
            const todasCompletadas = cadenasCert.every(
              (ch) => ch.estado === ChainStatus.COMPLETED,
            )
            const algunaFallo = cadenasCert.some(
              (ch) => ch.estado === ChainStatus.FAILED,
            )

            return {
              serial: c.certificadoSerial,
              nombre: c.nombreCert,
              dominios: {
                dehu: !!c.dehu,
                notificaciones: c.portalesNotificaciones,
                documentos: c.documentos,
              },
              estado: todasCompletadas
                ? 'completado' as const
                : algunaFallo
                  ? 'fallido' as const
                  : 'parcial' as const,
            }
          }),
        }
        registrarEjecucion(resultado)

        // Notificacion resumen al tray
        const completados = resultado.certificados.filter(c => c.estado === 'completado').length
        const fallidos = resultado.certificados.filter(c => c.estado === 'fallido').length
        const duracionSeg = Math.round(duracionMs / 1000)
        notificarSyncCompletada(
          `Scraping finalizado en ${duracionSeg}s — ${completados} completado(s)` +
          (fallidos > 0 ? `, ${fallidos} con errores` : ''),
        )

        return { exito: true }
      } catch (error) {
        const msg =
          error instanceof Error ? error.message : 'Error desconocido'
        log.error(`[MultiCert] Error: ${msg}`)
        return { exito: false, error: msg }
      } finally {
        // Limpiar PFX temporales siempre
        limpiarPfxTemporales(rutasTemporales)
      }
    },
  )

  /** Detener consulta en curso */
  ipcMain.handle('multicert:detener', () => {
    factory.detener()
    return { exito: true }
  })

  /** Obtener estado enriquecido con nombres de certificados */
  ipcMain.handle('multicert:obtenerEstado', () => {
    const estado = factory.obtenerEstado()
    // Enriquecer cadenas con nombre de certificado
    const cadenas = estado.cadenas.map((c) => {
      const serialLimpio = c.certificadoSerial.startsWith('notif-')
        ? c.certificadoSerial.replace('notif-', '')
        : c.certificadoSerial
      return {
        ...c,
        nombreCert: mapaNombres[serialLimpio] ?? c.nombreCert,
      }
    })
    return { ...estado, cadenas }
  })

  /** Obtener historial de ejecuciones */
  ipcMain.handle(
    'multicert:obtenerHistorial',
    (_event, limite?: number) => {
      return obtenerHistorialMultiCert(limite)
    },
  )

  /** Limpiar historial */
  ipcMain.handle('multicert:limpiarHistorial', () => {
    limpiarHistorialMultiCert()
    return { exito: true }
  })

  log.info('Handlers multi-certificado registrados')
}
