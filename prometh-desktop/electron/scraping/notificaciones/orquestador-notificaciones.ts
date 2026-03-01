import log from 'electron-log'
import { BaseScraper } from '../base-scraper'
import { Block } from '../block'
import { Chain } from '../chain'
import { ProcessType, type ResultadoScraping, type ConfigScraping } from '../tipos'
import {
  PortalNotificaciones,
  EstadoAutenticacion,
} from './tipos-notificaciones'
import type {
  ConfigPortalesCertificado,
  ResultadoConsultaPortal,
  ResultadoConsultaMultiPortal,
} from './tipos-notificaciones'
import { sincronizarPortalConCloud } from './sincronizar-notificaciones'
import type { BaseScraperNotificaciones } from './base-scraper-notificaciones'
// Scrapers concretos
import { ScraperDgt } from './dgt/dgt-scraper'
import { ScraperEnotum } from './enotum/enotum-scraper'
import { ScraperJuntaAndalucia } from './junta-andalucia/junta-andalucia-scraper'
import { ScraperAeatNotificaciones } from './aeat/aeat-notificaciones-scraper'
import { ScraperSeguridadSocial } from './seguridad-social/ss-notificaciones-scraper'
// Reutilizar DEHU existente
import { DehuOrquestador } from '../dehu/dehu-orquestador'
import type { ConfigCertificadoDehu } from '../dehu/tipos-dehu'
import type { Factory } from '../factory'

/** Crea el scraper concreto para un portal (excepto DEHU) */
function crearScraperPortal(
  portal: PortalNotificaciones,
  serialNumber: string,
  config?: Partial<ConfigScraping>,
): BaseScraperNotificaciones {
  switch (portal) {
    case PortalNotificaciones.DGT:
      return new ScraperDgt(serialNumber, config)
    case PortalNotificaciones.E_NOTUM:
      return new ScraperEnotum(serialNumber, config)
    case PortalNotificaciones.JUNTA_ANDALUCIA:
      return new ScraperJuntaAndalucia(serialNumber, config)
    case PortalNotificaciones.AEAT_DIRECTA:
      return new ScraperAeatNotificaciones(serialNumber, config)
    case PortalNotificaciones.SEGURIDAD_SOCIAL:
      return new ScraperSeguridadSocial(serialNumber, config)
    default:
      throw new Error(`Portal no soportado para scraper directo: ${portal}`)
  }
}

// ── Blocks para Factory ──────────────────────────────────────

/**
 * Block wrapper para consulta de un portal de notificaciones.
 * Similar a DehuConsultaBlock pero para portales adicionales.
 */
class PortalConsultaBlock extends BaseScraper {
  private readonly portal: PortalNotificaciones
  private readonly configScraping: Partial<ConfigScraping> | undefined
  resultado: ResultadoConsultaPortal | null = null

  constructor(
    portal: PortalNotificaciones,
    serialNumber: string,
    configScraping?: Partial<ConfigScraping>,
  ) {
    super(serialNumber, configScraping)
    this.portal = portal
    this.configScraping = configScraping
  }

  get nombre(): string {
    return `${this.portal}-Consulta (${this.serialNumber})`
  }

  /** Override run() — delega al scraper concreto sin usar Puppeteer propio */
  async run(): Promise<ResultadoScraping> {
    try {
      const scraper = crearScraperPortal(
        this.portal,
        this.serialNumber,
        this.configScraping,
      )
      const resultado = await scraper.run()
      this.resultado = resultado.datos as ResultadoConsultaPortal
      return resultado
    } catch (error) {
      const msg = error instanceof Error ? error.message : 'Error desconocido'
      this.resultado = {
        exito: false,
        portal: this.portal,
        certificadoSerial: this.serialNumber,
        estadoAutenticacion: EstadoAutenticacion.ERROR,
        notificaciones: [],
        error: msg,
        fechaConsulta: new Date().toISOString(),
      }
      return { exito: false, error: msg }
    }
  }

  async ejecutar(): Promise<ResultadoScraping> {
    return { exito: false, error: 'Usar run() directamente' }
  }
}

/**
 * Block wrapper para sincronizacion cloud de un portal.
 * Similar a DehuSyncBlock.
 */
class PortalSyncBlock extends BaseScraper {
  private readonly bloqueConsulta: PortalConsultaBlock
  private readonly certificadoId: string
  private readonly apiUrl: string
  private readonly token: string

