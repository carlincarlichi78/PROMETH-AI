import log from 'electron-log'
import { BaseScraper } from '../base-scraper'
import { Block } from '../block'
import { Chain } from '../chain'
import { ProcessType, type ResultadoScraping, type ConfigScraping } from '../tipos'
import {
  TipoDocumento,
  type ConfigDocumentosCertificado,
  type ResultadoDescarga,
  type RegistroHistorialDescarga,
} from './tipos-documentales'
import { registrarDescarga } from './historial-descargas'
import type { Factory } from '../factory'
import type { BaseScraperDocumental } from './base-scraper-documental'

// Imports de scrapers concretos
import { ScraperDeudasAeat } from './aeat/deudas-aeat'
import { ScraperDatosFiscales } from './aeat/datos-fiscales'
import { ScraperCertificadosIrpf } from './aeat/certificados-irpf'
import { ScraperCnaeAutonomo } from './aeat/cnae-autonomo'
import { ScraperIaeActividades } from './aeat/iae-actividades'
import { ScraperDeudasSS } from './seguridad-social/deudas-ss'
import { ScraperVidaLaboral } from './seguridad-social/vida-laboral'
import { ScraperCertificadoINSS } from './seguridad-social/certificado-inss'
import { ScraperConsultaVehiculos } from './carpeta-ciudadana/consulta-vehiculos'
import { ScraperConsultaInmuebles } from './carpeta-ciudadana/consulta-inmuebles'
import { ScraperEmpadronamiento } from './carpeta-ciudadana/empadronamiento'
import { ScraperCertificadoPenales } from './carpeta-ciudadana/certificado-penales'
import { ScraperCertificadoNacimiento } from './justicia/certificado-nacimiento'
import { ScraperApudActa } from './justicia/apud-acta'
import { ScraperCertificadoMatrimonio } from './justicia/certificado-matrimonio'
import { ScraperDeudasHacienda } from './aeat/deudas-hacienda'
import { ScraperCertificadoSepe } from './otros/certificado-sepe'
import { ScraperSolicitudCirbe } from './otros/solicitud-cirbe'
import { ScraperObtencionCirbe } from './otros/obtencion-cirbe'
import { ScraperLicitacionesGeneral } from './licitaciones/procedimientos-general'
import { ScraperLicitacionesMadrid } from './licitaciones/procedimientos-madrid'
import { ScraperLicitacionesAndalucia } from './licitaciones/procedimientos-andalucia'
import { ScraperLicitacionesValencia } from './licitaciones/procedimientos-valencia'
import { ScraperLicitacionesCatalunya } from './licitaciones/procedimientos-catalunya'

