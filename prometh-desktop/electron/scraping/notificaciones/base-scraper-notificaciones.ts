import log from 'electron-log'
import { BaseScraper } from '../base-scraper'
import type { ResultadoScraping, ConfigScraping } from '../tipos'
import type { NotificacionPortal, ResultadoConsultaPortal } from './tipos-notificaciones'
import { type PortalNotificaciones, EstadoAutenticacion } from './tipos-notificaciones'

/**
 * Clase base abstracta para scrapers de portales de notificaciones.
 * Hereda de BaseScraper (BrowserWindow) y anade contrato especifico de notificaciones.
 *
 * Cada scraper concreto implementa:
 * - urlPortal: URL de acceso al portal
 * - portal: identificador del portal
 * - ejecutarConsulta(): navegar + autenticar + extraer notificaciones
 */
export abstract class BaseScraperNotificaciones extends BaseScraper {
  /** URL de acceso al portal */
  protected abstract readonly urlPortal: string

  /** Identificador del portal */
  protected abstract readonly portal: PortalNotificaciones

  constructor(serialNumber: string, configScraping?: Partial<ConfigScraping>) {
    super(serialNumber, configScraping)
  }

  /**
   * Logica especifica de cada portal.
   * Navega, autentica y extrae notificaciones.
   */
  protected abstract ejecutarConsulta(): Promise<NotificacionPortal[]>

  /**
   * Implementacion de ejecutar() requerida por BaseScraper.
   * Delega a ejecutarConsulta() y envuelve en ResultadoConsultaPortal.
   */
  async ejecutar(): Promise<ResultadoScraping> {
    try {
      const notificaciones = await this.ejecutarConsulta()
      const resultado: ResultadoConsultaPortal = {
        exito: true,
        portal: this.portal,
        certificadoSerial: this.serialNumber,
        estadoAutenticacion: EstadoAutenticacion.AUTENTICADO,
        notificaciones,
        fechaConsulta: new Date().toISOString(),
      }
      return { exito: true, datos: resultado }
    } catch (error) {
      const msg = error instanceof Error ? error.message : 'Error desconocido'
      log.error(`[${this.nombre}] Error en ejecutarConsulta: ${msg}`)
      const resultado: ResultadoConsultaPortal = {
        exito: false,
        portal: this.portal,
        certificadoSerial: this.serialNumber,
        estadoAutenticacion: EstadoAutenticacion.ERROR,
        notificaciones: [],
        error: msg,
        fechaConsulta: new Date().toISOString(),
      }
      return { exito: false, datos: resultado, error: msg }
    }
  }

  /**
   * Genera idExterno unico para una notificacion.
   * Formato: `${portal}-${serialNumber}-${idInterno}`
   */
  protected generarIdExterno(idInterno: string): string {
    return `${this.portal}-${this.serialNumber}-${idInterno}`
  }

  /**
   * Normaliza fecha texto (dd/mm/yyyy) a ISO string.
   */
  protected normalizarFecha(fecha: string): string {
    if (!fecha) return new Date().toISOString()
    const partes = fecha.match(/(\d{2})\/(\d{2})\/(\d{4})/)
    if (partes) {
      return new Date(
        `${partes[3]}-${partes[2]}-${partes[1]}T00:00:00.000Z`,
      ).toISOString()
    }
    try {
      return new Date(fecha).toISOString()
    } catch {
      return new Date().toISOString()
    }
  }
}
