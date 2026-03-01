import log from 'electron-log'
import { DehuOrquestador } from './dehu/dehu-orquestador'
import { OrquestadorNotificaciones } from './notificaciones/orquestador-notificaciones'
import { OrquestadorDocumentales } from './documentales/orquestador-documentales'
import { PortalNotificaciones } from './notificaciones/tipos-notificaciones'
import type { ConfigCertificadoDehu } from './dehu/tipos-dehu'
import type { TipoDocumento } from './documentales/tipos-documentales'
import type { Factory } from './factory'

/** Configuracion de un certificado para consulta multi-dominio */
export interface ConfigMultiCert {
  certificadoSerial: string
  certificadoId: string
  nombreCert?: string
  /** Thumbprint del cert en almacen Windows (para exportar PFX temporal si DEHU) */
  thumbprint?: string
  dehu?: ConfigCertificadoDehu
  portalesNotificaciones?: PortalNotificaciones[]
  documentos?: TipoDocumento[]
  datosExtraDocs?: Record<string, unknown>
}

/** Resultado de una ejecucion multi-cert */
export interface ResultadoMultiCert {
  fecha: string
  duracionMs: number
  totalCadenas: number
  certificados: Array<{
    serial: string
    nombre?: string
    dominios: {
      dehu?: boolean
      notificaciones?: string[]
      documentos?: string[]
    }
    estado: 'completado' | 'parcial' | 'fallido'
    errores?: string[]
  }>
}

/**
 * Orquestador global que coordina DEHU + Notificaciones + Documentales
 * para multiples certificados en una sola ejecucion de la Factory.
 *
 * Delega a los orquestadores especializados existentes sin duplicar logica.
 */
export class OrquestadorGlobal {
  private readonly apiUrl: string
  private readonly token: string

  constructor(apiUrl: string, token: string) {
    this.apiUrl = apiUrl
    this.token = token
  }

  /**
   * Construye cadenas para todos los dominios y certificados.
   * NO limpia la factory — el caller decide cuando limpiar.
   */
  construirCadenasMultiCert(
    factory: Factory,
    configuraciones: ConfigMultiCert[],
  ): void {
    let totalCadenas = 0

    for (const config of configuraciones) {
      const { certificadoSerial, certificadoId } = config

      // DEHU
      if (config.dehu) {
        const dehuOrq = new DehuOrquestador(this.apiUrl, this.token)
        dehuOrq.construirCadena(factory, config.dehu, certificadoId)
        totalCadenas++
      }

      // Notificaciones (portales adicionales, sin DEHU que ya se manejo arriba)
      const portalesAdicionales = (config.portalesNotificaciones ?? []).filter(
        (p) => p !== PortalNotificaciones.DEHU,
      )
      if (portalesAdicionales.length > 0) {
        const notifOrq = new OrquestadorNotificaciones(this.apiUrl, this.token)
        notifOrq.construirCadenaPortalesAdicionales(
          factory,
          certificadoSerial,
          certificadoId,
          portalesAdicionales,
        )
        totalCadenas++
      }

      // Documentales
      if (config.documentos && config.documentos.length > 0) {
        const docOrq = new OrquestadorDocumentales()
        docOrq.construirCadena(factory, {
          certificadoSerial,
          documentosActivos: config.documentos,
          datosExtra: config.datosExtraDocs,
        })
        totalCadenas++
      }
    }

    log.info(
      `[OrqGlobal] ${totalCadenas} cadenas creadas para ${configuraciones.length} certificados`,
    )
  }
}
