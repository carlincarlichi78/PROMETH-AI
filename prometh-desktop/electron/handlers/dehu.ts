import { ipcMain, app, shell, type BrowserWindow } from 'electron'
import { join, dirname } from 'path'
import { existsSync, mkdirSync, unlinkSync, readdirSync } from 'fs'
import { randomBytes } from 'crypto'
import log from 'electron-log'
import { DehuOrquestador } from '../scraping/dehu/dehu-orquestador'
import { LemaApi } from '../scraping/dehu/lema-api'
import { sincronizarConCloud } from '../scraping/dehu/sincronizar-cloud'
import { exportarCertificadoPfx, listarCertificadosInstalados } from '../certs/almacen'
import { resolverNombreCarpeta } from '../certs/nombre-carpeta'
import { factory } from './scraping'
import type {
  ConfigCertificadoDehu,
  NotificacionDEHU,
  ResultadoConsultaDEHU,
  ResultadoSincronizacion,
} from '../scraping/dehu/tipos-dehu'

/**
 * Extrae el CIF de empresa del subject de un certificado X.509 de representante.
 * Busca OID 2.5.4.97 (organizationIdentifier) con formato VATES-{CIF}.
 */
function extraerCifDeSubject(subject: string): string {
  const matchOid = subject.match(/(?:OID\.)?2\.5\.4\.97=VATES-([A-Z0-9]+)/i)
  if (matchOid) return matchOid[1]
  const matchOrgId = subject.match(/organizationIdentifier=VATES-([A-Z0-9]+)/i)
  if (matchOrgId) return matchOrgId[1]
  return ''
}

/** Extrae NIF personal del subject (SERIALNUMBER=IDCES-{NIF}) */
function extraerNifDeSubject(subject: string): string {
  const matchSerial = subject.match(/SERIALNUMBER=IDCES-([A-Z0-9]+)/i)
  if (matchSerial) return matchSerial[1]
  const matchCN = subject.match(/CN=.*?-\s*([A-Z0-9]{8,9}[A-Z]?)/)
  if (matchCN) return matchCN[1]
  return ''
}

/**
 * Exporta cert del almacen Windows a PFX temporal si faltan rutaPfx/passwordPfx.
 * Tambien extrae CIF de empresa y NIF personal del subject del certificado.
 * Devuelve la ruta temporal creada (o null si no fue necesario).
 */
async function resolverPfxDehu(
  config: ConfigCertificadoDehu & { thumbprint?: string },
): Promise<string | null> {
  // Enriquecer config con CIF/NIF si no estan presentes
  if (!config.nifEmpresa || !config.titularNif) {
    try {
      const certs = await listarCertificadosInstalados()
      const certMatch = config.thumbprint
        ? certs.find(c => c.thumbprint === config.thumbprint)
        : certs.find(c => c.numeroSerie === config.certificadoSerial)
      if (certMatch) {
        if (!config.nifEmpresa) {
          config.nifEmpresa = extraerCifDeSubject(certMatch.subject) || undefined
        }
        if (!config.titularNif) {
          config.titularNif = extraerNifDeSubject(certMatch.subject) || undefined
        }
        log.info(`[DEHU] Cert ${certMatch.thumbprint}: NIF=${config.titularNif ?? 'N/A'}, CIF empresa=${config.nifEmpresa ?? 'N/A'}`)
      }
    } catch (err) {
      log.warn(`[DEHU] No se pudo enriquecer config con CIF/NIF: ${err}`)
    }
  }

  if (config.rutaPfx && config.passwordPfx) return null
  const { thumbprint } = config
  if (!thumbprint) {
    log.warn('[DEHU] Config sin rutaPfx ni thumbprint, LEMA no podra firmar')
    return null
  }

  const dir = join(app.getPath('temp'), 'certigestor-pfx')
  if (!existsSync(dir)) mkdirSync(dir, { recursive: true })

  const passwordTemp = randomBytes(16).toString('hex')
  const rutaTemp = join(dir, `${thumbprint}.pfx`)

  const resultado = await exportarCertificadoPfx(thumbprint, rutaTemp, passwordTemp)
  if (resultado.exito) {
    config.rutaPfx = rutaTemp
    config.passwordPfx = passwordTemp
    log.info(`[DEHU] PFX temporal exportado: ${rutaTemp}`)
    return rutaTemp
  }
  log.error(`[DEHU] No se pudo exportar PFX: ${resultado.error}`)
  return null
}