/** Crea el scraper concreto segun el tipo de documento */
function crearScraper(
  tipo: TipoDocumento,
  serialNumber: string,
  config?: Partial<ConfigScraping>,
  datosExtra?: Record<string, unknown>,
): BaseScraperDocumental {
  switch (tipo) {
    // AEAT
    case TipoDocumento.DEUDAS_AEAT:
      return new ScraperDeudasAeat(serialNumber, config)
    case TipoDocumento.DATOS_FISCALES:
      return new ScraperDatosFiscales(serialNumber, config)
    case TipoDocumento.CERTIFICADOS_IRPF:
      return new ScraperCertificadosIrpf(serialNumber, config)
    case TipoDocumento.CNAE_AUTONOMO:
      return new ScraperCnaeAutonomo(serialNumber, config)
    case TipoDocumento.IAE_ACTIVIDADES:
      return new ScraperIaeActividades(serialNumber, config)
    // Seguridad Social
    case TipoDocumento.DEUDAS_SS: {
      const datosSS = (datosExtra ?? {}) as { tipoCertificado?: string }
      return new ScraperDeudasSS(serialNumber, config, datosSS)
    }
    case TipoDocumento.VIDA_LABORAL:
      return new ScraperVidaLaboral(serialNumber, config)
    case TipoDocumento.CERTIFICADO_INSS:
      return new ScraperCertificadoINSS(serialNumber, config)
    // Carpeta Ciudadana
    case TipoDocumento.CONSULTA_VEHICULOS:
      return new ScraperConsultaVehiculos(serialNumber, config)
    case TipoDocumento.CONSULTA_INMUEBLES:
      return new ScraperConsultaInmuebles(serialNumber, config)
    case TipoDocumento.EMPADRONAMIENTO:
      return new ScraperEmpadronamiento(serialNumber, config)
    case TipoDocumento.CERTIFICADO_PENALES:
      return new ScraperCertificadoPenales(serialNumber, config)
    // Justicia
    case TipoDocumento.CERTIFICADO_NACIMIENTO:
      return new ScraperCertificadoNacimiento(serialNumber, config)
    case TipoDocumento.APUD_ACTA:
      return new ScraperApudActa(serialNumber, config)
    case TipoDocumento.CERTIFICADO_MATRIMONIO:
      return new ScraperCertificadoMatrimonio(serialNumber, config)
    // Hacienda
    case TipoDocumento.DEUDAS_HACIENDA:
      return new ScraperDeudasHacienda(serialNumber, config)
    // Otros
    case TipoDocumento.CERTIFICADO_SEPE:
      return new ScraperCertificadoSepe(serialNumber, config)
    case TipoDocumento.SOLICITUD_CIRBE: {
      const datosCirbe = (datosExtra ?? {}) as { email: string; fechaNacimiento?: string }
      return new ScraperSolicitudCirbe(serialNumber, datosCirbe, config)
    }
    case TipoDocumento.OBTENCION_CIRBE:
      return new ScraperObtencionCirbe(serialNumber, config)
    // Licitaciones
    case TipoDocumento.PROC_ABIERTOS_GENERAL:
      return new ScraperLicitacionesGeneral(serialNumber, config)
    case TipoDocumento.PROC_ABIERTOS_MADRID:
      return new ScraperLicitacionesMadrid(serialNumber, config)
    case TipoDocumento.PROC_ABIERTOS_ANDALUCIA:
      return new ScraperLicitacionesAndalucia(serialNumber, config)
    case TipoDocumento.PROC_ABIERTOS_VALENCIA:
      return new ScraperLicitacionesValencia(serialNumber, config)
    case TipoDocumento.PROC_ABIERTOS_CATALUNYA:
      return new ScraperLicitacionesCatalunya(serialNumber, config)
    default:
      throw new Error(`Tipo de documento no soportado: ${tipo}`)
  }
}

/**
 * Bloque wrapper que ejecuta un scraper documental como Block en una Chain.
 * Override de run() porque BaseScraperDocumental no hereda de BaseScraper (Puppeteer).
 */
class DocDescargaBlock extends BaseScraper {
  private readonly tipo: TipoDocumento
  private readonly configScraping: Partial<ConfigScraping> | undefined
  private readonly datosExtra: Record<string, unknown> | undefined

  constructor(
    tipo: TipoDocumento,
    serialNumber: string,
    configScraping?: Partial<ConfigScraping>,
    datosExtra?: Record<string, unknown>,
  ) {
    super(serialNumber, configScraping)
    this.tipo = tipo
    this.configScraping = configScraping
    this.datosExtra = datosExtra
  }

  get nombre(): string {
    return `DocDescarga-${this.tipo} (${this.serialNumber})`
  }

