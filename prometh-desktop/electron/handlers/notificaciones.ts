import { ipcMain, type BrowserWindow } from 'electron'
import log from 'electron-log'
import { OrquestadorNotificaciones } from '../scraping/notificaciones/orquestador-notificaciones'
import {
  obtenerConfigPortales,
  guardarConfigPortalesCert,
} from '../scraping/notificaciones/config-portales'
import { factory } from './scraping'
import { PortalNotificaciones } from '../scraping/notificaciones/tipos-notificaciones'
import type {
  ConfigPortalesCertificado,
  ResultadoConsultaMultiPortal,
  ResultadoConsultaPortal,
} from '../scraping/notificaciones/tipos-notificaciones'
import type { ConfigCertificadoDehu, NotificacionDEHU } from '../scraping/dehu/tipos-dehu'
import { DehuScraper } from '../scraping/dehu/dehu-scraper'
import { listarCertificadosInstalados } from '../certs/almacen'
import { resolverNombreCarpeta } from '../certs/nombre-carpeta'

/** Extrae NIF/CIF del campo subject del certificado X.509 */
function extraerNifDeSubject(subject: string): string {
  const matchSerial = subject.match(/SERIALNUMBER=IDCES-([A-Z0-9]+)/i)
  if (matchSerial) return matchSerial[1]
  const matchCN = subject.match(/CN=.*?-\s*([A-Z0-9]{8,9}[A-Z]?)/)
  if (matchCN) return matchCN[1]
  return ''
}

/** Extrae nombre del campo CN del subject */
function extraerNombreDeSubject(subject: string): string {
  const matchCN = subject.match(/CN=([^,]+)/)
  return matchCN ? matchCN[1].trim() : ''
}

/**
 * Extrae el CIF de la empresa representada del subject del certificado.
 * En certificados FNMT de representante, el CIF esta en OID 2.5.4.97 como VATES-{CIF}.
 * Formatos posibles en el subject string:
 * - OID.2.5.4.97=VATES-B93587418
 * - 2.5.4.97=VATES-B93587418
 * - organizationIdentifier=VATES-B93587418
 */
function extraerCifEmpresaDeSubject(subject: string): string {
  // OID 2.5.4.97 (organizationIdentifier) con prefijo VATES
  const matchOid = subject.match(/(?:OID\.)?2\.5\.4\.97=VATES-([A-Z0-9]+)/i)
  if (matchOid) return matchOid[1]

  // Formato organizationIdentifier=VATES-
  const matchOrgId = subject.match(/organizationIdentifier=VATES-([A-Z0-9]+)/i)
  if (matchOrgId) return matchOrgId[1]

  // Fallback: buscar patron CIF (letra + 8 digitos) en campo O= que no sea un NIF personal
  const matchOrg = subject.match(/O=([^,]+)/i)
  if (matchOrg) {
    // Extraer CIF del nombre de la org si incluye el CIF
    const cifEnOrg = matchOrg[1].match(/\b([A-HJ-NP-SUVW]\d{7}[A-J0-9])\b/)
    if (cifEnOrg) return cifEnOrg[1]
  }

  return ''
}

/**
 * Construye ConfigCertificadoDehu desde el almacen de Windows.
 * Si se pasa `titularHint`, intenta matchear el certificado correcto
 * por NIF/CIF/nombre en vez de tomar ciegamente certs[0].
 */