  constructor(
    bloqueConsulta: PortalConsultaBlock,
    certificadoId: string,
    apiUrl: string,
    token: string,
  ) {
    super(bloqueConsulta.serialNumber)
    this.bloqueConsulta = bloqueConsulta
    this.certificadoId = certificadoId
    this.apiUrl = apiUrl
    this.token = token
  }

  get nombre(): string {
    return `${this.bloqueConsulta.nombre}-Sync`
  }

  /** Override run() — sincroniza sin necesitar Puppeteer */
  async run(): Promise<ResultadoScraping> {
    try {
      const consulta = this.bloqueConsulta.resultado
      if (!consulta || !consulta.exito) {
        return { exito: false, error: 'Sin resultado de consulta para sincronizar' }
      }

      if (consulta.notificaciones.length === 0) {
        return { exito: true, datos: { nuevas: 0, actualizadas: 0, errores: 0 } }
      }

      const resultado = await sincronizarPortalConCloud(
        consulta.notificaciones,
        this.certificadoId,
        consulta.portal,
        this.apiUrl,
        this.token,
      )

      return { exito: resultado.errores === 0, datos: resultado }
    } catch (error) {
      const msg = error instanceof Error ? error.message : 'Error desconocido'
      return { exito: false, error: msg }
    }
  }

  async ejecutar(): Promise<ResultadoScraping> {
    return { exito: false, error: 'Usar run() directamente' }
  }
}

// ── Orquestador principal ────────────────────────────────────

/**
 * Orquestador de notificaciones multi-portal.
 *
 * Responsabilidades:
 * 1. Consulta individual de un portal para un certificado
 * 2. Consulta multi-portal (N portales) para un certificado
 * 3. Construccion de Chains para la Factory
 * 4. Integracion con DehuOrquestador (sin duplicar logica DEHU)
 */
export class OrquestadorNotificaciones {
  private readonly apiUrl: string
  private readonly token: string

  constructor(apiUrl: string, token: string) {
    this.apiUrl = apiUrl
    this.token = token
  }

  /**
   * Consulta un portal concreto para un certificado.
   * DEHU delega al DehuOrquestador existente.
   */
  async consultarPortal(
    portal: PortalNotificaciones,
    serialNumber: string,
    configDehu?: ConfigCertificadoDehu,
  ): Promise<ResultadoConsultaPortal> {
    if (portal === PortalNotificaciones.DEHU) {
      return this.consultarDehu(serialNumber, configDehu)
    }

    const scraper = crearScraperPortal(portal, serialNumber)
    const resultado = await scraper.run()
    return (resultado.datos as ResultadoConsultaPortal) ?? {
      exito: false,
      portal,
      certificadoSerial: serialNumber,
      estadoAutenticacion: EstadoAutenticacion.ERROR,
      notificaciones: [],
      error: resultado.error,
      fechaConsulta: new Date().toISOString(),
    }
  }

  /**
   * Consulta todos los portales activos de un certificado.
   * Ejecuta portales en paralelo (independientes entre si).
   */
  async consultarMultiPortal(
    serialNumber: string,
    configPortales: ConfigPortalesCertificado,
    configDehu?: ConfigCertificadoDehu,
  ): Promise<ResultadoConsultaMultiPortal> {
    const { portalesActivos } = configPortales

    log.info(
      `[OrqNotif] Consultando ${portalesActivos.length} portales para cert: ${serialNumber}`,
    )

    const promesas = portalesActivos.map((portal) =>
      this.consultarPortal(portal, serialNumber, configDehu).catch(
        (err): ResultadoConsultaPortal => ({
          exito: false,
          portal,
          certificadoSerial: serialNumber,
          estadoAutenticacion: EstadoAutenticacion.ERROR,
          notificaciones: [],
          error: (err as Error).message,
          fechaConsulta: new Date().toISOString(),
        }),
      ),
    )

    const resultados = await Promise.all(promesas)
    const totalNotificaciones = resultados.reduce(
      (sum, r) => sum + r.notificaciones.length,
      0,
    )
    const portalesConError = resultados
      .filter((r) => !r.exito)
      .map((r) => r.portal)

    return {
      certificadoSerial: serialNumber,
      portalesConsultados: portalesActivos,
      resultados,
      totalNotificaciones,
      portalesConError,
      fechaConsulta: new Date().toISOString(),
    }
  }

