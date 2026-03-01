import log from 'electron-log'
import { LemaApi } from './lema-api'
import { DehuScraper } from './dehu-scraper'
import { Block } from '../block'
import { Chain } from '../chain'
import { BaseScraper } from '../base-scraper'
import { ProcessType, type ResultadoScraping, type ConfigScraping } from '../tipos'
import {
  EstadoAltaDehu,
  type ConfigCertificadoDehu,
  type ResultadoConsultaDEHU,
  type NotificacionDEHU,
} from './tipos-dehu'
import { sincronizarConCloud } from './sincronizar-cloud'
import type { Factory } from '../factory'

/**
 * Scraper wrapper para consulta DEHU (usado como Block en Chain).
 * Delega al orquestador que decide LEMA vs Puppeteer.
 */
class DehuConsultaBlock extends BaseScraper {
  private readonly configDehu: ConfigCertificadoDehu
  private readonly apiUrl: string
  private readonly token: string
  resultado: ResultadoConsultaDEHU | null = null

  constructor(
    configDehu: ConfigCertificadoDehu,
    apiUrl: string,
    token: string,
    configScraping?: Partial<ConfigScraping>,
  ) {
    super(configDehu.certificadoSerial, configScraping)
    this.configDehu = configDehu
    this.apiUrl = apiUrl
    this.token = token
  }

  get nombre(): string {
    return `DEHU-Consulta (${this.serialNumber})`
  }

  /**
   * No necesita navegador si usa LEMA.
   * Override run() para manejar ambos caminos.
   */
  async run(): Promise<ResultadoScraping> {
    try {
      const orquestador = new DehuOrquestador(this.apiUrl, this.token)
      this.resultado = await orquestador.consultarCertificado(this.configDehu)

      return {
        exito: this.resultado.exito,
        datos: this.resultado,
        error: this.resultado.error,
      }
    } catch (error) {
      const msg = error instanceof Error ? error.message : 'Error desconocido'
      return { exito: false, error: msg }
    }
  }

  async ejecutar(): Promise<ResultadoScraping> {
    // No se usa directamente — run() override maneja el flujo
    return { exito: false, error: 'Usar run() directamente' }
  }
}

/**
 * Scraper wrapper para sincronizacion con cloud (usado como Block en Chain).
 */
class DehuSyncBlock extends BaseScraper {
  private readonly bloqueConsulta: DehuConsultaBlock
  private readonly certificadoId: string
  private readonly apiUrl: string
  private readonly token: string

  constructor(
    bloqueConsulta: DehuConsultaBlock,
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
    return `DEHU-Sync (${this.serialNumber})`
  }

