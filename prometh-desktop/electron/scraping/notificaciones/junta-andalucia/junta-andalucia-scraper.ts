import log from 'electron-log'
import { BaseScraperNotificaciones } from '../base-scraper-notificaciones'
import { PortalNotificaciones } from '../tipos-notificaciones'
import type { NotificacionPortal } from '../tipos-notificaciones'
import type { ConfigScraping } from '../../tipos'

const SELECTORES = {
  botonCertificado:
    '#certificadoDigital, .btn-certificado, a[href*="certificado"]',
  indicadorLogin: '.usuario-autenticado, .datos-usuario, #panel-principal',
  tablaNotificaciones:
    'table.listado, .tabla-notificaciones, #tabla-avisos',
  filasTabla:
    'table.listado tbody tr, .tabla-notificaciones tbody tr',
  sinResultados: '.sin-notificaciones, .mensaje-vacio',
}

const TIMEOUT_CLICK = 10_000
const TIMEOUT_AUTH = 30_000
const TIMEOUT_TABLA = 15_000

/**
 * Scraper para el portal Notifica de la Junta de Andalucia.
 * Extrae avisos y notificaciones del portal ws020.juntadeandalucia.es.
 */
export class ScraperJuntaAndalucia extends BaseScraperNotificaciones {
  protected readonly urlPortal =
    'https://ws020.juntadeandalucia.es/Notifica/auth/login'
  protected readonly portal = PortalNotificaciones.JUNTA_ANDALUCIA

  constructor(serialNumber: string, configScraping?: Partial<ConfigScraping>) {
    super(serialNumber, configScraping)
  }

  get nombre(): string {
    return 'Junta-Andalucia'
  }

  protected async ejecutarConsulta(): Promise<NotificacionPortal[]> {
    await this.navegar(this.urlPortal)
    await this.esperar(3000)

    // Click boton acceso con certificado (si existe en la pagina)
    try {
      await this.esperarElemento(SELECTORES.botonCertificado, TIMEOUT_CLICK)
      await this.clic(SELECTORES.botonCertificado)
      await this.esperar(2000)
    } catch {
      log.warn(`[${this.nombre}] Boton certificado no encontrado, verificando Cl@ve...`)
    }

    // Junta Andalucia puede redirigir a Cl@ve
    await this.manejarPasarelaClave(10_000, 30_000)

    // Esperar autenticacion
    try {
      await this.esperarElemento(SELECTORES.indicadorLogin, TIMEOUT_AUTH)
    } catch {
      log.warn(`[${this.nombre}] Timeout esperando autenticacion`)
      await this.capturarPantalla('junta-sin-auth')
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
            organismo: celdas[1]?.textContent?.trim() || 'Junta de Andalucia',
            fechaTexto: celdas[2]?.textContent?.trim() ?? '',
            estado: celdas[3]?.textContent?.trim() ?? 'Pendiente',
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
        idExterno: this.generarIdExterno(datos.enlace || `junta-${i}`),
        portal: this.portal,
        tipo: 'Aviso',
        titulo: datos.titulo,
        organismo: datos.organismo,
        fechaDisposicion: this.normalizarFecha(datos.fechaTexto),
        fechaCaducidad: null,
        estado: datos.estado,
        rutaPdfLocal: null,
      })
    }

    log.info(`[${this.nombre}] ${resultado.length} avisos extraidos`)
    return resultado
  }
}
