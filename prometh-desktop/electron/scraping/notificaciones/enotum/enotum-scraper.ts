import log from 'electron-log'
import { BaseScraperNotificaciones } from '../base-scraper-notificaciones'
import { PortalNotificaciones } from '../tipos-notificaciones'
import type { NotificacionPortal } from '../tipos-notificaciones'
import type { ConfigScraping } from '../../tipos'

const SELECTORES = {
  indicadorLogin: '.user-logged, .nom-usuari, #dades-usuari',
  tablaNotificaciones:
    '.llista-notificacions, table#notificacions, .taula-resultats',
  filasTabla:
    '.llista-notificacions tr, table#notificacions tbody tr',
  sinResultados: '.sense-resultats, .no-notificacions, .missatge-buit',
}

const TIMEOUT_AUTH = 30_000
const TIMEOUT_TABLA = 15_000

/**
 * Scraper para e-NOTUM de la Generalitat de Catalunya.
 * Extrae notificaciones electronicas del portal usuari.enotum.cat.
 */
export class ScraperEnotum extends BaseScraperNotificaciones {
  protected readonly urlPortal = 'https://usuari.enotum.cat/'
  protected readonly portal = PortalNotificaciones.E_NOTUM

  constructor(serialNumber: string, configScraping?: Partial<ConfigScraping>) {
    super(serialNumber, configScraping)
  }

  get nombre(): string {
    return 'e-NOTUM'
  }

  protected async ejecutarConsulta(): Promise<NotificacionPortal[]> {
    await this.navegar(this.urlPortal)
    await this.esperar(3000)

    // e-NOTUM puede redirigir a Cl@ve para autenticacion
    await this.manejarPasarelaClave(10_000, 30_000)

    try {
      await this.esperarElemento(SELECTORES.indicadorLogin, TIMEOUT_AUTH)
    } catch {
      log.warn(`[${this.nombre}] Timeout esperando autenticacion`)
      await this.capturarPantalla('enotum-sin-auth')
      return []
    }

    const haySinResultados = await this.ejecutarJS<boolean>(`
      !!document.querySelector('${SELECTORES.sinResultados.replace(/'/g, "\\'")}')
    `)
    if (haySinResultados) {
      log.info(`[${this.nombre}] Sin notificaciones`)
      return []
    }

    try {
      await this.esperarElemento(SELECTORES.tablaNotificaciones, TIMEOUT_TABLA)
    } catch {
      log.warn(`[${this.nombre}] Tabla no encontrada`)
      return []
    }

    return this.extraerFilas()
  }

  private async extraerFilas(): Promise<NotificacionPortal[]> {
    if (!this.window) return []

    const datosFilas = await this.ejecutarJS<Array<{
      titulo: string
      organismo: string
      fechaTexto: string
      estado: string
      enlace: string
    } | null>>(`
      (() => {
        const filas = document.querySelectorAll('${SELECTORES.filasTabla.replace(/'/g, "\\'")}');
        return Array.from(filas).map(fila => {
          const celdas = fila.querySelectorAll('td');
          if (celdas.length < 3) return null;
          return {
            titulo: celdas[0]?.textContent?.trim() ?? 'Sin titulo',
            organismo: celdas[1]?.textContent?.trim() || 'Generalitat de Catalunya',
            fechaTexto: celdas[2]?.textContent?.trim() ?? '',
            estado: celdas[3]?.textContent?.trim() ?? 'Pendent',
            enlace: fila.querySelector('a')?.getAttribute('href') ?? '',
          };
        });
      })()
    `)

    if (!datosFilas) return []

    const resultado: NotificacionPortal[] = []

    for (let i = 0; i < datosFilas.length; i++) {
      const datos = datosFilas[i]
      if (!datos || !datos.titulo) continue

      resultado.push({
        idExterno: this.generarIdExterno(datos.enlace || `enotum-${i}`),
        portal: this.portal,
        tipo: 'Notificacion',
        titulo: datos.titulo,
        organismo: datos.organismo,
        fechaDisposicion: this.normalizarFecha(datos.fechaTexto),
        fechaCaducidad: null,
        estado: datos.estado,
        rutaPdfLocal: null,
      })
    }

    log.info(`[${this.nombre}] ${resultado.length} notificaciones extraidas`)
    return resultado
  }
}