  /**
   * No necesita navegador. Override run() para sync directo.
   */
  async run(): Promise<ResultadoScraping> {
    try {
      const consulta = this.bloqueConsulta.resultado
      if (!consulta || !consulta.exito) {
        return {
          exito: false,
          error: 'No hay resultado de consulta para sincronizar',
        }
      }

      const todasNotif = [
        ...consulta.notificaciones,
        ...consulta.comunicaciones,
      ]

      if (todasNotif.length === 0) {
        return { exito: true, datos: { nuevas: 0, actualizadas: 0, errores: 0 } }
      }

      const resultado = await sincronizarConCloud(
        todasNotif,
        this.certificadoId,
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

/**
 * Orquestador DEHU: coordina LEMA + Puppeteer por certificado.
 *
 * Flujo por certificado:
 * 1. Verificar estado de alta en LEMA
 * 2. Si ALTA: consultar via LemaApi
 * 3. Si NO_ALTA o LEMA falla: fallback a DehuScraper (Puppeteer)
 * 4. Sincronizar resultados con API cloud
 */
export class DehuOrquestador {
  private readonly apiUrl: string
  private readonly token: string

  constructor(apiUrl: string, token: string) {
    this.apiUrl = apiUrl
    this.token = token
  }

  /**
   * Consulta DEHU para un certificado.
   * Intenta LEMA primero, fallback a Puppeteer.
   */
  async consultarCertificado(
    config: ConfigCertificadoDehu,
  ): Promise<ResultadoConsultaDEHU> {
    log.info(
      `[DehuOrquestador] Consultando cert: ${config.certificadoSerial}`,
    )

    // Intentar LEMA si tiene alta o no sabemos
    if (config.estadoAlta !== EstadoAltaDehu.NO_ALTA) {
      try {
        const lema = new LemaApi(config)
        const resultadoLema = await lema.ejecutarConsulta()

        if (resultadoLema.exito) {
          log.info('[DehuOrquestador] Consulta LEMA exitosa')

          // LEMA no soporta HISTORICO_REALIZADAS de forma fiable.
          // Complementar con Puppeteer para obtener realizadas.
          const tieneRealizadas = resultadoLema.notificaciones.some(
            (n) => n.estado !== 'Pendiente de abrir' && n.estado !== 'Pendiente',
          )

          if (!tieneRealizadas) {
            log.info('[DehuOrquestador] LEMA sin realizadas, complementando con Puppeteer')
            try {
              const resultadoPuppeteer = await this.consultarConPuppeteer(config)
              if (resultadoPuppeteer.exito) {
                // Extraer solo las realizadas del Puppeteer (las que no son "Pendiente de abrir")
                const realizadasPuppeteer = resultadoPuppeteer.notificaciones.filter(
                  (n) => n.estado !== 'Pendiente de abrir' && n.estado !== 'Pendiente',
                )
                if (realizadasPuppeteer.length > 0) {
                  log.info(`[DehuOrquestador] Puppeteer aporto ${realizadasPuppeteer.length} realizadas`)
                  resultadoLema.notificaciones = [
                    ...resultadoLema.notificaciones,
                    ...realizadasPuppeteer,
                  ]
                }
                // Tambien complementar comunicaciones si LEMA no trajo
                if (resultadoLema.comunicaciones.length === 0 && resultadoPuppeteer.comunicaciones.length > 0) {
                  resultadoLema.comunicaciones = resultadoPuppeteer.comunicaciones
                }
              }
            } catch (puppErr) {
              log.warn('[DehuOrquestador] Puppeteer complementario fallo:', puppErr)
            }
          }

          return resultadoLema
        }

        log.warn(
          `[DehuOrquestador] LEMA fallo: ${resultadoLema.error}, intentando Puppeteer`,
        )
      } catch (error) {
        log.warn(
          '[DehuOrquestador] Error en LEMA, fallback a Puppeteer:',
          error instanceof Error ? error.message : error,
        )
      }
    }

    // Fallback completo a Puppeteer
    return this.consultarConPuppeteer(config)
  }

  /**
   * Consulta via Puppeteer (scraping web).
   */
  private async consultarConPuppeteer(
    config: ConfigCertificadoDehu,
  ): Promise<ResultadoConsultaDEHU> {
    log.info('[DehuOrquestador] Ejecutando scraping Puppeteer DEHU')

    const scraper = new DehuScraper(config)
    const resultado = await scraper.run()

    if (resultado.exito && resultado.datos) {
      return resultado.datos as ResultadoConsultaDEHU
    }

    return {
      exito: false,
      metodo: MetodoConsulta.PUPPETEER,
      certificadoSerial: config.certificadoSerial,
      estadoAlta: config.estadoAlta ?? EstadoAltaDehu.DESCONOCIDO,
      notificaciones: [],
      comunicaciones: [],
      error: resultado.error ?? 'Error en scraping Puppeteer',
      fechaConsulta: new Date().toISOString(),
    }
  }

  /**
   * Descarga el PDF de una notificacion concreta.
   * Siempre usa Puppeteer (LEMA no permite descarga directa de PDFs).
   * Usa runDescargarPdf() que gestiona login completo + descarga + cierre.
   */
  async descargarNotificacion(
    config: ConfigCertificadoDehu,
    notificacion: NotificacionDEHU,
    configScraping?: Partial<ConfigScraping>,
  ): Promise<{ exito: boolean; rutaLocal?: string; error?: string }> {
    log.info(
      `[DehuOrquestador] Descargando PDF: ${notificacion.titulo}`,
    )

    const scraper = new DehuScraper(config, configScraping)

    try {
      const ruta = await scraper.runDescargarPdf(notificacion)

      if (ruta) {
        return { exito: true, rutaLocal: ruta }
      }

      return { exito: false, error: 'No se pudo descargar el PDF' }
    } catch (error) {
      const msg = error instanceof Error ? error.message : 'Error desconocido'
      return { exito: false, error: msg }
    }
  }

  /**
   * Construye una Chain de bloques para un certificado y la agrega a la factory.
   * Bloque 1: Consulta DEHU (LEMA + fallback Puppeteer)
   * Bloque 2: Sincronizacion con cloud
   */
  construirCadena(
    factory: Factory,
    config: ConfigCertificadoDehu,
    certificadoId: string,
  ): Chain {
    const cadena = new Chain(config.certificadoSerial)

    // Bloque consulta DEHU
    const bloqueConsulta = new DehuConsultaBlock(
      config,
      this.apiUrl,
      this.token,
    )
    cadena.agregarBloque(
      new Block(
        ProcessType.NOTIFICATION_CHECK,
        `Consultar DEHU — ${config.certificadoSerial}`,
        bloqueConsulta,
      ),
    )

    // Bloque sincronizacion cloud
    const bloqueSync = new DehuSyncBlock(
      bloqueConsulta,
      certificadoId,
      this.apiUrl,
      this.token,
    )
    cadena.agregarBloque(
      new Block(
        ProcessType.DATA_SCRAPING,
        `Sincronizar cloud — ${config.certificadoSerial}`,
        bloqueSync,
      ),
    )

    factory.agregarCadena(cadena)
    log.info(
      `[DehuOrquestador] Cadena creada para cert: ${config.certificadoSerial}`,
    )

    return cadena
  }

  /**
   * Construye cadenas para multiples certificados.
   */
  construirCadenasBatch(
    factory: Factory,
    configs: Array<ConfigCertificadoDehu & { certificadoId: string }>,
  ): void {
    for (const config of configs) {
      this.construirCadena(factory, config, config.certificadoId)
    }
    log.info(
      `[DehuOrquestador] ${configs.length} cadenas creadas en batch`,
    )
  }
}

// Re-export MetodoConsulta para usar en consultarConPuppeteer
import { MetodoConsulta } from './tipos-dehu'
