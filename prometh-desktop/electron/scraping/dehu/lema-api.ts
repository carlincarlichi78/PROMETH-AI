import log from 'electron-log'
import { XMLParser, XMLBuilder } from 'fast-xml-parser'
import { extraerCredencialesPfx, firmarXmlSoap } from './firma-xml'
import {
  TipoConsultaLema,
  EstadoAltaDehu,
  MetodoConsulta,
  type NotificacionDEHU,
  type ResultadoConsultaDEHU,
  type ConfigCertificadoDehu,
} from './tipos-dehu'

const LEMA_ENDPOINT = 'https://lema.redsara.es/ws/LemaServices'
const TIMEOUT_LEMA = 30_000
const NAMESPACE_LEMA = 'http://lema.redsara.es/ws'

/**
 * Wrapper para la API LEMA (SOAP XML con firma digital).
 * Metodo primario de consulta DEHU. Mas fiable que Puppeteer.
 */
/** Config con PFX obligatorio para LEMA */
type ConfigLema = ConfigCertificadoDehu & { rutaPfx: string; passwordPfx: string }

export class LemaApi {
  private readonly config: ConfigLema
  private readonly parser: XMLParser
  private readonly builder: XMLBuilder

  constructor(config: ConfigCertificadoDehu) {
    if (!config.rutaPfx || !config.passwordPfx) {
      throw new Error('LEMA API requiere rutaPfx y passwordPfx en la configuracion')
    }
    this.config = config as ConfigLema
    this.parser = new XMLParser({
      ignoreAttributes: false,
      removeNSPrefix: true,
      parseAttributeValue: true,
    })
    this.builder = new XMLBuilder({
      ignoreAttributes: false,
      suppressEmptyNode: true,
    })
  }

  /**
   * Verifica si el certificado tiene alta en LEMA.
   * Ejecuta una consulta ligera para determinar el estado.
   */
  async verificarAlta(): Promise<EstadoAltaDehu> {
    try {
      const xmlRequest = this.construirSoapRequest(
        TipoConsultaLema.PENDIENTES_NOTIFICACIONES,
      )
      const { clavePem, certificadoPem } = extraerCredencialesPfx(
        this.config.rutaPfx,
        this.config.passwordPfx,
      )
      const xmlFirmado = firmarXmlSoap(xmlRequest, clavePem, certificadoPem)
      const respuesta = await this.enviarSoap(xmlFirmado)

      if (this.esFaultSoap(respuesta)) {
        const mensajeFault = this.extraerMensajeFault(respuesta)
        if (
          mensajeFault.includes('NO_ALTA') ||
          mensajeFault.includes('no dado de alta')
        ) {
          log.info(
            `[LEMA] Certificado ${this.config.certificadoSerial} sin alta en LEMA`,
          )
          return EstadoAltaDehu.NO_ALTA
        }
        log.warn(`[LEMA] Fault inesperado al verificar alta: ${mensajeFault}`)
        return EstadoAltaDehu.DESCONOCIDO
      }

      log.info(
        `[LEMA] Certificado ${this.config.certificadoSerial} tiene alta en LEMA`,
      )
      return EstadoAltaDehu.ALTA
    } catch (error) {
      const msg = error instanceof Error ? error.message : 'Error desconocido'
      log.warn(`[LEMA] Error verificando alta: ${msg}`)
      return EstadoAltaDehu.DESCONOCIDO
    }
  }

  /**
   * Consulta notificaciones pendientes via SOAP.
   */
  async consultarPendientes(): Promise<NotificacionDEHU[]> {
    return this.ejecutarConsultaTipo(
      TipoConsultaLema.PENDIENTES_NOTIFICACIONES,
      'Notificacion',
    )
  }

  /**
   * Consulta comunicaciones pendientes via SOAP.
   */
  async consultarComunicaciones(): Promise<NotificacionDEHU[]> {
    return this.ejecutarConsultaTipo(
      TipoConsultaLema.PENDIENTES_COMUNICACIONES,
      'Comunicacion',
    )
  }

