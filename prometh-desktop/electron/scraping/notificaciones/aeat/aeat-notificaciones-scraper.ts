import log from 'electron-log'
import { BaseScraperNotificaciones } from '../base-scraper-notificaciones'
import { PortalNotificaciones } from '../tipos-notificaciones'
import type { NotificacionPortal } from '../tipos-notificaciones'
import type { ConfigScraping } from '../../tipos'

const SELECTORES = {
  indicadorLogin:
    '#cabeceraNombre, .nombre-usuario, .acceso-identificado',
  tablaNotificaciones:
    '#tablaNotificaciones, table.listado-notificaciones, .resultado-consulta table',
  filasTabla:
    '#tablaNotificaciones tbody tr, table.listado-notificaciones tbody tr',
  sinResultados: '.sin-notificaciones, .no-resultados, #mensajeSinDatos',
}

const TIMEOUT_AUTH = 30_000
const TIMEOUT_TABLA = 15_000

/**
 * Scraper para las notificaciones directas de la AEAT (Agencia Tributaria).
 * Extrae notificaciones del procedimiento GF01 en la sede electronica.
 *
 * Auth: certificado via Cl@ve (selectedIdP('AFIRMA')) — hereda de BaseScraper
 */
export class ScraperAeatNotificaciones extends BaseScraperNotificaciones {
  protected readonly urlPortal =
    'https://www.agenciatributaria.gob.es/AEAT.sede/procedimientoini/GF01.shtml'
  protected readonly portal = PortalNotificaciones.AEAT_DIRECTA

  constructor(serialNumber: string, configScraping?: Partial<ConfigScraping>) {
    super(serialNumber, configScraping)
  }

  get nombre(): string {
    return 'AEAT-Notificaciones'
  }

  protected async ejecutarConsulta(): Promise<NotificacionPortal[]> {
    await this.navegar(this.urlPortal)
    await this.esperar(3000)

    // AEAT redirige a Cl@ve para autenticacion — usar selectedIdP('AFIRMA')
    await this.manejarPasarelaClave(10_000, 30_000)

    try {
      await this.esperarElemento(SELECTORES.indicadorLogin, TIMEOUT_AUTH)
    } catch {
      log.warn(`[${this.nombre}] Timeout esperando autenticacion`)
      await this.capturarPantalla('aeat-notif-sin-auth')
      return []
    }

    const haySinResultados = await this.ejecutarJS<boolean>(`
      !!document.querySelector('${SELECTORES.sinResultados.replace(/'/g, "\\\'")}')
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
      (function() {
        var filas = document.querySelectorAll('${SELECTORES.filasTabla.replace(/'/g, "\\\\'")}');
        return Array.from(filas).map(function(fila) {
          var celdas = fila.querySelectorAll('td');
          if (celdas.length < 3) return null;
          return {
            titulo: celdas[0] ? celdas[0].textContent.trim() : 'Sin titulo',
            organismo: celdas[1] ? celdas[1].textContent.trim() || 'Agencia Tributaria' : 'Agencia Tributaria',
            fechaTexto: celdas[2] ? celdas[2].textContent.trim() : '',
            estado: celdas[3] ? celdas[3].textContent.trim() : 'Pendiente',
            enlace: fila.querySelector('a') ? fila.querySelector('a').getAttribute('href') || '' : '',
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
        idExterno: this.generarIdExterno(datos.enlace || `aeat-${i}`),
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