  /**
   * Construye Chains para portales ADICIONALES (no DEHU) de un certificado.
   * DEHU se maneja via DehuOrquestador.construirCadena() por separado.
   */
  construirCadenaPortalesAdicionales(
    factory: Factory,
    serialNumber: string,
    certificadoId: string,
    portalesAdicionales: PortalNotificaciones[],
  ): Chain {
    const cadena = new Chain(`notif-${serialNumber}`)

    for (const portal of portalesAdicionales) {
      const bloqueConsulta = new PortalConsultaBlock(portal, serialNumber)
      cadena.agregarBloque(
        new Block(
          ProcessType.NOTIFICATION_CHECK,
          `Consultar ${portal} — ${serialNumber}`,
          bloqueConsulta,
        ),
      )

      const bloqueSync = new PortalSyncBlock(
        bloqueConsulta,
        certificadoId,
        this.apiUrl,
        this.token,
      )
      cadena.agregarBloque(
        new Block(
          ProcessType.DATA_SCRAPING,
          `Sincronizar ${portal} — ${serialNumber}`,
          bloqueSync,
        ),
      )
    }

    factory.agregarCadena(cadena)
    return cadena
  }

  /**
   * Construye cadenas batch para todos los portales (DEHU + adicionales).
   * DEHU usa DehuOrquestador (sin duplicar), adicionales usan PortalConsultaBlock.
   */
  construirCadenasBatch(
    factory: Factory,
    configs: Array<{
      serialNumber: string
      certificadoId: string
      configPortales: ConfigPortalesCertificado
      configDehu?: ConfigCertificadoDehu & { certificadoId: string }
    }>,
  ): void {
    for (const config of configs) {
      const portalesAdicionales = config.configPortales.portalesActivos.filter(
        (p) => p !== PortalNotificaciones.DEHU,
      )
      const incluyeDehu = config.configPortales.portalesActivos.includes(
        PortalNotificaciones.DEHU,
      )

      // DEHU: delegar a su orquestador especializado
      if (incluyeDehu && config.configDehu) {
        const dehuOrq = new DehuOrquestador(this.apiUrl, this.token)
        dehuOrq.construirCadena(factory, config.configDehu, config.certificadoId)
      }

      // Portales adicionales: cadena propia
      if (portalesAdicionales.length > 0) {
        this.construirCadenaPortalesAdicionales(
          factory,
          config.serialNumber,
          config.certificadoId,
          portalesAdicionales,
        )
      }
    }

    log.info(`[OrqNotif] Cadenas batch creadas para ${configs.length} certificados`)
  }

  // ── Privado: delegacion DEHU ─────────────────────────────

  private async consultarDehu(
    serialNumber: string,
    configDehu?: ConfigCertificadoDehu,
  ): Promise<ResultadoConsultaPortal> {
    if (!configDehu) {
      return {
        exito: false,
        portal: PortalNotificaciones.DEHU,
        certificadoSerial: serialNumber,
        estadoAutenticacion: EstadoAutenticacion.ERROR,
        notificaciones: [],
        error: 'configDehu requerida para portal DEHU',
        fechaConsulta: new Date().toISOString(),
      }
    }

    const dehuOrq = new DehuOrquestador(this.apiUrl, this.token)
    const resultadoDehu = await dehuOrq.consultarCertificado(configDehu)

    // Traducir ResultadoConsultaDEHU → ResultadoConsultaPortal
    const notificaciones = [
      ...resultadoDehu.notificaciones.map((n) => ({
        idExterno: `DEHU-${n.idDehu}`,
        portal: PortalNotificaciones.DEHU as PortalNotificaciones,
        tipo: n.tipo as 'Notificacion' | 'Comunicacion',
        titulo: n.titulo,
        organismo: n.organismo,
        fechaDisposicion: n.fechaDisposicion,
        fechaCaducidad: n.fechaCaducidad,
        estado: n.estado,
        rutaPdfLocal: n.rutaPdfLocal,
      })),
      ...resultadoDehu.comunicaciones.map((n) => ({
        idExterno: `DEHU-${n.idDehu}`,
        portal: PortalNotificaciones.DEHU as PortalNotificaciones,
        tipo: 'Comunicacion' as const,
        titulo: n.titulo,
        organismo: n.organismo,
        fechaDisposicion: n.fechaDisposicion,
        fechaCaducidad: n.fechaCaducidad,
        estado: n.estado,
        rutaPdfLocal: n.rutaPdfLocal,
      })),
    ]

    return {
      exito: resultadoDehu.exito,
      portal: PortalNotificaciones.DEHU,
      certificadoSerial: serialNumber,
      estadoAutenticacion: resultadoDehu.exito
        ? EstadoAutenticacion.AUTENTICADO
        : EstadoAutenticacion.ERROR,
      notificaciones,
      error: resultadoDehu.error,
      fechaConsulta: resultadoDehu.fechaConsulta,
    }
  }
}