async function resolverConfigDesdeAlmacen(titularHint?: string): Promise<ConfigCertificadoDehu | null> {
  const certs = await listarCertificadosInstalados()
  if (certs.length === 0) return null

  log.info(`[Notif Handler] Certs disponibles: ${certs.length}. Titular hint: ${titularHint ?? 'ninguno'}`)

  type CertInstalado = (typeof certs)[number]
  let certSeleccionado: CertInstalado = certs[0]
  let metodoMatch = 'default(certs[0])'

  // Si hay hint de titular y multiples certs, intentar matchear
  if (titularHint && certs.length > 1) {
    const hintNorm = titularHint.toUpperCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '')

    // Estrategia 1: Extraer NIF (8 digitos + letra) del titular y buscar en subjects
    const nifMatch = hintNorm.match(/(\d{8}[A-Z])/i)
    if (nifMatch) {
      const certPorNif = certs.find(c => c.subject.toUpperCase().includes(nifMatch[1]))
      if (certPorNif) {
        certSeleccionado = certPorNif
        metodoMatch = `nif(${nifMatch[1]})`
      }
    }

    // Estrategia 2: Extraer CIF (letra + 7 digitos + check) del titular
    if (metodoMatch.startsWith('default')) {
      const cifMatch = hintNorm.match(/([A-HJ-NP-SUVW]\d{7}[A-J0-9])/i)
      if (cifMatch) {
        const certPorCif = certs.find(c => c.subject.toUpperCase().includes(cifMatch[1]))
        if (certPorCif) {
          certSeleccionado = certPorCif
          metodoMatch = `cif(${cifMatch[1]})`
        }
      }
    }

    // Estrategia 3: Match por nombre (normalizado sin acentos)
    if (metodoMatch.startsWith('default')) {
      const certPorNombre = certs.find(c => {
        const subjectNorm = c.subject.toUpperCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '')
        // Extraer CN del subject
        const cnMatch = subjectNorm.match(/CN=([^,]+)/)
        if (!cnMatch) return false
        const cn = cnMatch[1].trim()
        // Match bidireccional: titular contiene CN o CN contiene titular
        return hintNorm.includes(cn) || cn.includes(hintNorm)
      })
      if (certPorNombre) {
        certSeleccionado = certPorNombre
        metodoMatch = 'nombre'
      }
    }
  }

  const nifPersonal = extraerNifDeSubject(certSeleccionado.subject)
  const cifEmpresa = extraerCifEmpresaDeSubject(certSeleccionado.subject)

  log.info(`[Notif Handler] Cert seleccionado (${metodoMatch}): ${certSeleccionado.numeroSerie}`)
  log.info(`[Notif Handler] Subject: ${certSeleccionado.subject}`)
  log.info(`[Notif Handler] NIF personal: ${nifPersonal}, CIF empresa: ${cifEmpresa || 'N/A'}`)

  return {
    certificadoSerial: certSeleccionado.numeroSerie,
    titularNombre: extraerNombreDeSubject(certSeleccionado.subject),
    titularNif: nifPersonal,
    nifEmpresa: cifEmpresa || undefined,
    thumbprint: certSeleccionado.thumbprint,
    timeoutGlobal: 300_000,
  } as ConfigCertificadoDehu
}

/**
 * Registra los IPC handlers de notificaciones multi-portal.
 */