  /** Override run() — no necesita Puppeteer, delega al scraper documental */
  async run(): Promise<ResultadoScraping> {
    try {
      const scraper = crearScraper(
        this.tipo,
        this.serialNumber,
        this.configScraping,
        this.datosExtra,
      )
      const resultado = await scraper.run()

      // Registrar en historial local
      const rutasArchivos = resultado.datos
        ? ((resultado.datos as Record<string, unknown>).rutasArchivos as string[] ?? [])
        : resultado.rutaDescarga
          ? [resultado.rutaDescarga]
          : []

      const registro: RegistroHistorialDescarga = {
        certificadoSerial: this.serialNumber,
        tipo: this.tipo,
        exito: resultado.exito,
        rutasArchivos,
        fechaDescarga: new Date().toISOString(),
        error: resultado.error,
      }
      registrarDescarga(registro)

      return resultado
    } catch (error) {
      const msg = error instanceof Error ? error.message : 'Error desconocido'
      log.error(`[${this.nombre}] Error:`, msg)

      registrarDescarga({
        certificadoSerial: this.serialNumber,
        tipo: this.tipo,
        exito: false,
        rutasArchivos: [],
        fechaDescarga: new Date().toISOString(),
        error: msg,
      })

      return { exito: false, error: msg }
    }
  }

  async ejecutar(): Promise<ResultadoScraping> {
    // No se usa — run() override maneja el flujo
    return { exito: false, error: 'Usar run() directamente' }
  }
}

/**
 * Orquestador de scrapers documentales.
 * Construye cadenas para la Factory con N bloques (1 por documento activo).
 */
export class OrquestadorDocumentales {
  /** Construye una Chain para un certificado con sus documentos activos */
  construirCadena(
    factory: Factory,
    config: ConfigDocumentosCertificado,
  ): Chain {
    const cadena = new Chain(config.certificadoSerial)

    for (const tipo of config.documentosActivos) {
      const bloque = new DocDescargaBlock(
        tipo,
        config.certificadoSerial,
        undefined,
        config.datosExtra,
      )
      cadena.agregarBloque(
        new Block(
          ProcessType.DOCUMENT_DOWNLOAD,
          `Descargar ${tipo} — ${config.certificadoSerial}`,
          bloque,
        ),
      )
    }

    factory.agregarCadena(cadena)
    log.info(
      `[OrquestadorDocs] Cadena creada: ${config.certificadoSerial} — ${config.documentosActivos.length} documentos`,
    )

    return cadena
  }

  /** Construye cadenas para multiples certificados */
  construirCadenasBatch(
    factory: Factory,
    configs: ConfigDocumentosCertificado[],
  ): void {
    for (const config of configs) {
      this.construirCadena(factory, config)
    }
    log.info(
      `[OrquestadorDocs] ${configs.length} cadenas creadas en batch`,
    )
  }

  /** Descarga un documento individual sin Factory */
  async descargarDocumento(
    tipo: TipoDocumento,
    serialNumber: string,
    configScraping?: Partial<ConfigScraping>,
    datosExtra?: Record<string, unknown>,
  ): Promise<ResultadoDescarga> {
    const inicio = Date.now()

    try {
      const scraper = crearScraper(tipo, serialNumber, configScraping, datosExtra)
      const resultado = await scraper.run()

      const rutasArchivos = resultado.datos
        ? ((resultado.datos as Record<string, unknown>).rutasArchivos as string[] ?? [])
        : resultado.rutaDescarga
          ? [resultado.rutaDescarga]
          : []

      const descarga: ResultadoDescarga = {
        tipo,
        exito: resultado.exito,
        rutasArchivos,
        error: resultado.error,
        fechaDescarga: new Date().toISOString(),
        duracionMs: Date.now() - inicio,
      }

      registrarDescarga({
        certificadoSerial: serialNumber,
        tipo,
        exito: resultado.exito,
        rutasArchivos,
        fechaDescarga: descarga.fechaDescarga,
        error: resultado.error,
      })

      return descarga
    } catch (error) {
      const msg = error instanceof Error ? error.message : 'Error desconocido'
      return {
        tipo,
        exito: false,
        rutasArchivos: [],
        error: msg,
        fechaDescarga: new Date().toISOString(),
        duracionMs: Date.now() - inicio,
      }
    }
  }
}