  /**
   * Consulta historico de notificaciones realizadas via SOAP.
   */
  async consultarRealizadas(): Promise<NotificacionDEHU[]> {
    return this.ejecutarConsultaTipo(
      TipoConsultaLema.HISTORICO_REALIZADAS,
      'Notificacion',
    )
  }

  /**
   * Ejecuta consulta completa (pendientes + realizadas + comunicaciones).
   * Retorna ResultadoConsultaDEHU con todos los resultados.
   */
  async ejecutarConsulta(): Promise<ResultadoConsultaDEHU> {
    const fechaConsulta = new Date().toISOString()

    try {
      // Realizadas puede fallar si LEMA no soporta HISTORICO_REALIZADAS
      // Usar allSettled para no romper pendientes/comunicaciones
      const [resPendientes, resRealizadas, resComunicaciones] = await Promise.allSettled([
        this.consultarPendientes(),
        this.consultarRealizadas(),
        this.consultarComunicaciones(),
      ])

      const pendientes = resPendientes.status === 'fulfilled' ? resPendientes.value : []
      const realizadas = resRealizadas.status === 'fulfilled' ? resRealizadas.value : []
      const comunicaciones = resComunicaciones.status === 'fulfilled' ? resComunicaciones.value : []

      if (resRealizadas.status === 'rejected') {
        log.warn(`[LEMA] HISTORICO_REALIZADAS no soportado: ${resRealizadas.reason}`)
      }
      if (resPendientes.status === 'rejected') {
        throw resPendientes.reason
      }

      const notificaciones = [...pendientes, ...realizadas]

      log.info(
        `[LEMA] Consulta completada — pendientes: ${pendientes.length}, realizadas: ${realizadas.length}, comunicaciones: ${comunicaciones.length}`,
      )

      return {
        exito: true,
        metodo: MetodoConsulta.LEMA_API,
        certificadoSerial: this.config.certificadoSerial,
        estadoAlta: EstadoAltaDehu.ALTA,
        notificaciones,
        comunicaciones,
        fechaConsulta,
      }
    } catch (error) {
      const msg = error instanceof Error ? error.message : 'Error desconocido'
      log.error(`[LEMA] Error en consulta completa: ${msg}`)

      return {
        exito: false,
        metodo: MetodoConsulta.LEMA_API,
        certificadoSerial: this.config.certificadoSerial,
        estadoAlta: this.config.estadoAlta ?? EstadoAltaDehu.DESCONOCIDO,
        notificaciones: [],
        comunicaciones: [],
        error: msg,
        fechaConsulta,
      }
    }
  }

  /**
   * Ejecuta una consulta SOAP para un tipo especifico.
   */
  private async ejecutarConsultaTipo(
    tipo: TipoConsultaLema,
    tipoNotif: 'Notificacion' | 'Comunicacion',
  ): Promise<NotificacionDEHU[]> {
    const xmlRequest = this.construirSoapRequest(tipo)
    const { clavePem, certificadoPem } = extraerCredencialesPfx(
      this.config.rutaPfx,
      this.config.passwordPfx,
    )
    const xmlFirmado = firmarXmlSoap(xmlRequest, clavePem, certificadoPem)
    const respuesta = await this.enviarSoap(xmlFirmado)

    if (this.esFaultSoap(respuesta)) {
      const mensajeFault = this.extraerMensajeFault(respuesta)
      throw new Error(`SOAP Fault: ${mensajeFault}`)
    }

    return this.parsearRespuesta(respuesta, tipoNotif)
  }