/**
 * Registra los IPC handlers de DEHU.
 */
export function registrarHandlersDehu(_ventana: BrowserWindow): void {
  /** Consulta DEHU para un certificado (LEMA + fallback Puppeteer) */
  ipcMain.handle(
    'dehu:consultarNotificaciones',
    async (
      _event,
      config: ConfigCertificadoDehu,
      apiUrl: string,
      token: string,
    ): Promise<ResultadoConsultaDEHU> => {
      log.info(
        `[DEHU Handler] Consultando notificaciones para cert: ${config.certificadoSerial}`,
      )

      const rutaTemp = await resolverPfxDehu(config)
      try {
        const orquestador = new DehuOrquestador(apiUrl, token)
        return await orquestador.consultarCertificado(config)
      } finally {
        if (rutaTemp && existsSync(rutaTemp)) {
          try { unlinkSync(rutaTemp) } catch { /* ignorar */ }
        }
      }
    },
  )

  /** Descarga PDF de una notificacion via Puppeteer */
  ipcMain.handle(
    'dehu:descargarNotificacion',
    async (
      _event,
      config: ConfigCertificadoDehu,
      notificacion: NotificacionDEHU,
    ): Promise<{ exito: boolean; rutaLocal?: string; error?: string }> => {
      log.info(`[DEHU Handler] ========================================`)
      log.info(`[DEHU Handler] DESCARGA PDF DEHU`)
      log.info(`[DEHU Handler] Notificacion: ${notificacion.idDehu}`)
      log.info(`[DEHU Handler] Titular: ${notificacion.titular || 'N/A'}`)
      log.info(`[DEHU Handler] Config serial: ${config.certificadoSerial}`)
      log.info(`[DEHU Handler] Config thumbprint: ${(config as Record<string, unknown>).thumbprint || 'N/A'}`)
      log.info(`[DEHU Handler] Config nifEmpresa: ${config.nifEmpresa || 'N/A'}`)
      log.info(`[DEHU Handler] Config titularNif: ${config.titularNif || 'N/A'}`)
      log.info(`[DEHU Handler] ========================================`)

      const rutaTemp = await resolverPfxDehu(config)
      // Resolver carpeta por nombre titular (mismo patron que documentales)
      const nombreCarpeta = await resolverNombreCarpeta(config.certificadoSerial)
      try {
        const orquestador = new DehuOrquestador('', '')
        return await orquestador.descargarNotificacion(config, notificacion, nombreCarpeta ? { nombreCarpeta } : undefined)
      } finally {
        if (rutaTemp && existsSync(rutaTemp)) {
          try { unlinkSync(rutaTemp) } catch { /* ignorar */ }
        }
      }
    },
  )

  /** Sincroniza notificaciones con API cloud */
  ipcMain.handle(
    'dehu:sincronizarCloud',
    async (
      _event,
      notificaciones: NotificacionDEHU[],
      certificadoId: string,
      apiUrl: string,
      token: string,
    ): Promise<ResultadoSincronizacion> => {
      log.info(
        `[DEHU Handler] Sincronizando ${notificaciones.length} notificaciones con cloud`,
      )

      return sincronizarConCloud(notificaciones, certificadoId, apiUrl, token)
    },
  )

  /** Consulta + sincronizacion en un paso (construye cadenas Factory) */
  ipcMain.handle(
    'dehu:consultarYSincronizar',
    async (
      _event,
      configs: Array<ConfigCertificadoDehu & { certificadoId: string }>,
      apiUrl: string,
      token: string,
    ): Promise<{ exito: boolean; error?: string }> => {
      log.info(
        `[DEHU Handler] Consulta + sync para ${configs.length} certificados`,
      )

      const rutasTemp: string[] = []
      try {
        // Resolver PFX para cada config
        for (const cfg of configs) {
          const ruta = await resolverPfxDehu(cfg)
          if (ruta) rutasTemp.push(ruta)
        }

        const orquestador = new DehuOrquestador(apiUrl, token)

        // Limpiar cadenas previas
        factory.limpiar()

        // Construir cadenas para todos los certificados
        orquestador.construirCadenasBatch(factory, configs)

        // Iniciar ejecucion (el progreso se reporta via scraping:progreso)
        await factory.iniciar()

        return { exito: true }
      } catch (error) {
        const msg =
          error instanceof Error ? error.message : 'Error desconocido'
        log.error(`[DEHU Handler] Error en consulta+sync: ${msg}`)
        return { exito: false, error: msg }
      } finally {
        for (const ruta of rutasTemp) {
          try { if (existsSync(ruta)) unlinkSync(ruta) } catch { /* ignorar */ }
        }
      }
    },
  )

  /** Verifica si un certificado tiene alta en LEMA */
  ipcMain.handle(
    'dehu:verificarAlta',
    async (
      _event,
      config: ConfigCertificadoDehu,
    ): Promise<{ alta: boolean; estado: string }> => {
      log.info(
        `[DEHU Handler] Verificando alta LEMA para cert: ${config.certificadoSerial}`,
      )

      const rutaTemp = await resolverPfxDehu(config)
      try {
        const lema = new LemaApi(config)
        const estado = await lema.verificarAlta()
        return { alta: estado === 'ALTA', estado }
      } finally {
        if (rutaTemp && existsSync(rutaTemp)) {
          try { unlinkSync(rutaTemp) } catch { /* ignorar */ }
        }
      }
    },
  )

  /**
   * Verifica si un PDF de notificacion DEHU ya esta descargado en disco.
   * Busca archivos DEHU_{idDehu}.pdf en la carpeta del certificado.
   * Fallback: escanea TODAS las subcarpetas de descargas.
   */
  ipcMain.handle(
    'dehu:verificarPdfDescargado',
    async (
      _event,
      idDehu: string,
      certificadoSerial: string,
    ): Promise<{ descargado: boolean; rutaLocal?: string }> => {
      const baseDescargas = join(app.getPath('documents'), 'CertiGestor', 'descargas')
      const idSanitizado = idDehu.replace(/[^a-zA-Z0-9-_]/g, '_')
      const nombreArchivo = `DEHU_${idSanitizado}.pdf`

      if (!existsSync(baseDescargas)) return { descargado: false }

      // Resolver nombre carpeta del titular
      const nombreCarpeta = await resolverNombreCarpeta(certificadoSerial)

      // Buscar en carpeta por nombre titular
      if (nombreCarpeta) {
        const ruta = join(baseDescargas, nombreCarpeta, nombreArchivo)
        if (existsSync(ruta)) return { descargado: true, rutaLocal: ruta }
      }

      // Buscar en carpeta por serial (fallback/legacy)
      const rutaSerial = join(baseDescargas, certificadoSerial, nombreArchivo)
      if (existsSync(rutaSerial)) return { descargado: true, rutaLocal: rutaSerial }

      // Fallback: escanear TODAS las subcarpetas buscando el archivo
      try {
        const carpetas = readdirSync(baseDescargas, { withFileTypes: true })
        for (const entry of carpetas) {
          if (!entry.isDirectory()) continue
          const ruta = join(baseDescargas, entry.name, nombreArchivo)
          if (existsSync(ruta)) {
            log.info(`[DEHU] PDF encontrado via scan: ${ruta}`)
            return { descargado: true, rutaLocal: ruta }
          }
        }
      } catch (err) {
        log.warn(`[DEHU] Error escaneando carpetas: ${err}`)
      }

      return { descargado: false }
    },
  )

  /**
   * Verifica multiples PDFs de DEHU de una vez.
   * Retorna un mapa { idDehu: { descargado, rutaLocal } }.
   */
  ipcMain.handle(
    'dehu:verificarPdfsBatch',
    async (
      _event,
      items: Array<{ idDehu: string; certificadoSerial: string }>,
    ): Promise<Record<string, { descargado: boolean; rutaLocal?: string }>> => {
      const baseDescargas = join(app.getPath('documents'), 'CertiGestor', 'descargas')
      const resultado: Record<string, { descargado: boolean; rutaLocal?: string }> = {}

      if (!existsSync(baseDescargas)) {
        for (const { idDehu } of items) resultado[idDehu] = { descargado: false }
        return resultado
      }

      // Cache de nombre carpeta por serial para no resolver multiples veces
      const cacheNombres: Record<string, string | undefined> = {}

      // Pre-cargar listado de carpetas para fallback scan
      let todasCarpetas: string[] = []
      try {
        todasCarpetas = readdirSync(baseDescargas, { withFileTypes: true })
          .filter(e => e.isDirectory())
          .map(e => e.name)
      } catch { /* ignorar */ }

      for (const { idDehu, certificadoSerial } of items) {
        const idSanitizado = idDehu.replace(/[^a-zA-Z0-9-_]/g, '_')
        const nombreArchivo = `DEHU_${idSanitizado}.pdf`

        if (!(certificadoSerial in cacheNombres)) {
          cacheNombres[certificadoSerial] = await resolverNombreCarpeta(certificadoSerial)
        }
        const nombreCarpeta = cacheNombres[certificadoSerial]

        let encontrado = false

        // 1. Buscar por nombre titular
        if (nombreCarpeta) {
          const ruta = join(baseDescargas, nombreCarpeta, nombreArchivo)
          if (existsSync(ruta)) {
            resultado[idDehu] = { descargado: true, rutaLocal: ruta }
            encontrado = true
          }
        }

        // 2. Buscar por serial
        if (!encontrado) {
          const rutaSerial = join(baseDescargas, certificadoSerial, nombreArchivo)
          if (existsSync(rutaSerial)) {
            resultado[idDehu] = { descargado: true, rutaLocal: rutaSerial }
            encontrado = true
          }
        }

        // 3. Fallback: escanear todas las subcarpetas
        if (!encontrado) {
          for (const carpeta of todasCarpetas) {
            const ruta = join(baseDescargas, carpeta, nombreArchivo)
            if (existsSync(ruta)) {
              resultado[idDehu] = { descargado: true, rutaLocal: ruta }
              encontrado = true
              break
            }
          }
        }

        if (!encontrado) {
          resultado[idDehu] = { descargado: false }
        }
      }

      return resultado
    },
  )

  /** Abre un PDF local con el visor del sistema */
  ipcMain.handle(
    'dehu:abrirPdf',
    async (
      _event,
      rutaLocal: string,
    ): Promise<{ exito: boolean; error?: string }> => {
      if (!existsSync(rutaLocal)) {
        return { exito: false, error: 'Archivo no encontrado' }
      }
      try {
        await shell.openPath(rutaLocal)
        return { exito: true }
      } catch (error) {
        const msg = error instanceof Error ? error.message : 'Error desconocido'
        log.error(`[DEHU Handler] Error abriendo PDF: ${msg}`)
        return { exito: false, error: msg }
      }
    },
  )

  /**
   * Descarga PDFs DEHU en lote (secuencial, no paralelo).
   * Emite progreso via evento IPC 'dehu:progresoBatch'.
   */
  ipcMain.handle(
    'dehu:descargarPdfBatch',
    async (
      event,
      config: ConfigCertificadoDehu,
      notificaciones: NotificacionDEHU[],
    ): Promise<{ exitosos: number; errores: number; resultados: Array<{ idDehu: string; exito: boolean; error?: string }> }> => {
      log.info(`[DEHU Handler] Batch download: ${notificaciones.length} PDFs`)

      const rutaTemp = await resolverPfxDehu(config)
      const nombreCarpeta = await resolverNombreCarpeta(config.certificadoSerial)
      const resultados: Array<{ idDehu: string; exito: boolean; error?: string }> = []
      let exitosos = 0
      let errores = 0

      try {
        for (let i = 0; i < notificaciones.length; i++) {
          const notif = notificaciones[i]

          // Emitir progreso
          event.sender.send('dehu:progresoBatch', {
            actual: i + 1,
            total: notificaciones.length,
            idDehu: notif.idDehu,
          })

          try {
            const orquestador = new DehuOrquestador('', '')
            const resultado = await orquestador.descargarNotificacion(
              config,
              notif,
              nombreCarpeta ? { nombreCarpeta } : undefined,
            )
            if (resultado.exito) {
              exitosos++
              resultados.push({ idDehu: notif.idDehu, exito: true })
            } else {
              errores++
              resultados.push({ idDehu: notif.idDehu, exito: false, error: resultado.error })
            }
          } catch (error) {
            errores++
            const msg = error instanceof Error ? error.message : 'Error desconocido'
            resultados.push({ idDehu: notif.idDehu, exito: false, error: msg })
          }
        }
      } finally {
        if (rutaTemp && existsSync(rutaTemp)) {
          try { unlinkSync(rutaTemp) } catch { /* ignorar */ }
        }
      }

      log.info(`[DEHU Handler] Batch completado: ${exitosos} exitosos, ${errores} errores`)
      return { exitosos, errores, resultados }
    },
  )

  log.info('Handlers DEHU registrados')
}