export function registrarHandlersNotificaciones(_ventana: BrowserWindow): void {
  /** Obtiene la configuracion de portales activos para un certificado */
  ipcMain.handle(
    'notif:obtenerConfigPortales',
    (_event, certificadoSerial: string): ConfigPortalesCertificado => {
      return obtenerConfigPortales(certificadoSerial)
    },
  )

  /** Guarda la configuracion de portales activos para un certificado */
  ipcMain.handle(
    'notif:guardarConfigPortales',
    (
      _event,
      certificadoSerial: string,
      portalesActivos: PortalNotificaciones[],
      datosPortal?: ConfigPortalesCertificado['datosPortal'],
    ): void => {
      guardarConfigPortalesCert(certificadoSerial, portalesActivos, datosPortal)
    },
  )

  /** Lista los portales disponibles */
  ipcMain.handle(
    'notif:obtenerPortalesDisponibles',
    (): PortalNotificaciones[] => {
      return Object.values(PortalNotificaciones)
    },
  )

  /** Consulta un portal concreto para un certificado */
  ipcMain.handle(
    'notif:consultarPortal',
    async (
      _event,
      portal: PortalNotificaciones,
      serialNumber: string,
      apiUrl: string,
      token: string,
      configDehu?: ConfigCertificadoDehu,
    ): Promise<ResultadoConsultaPortal> => {
      log.info(`[Notif Handler] Consultando portal ${portal} para cert: ${serialNumber}`)
      const orquestador = new OrquestadorNotificaciones(apiUrl, token)
      return orquestador.consultarPortal(portal, serialNumber, configDehu)
    },
  )

  /** Consulta todos los portales activos para un certificado */
  ipcMain.handle(
    'notif:consultarMultiPortal',
    async (
      _event,
      serialNumber: string,
      apiUrl: string,
      token: string,
      configDehu?: ConfigCertificadoDehu,
    ): Promise<ResultadoConsultaMultiPortal> => {
      log.info(`[Notif Handler] Consulta multi-portal para cert: ${serialNumber}`)
      const configPortales = obtenerConfigPortales(serialNumber)
      const orquestador = new OrquestadorNotificaciones(apiUrl, token)
      return orquestador.consultarMultiPortal(serialNumber, configPortales, configDehu)
    },
  )

  /** Batch: consulta + sync para N certificados via Factory */
  ipcMain.handle(
    'notif:consultarYSincronizarBatch',
    async (
      _event,
      configs: Array<{
        serialNumber: string
        certificadoId: string
        configDehu?: ConfigCertificadoDehu & { certificadoId: string }
      }>,
      apiUrl: string,
      token: string,
    ): Promise<{ exito: boolean; error?: string }> => {
      log.info(`[Notif Handler] Batch multi-portal para ${configs.length} certificados`)

      try {
        const orquestador = new OrquestadorNotificaciones(apiUrl, token)

        const configsConPortales = configs.map((c) => ({
          ...c,
          configPortales: obtenerConfigPortales(c.serialNumber),
        }))

        factory.limpiar()
        orquestador.construirCadenasBatch(factory, configsConPortales)
        await factory.iniciar()

        return { exito: true }
      } catch (error) {
        const msg = error instanceof Error ? error.message : 'Error desconocido'
        log.error(`[Notif Handler] Error en batch: ${msg}`)
        return { exito: false, error: msg }
      }
    },
  )

  /**
   * Descarga el PDF de una notificacion desde su portal.
   * Solo DEHU implementado por ahora; otros portales retornan "no soportado".
   * Si no se pasa configDehu, auto-resuelve desde el almacen de Windows.
   */
  ipcMain.handle(
    'notif:descargarPdf',
    async (
      _event,
      idExterno: string,
      portal: string,
      configDehu?: ConfigCertificadoDehu,
      estadoNotificacion?: string,
      titularNotificacion?: string,
    ): Promise<{ exito: boolean; rutaLocal?: string; error?: string }> => {
      log.info(`[Notif Handler] Descarga PDF: ${idExterno} de ${portal} (estado: ${estadoNotificacion ?? 'desconocido'}, titular: ${titularNotificacion ?? 'N/A'})`)

      if (portal !== 'DEHU' && portal !== PortalNotificaciones.DEHU) {
        return { exito: false, error: `Descarga PDF no soportada para portal: ${portal}` }
      }

      // Auto-resolver certificado si no se pasa configDehu
      let config: ConfigCertificadoDehu | undefined = configDehu
      if (!config) {
        config = await resolverConfigDesdeAlmacen(titularNotificacion) ?? undefined
        if (!config) {
          return { exito: false, error: 'No hay certificados instalados en el almacen de Windows' }
        }
        log.info(`[Notif Handler] Config auto-resuelta desde almacen: ${config.certificadoSerial}`)
      }

      // Mapear estado CertiGestor → estado DEHU para navegar a la seccion correcta
      const esPendiente = !estadoNotificacion || estadoNotificacion === 'pendiente'

      try {
        // Resolver carpeta por nombre titular (mismo patron que documentales)
        const nombreCarpeta = await resolverNombreCarpeta(config.certificadoSerial)
        const scraper = new DehuScraper(config, nombreCarpeta ? { nombreCarpeta } : undefined)
        const notificacion: NotificacionDEHU = {
          idDehu: idExterno,
          tipo: 'Notificacion',
          titulo: '',
          titular: '',
          ambito: '',
          organismo: 'DEHU',
          fechaDisposicion: new Date().toISOString(),
          fechaCaducidad: null,
          estado: esPendiente ? 'Pendiente de abrir' : 'Aceptada',
          rutaPdfLocal: null,
        }

        const rutaLocal = await scraper.runDescargarPdf(notificacion)

        if (rutaLocal) {
          return { exito: true, rutaLocal }
        } else {
          return { exito: false, error: 'El scraper no devolvio ruta de archivo (retorno null sin error)' }
        }
      } catch (error) {
        const msg = error instanceof Error ? error.message : 'Error desconocido'
        log.error(`[Notif Handler] Error descarga PDF: ${msg}`)
        return { exito: false, error: msg }
      }
    },
  )

  log.info('Handlers notificaciones multi-portal registrados')
}