  /**
   * Construye el envelope SOAP XML para el tipo de consulta dado.
   */
  private construirSoapRequest(tipo: TipoConsultaLema): string {
    const soapEnvelope = {
      'soap:Envelope': {
        '@_xmlns:soap': 'http://schemas.xmlsoap.org/soap/envelope/',
        '@_xmlns:lem': NAMESPACE_LEMA,
        'soap:Header': {},
        'soap:Body': {
          'lem:consultaRequest': {
            'lem:tipoConsulta': tipo,
            'lem:nifTitular': '', // Se extrae del certificado al firmar
          },
        },
      },
    }

    return this.builder.build(soapEnvelope)
  }

  /**
   * Envia el SOAP request firmado y parsea la respuesta XML.
   */
  private async enviarSoap(xmlFirmado: string): Promise<Record<string, unknown>> {
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_LEMA)

    try {
      const response = await fetch(LEMA_ENDPOINT, {
        method: 'POST',
        headers: {
          'Content-Type': 'text/xml; charset=utf-8',
          SOAPAction: `${NAMESPACE_LEMA}/consulta`,
        },
        body: xmlFirmado,
        signal: controller.signal,
      })

      const textoRespuesta = await response.text()

      if (!response.ok) {
        throw new Error(
          `HTTP ${response.status}: ${response.statusText}`,
        )
      }

      return this.parser.parse(textoRespuesta) as Record<string, unknown>
    } finally {
      clearTimeout(timeoutId)
    }
  }

  /**
   * Verifica si la respuesta es un SOAP Fault.
   */
  private esFaultSoap(respuesta: Record<string, unknown>): boolean {
    const envelope = respuesta['Envelope'] as Record<string, unknown> | undefined
    if (!envelope) return false
    const body = envelope['Body'] as Record<string, unknown> | undefined
    if (!body) return false
    return 'Fault' in body
  }

  /**
   * Extrae el mensaje de error de un SOAP Fault.
   */
  private extraerMensajeFault(respuesta: Record<string, unknown>): string {
    try {
      const envelope = respuesta['Envelope'] as Record<string, unknown>
      const body = envelope['Body'] as Record<string, unknown>
      const fault = body['Fault'] as Record<string, unknown>
      return (
        (fault['faultstring'] as string) ??
        (fault['detail'] as string) ??
        'Error SOAP desconocido'
      )
    } catch {
      return 'Error SOAP desconocido'
    }
  }

  /**
   * Parsea la respuesta SOAP y extrae notificaciones.
   */
  private parsearRespuesta(
    respuesta: Record<string, unknown>,
    tipoNotif: 'Notificacion' | 'Comunicacion',
  ): NotificacionDEHU[] {
    try {
      const envelope = respuesta['Envelope'] as Record<string, unknown>
      const body = envelope['Body'] as Record<string, unknown>
      const consultaResponse = body['consultaResponse'] as Record<
        string,
        unknown
      >

      if (!consultaResponse) return []

      const items = consultaResponse['notificaciones'] ?? consultaResponse['comunicaciones']
      if (!items) return []

      const lista = Array.isArray(items) ? items : [items]

      return lista.map(
        (item: Record<string, unknown>): NotificacionDEHU => ({
          idDehu: String(item['codigoOrigen'] ?? item['id'] ?? ''),
          tipo: tipoNotif,
          titulo: String(item['concepto'] ?? item['titulo'] ?? 'Sin titulo'),
          titular: String(item['nifTitular'] ?? ''),
          ambito: String(item['ambito'] ?? ''),
          organismo: String(
            item['organismoEmisor'] ?? item['organismo'] ?? '',
          ),
          fechaDisposicion: String(
            item['fechaPuestaDisposicion'] ?? item['fecha'] ?? '',
          ),
          fechaCaducidad: item['fechaCaducidad']
            ? String(item['fechaCaducidad'])
            : null,
          estado: String(
            item['estado'] ?? 'Pendiente',
          ),
          tipoEnvio: item['tipoEnvio']
            ? String(item['tipoEnvio'])
            : undefined,
          rutaPdfLocal: null,
        }),
      )
    } catch (error) {
      log.error('[LEMA] Error parseando respuesta SOAP:', error)
      return []
    }
  }
}
