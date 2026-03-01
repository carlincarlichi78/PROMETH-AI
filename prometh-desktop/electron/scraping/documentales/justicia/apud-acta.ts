import log from 'electron-log'
import { BaseScraperDocumental } from '../base-scraper-documental'
import type { ResultadoScraping, ConfigScraping } from '../../tipos'

/**
 * Scraper semi-automatico para Apoderamiento Apud Acta.
 * Portal: Sede Judicial Electronica (sedejudicial.justicia.es).
 *
 * Flujo mapeado con Chrome MCP (2026-02-21):
 * 1. Navegar a URL publica del servicio
 * 2. Aceptar cookies necesarias
 * 3. Click "ACCEDER AL SERVICIO" → redirige a pasarela Cl@ve
 * 4. Cl@ve → "Acceso DNIe / Certificado electronico" → select-client-certificate
 * 5. Redireccion automatica a Area Privada → seccion "Apoderamiento Apud Acta"
 * 6. Formulario de busqueda con: En calidad de, Estados, NIF, Identificador, Fechas
 * 7. Boton "NUEVO APODERAMIENTO" para crear nuevo (18 pasos, requiere datos manuales)
 *
 * NOTA: Es un servicio interactivo (crear/buscar apoderamientos), no un documento descargable.
 * El scraper navega hasta el area privada y deja la ventana abierta para intervencion manual.
 * Timeout global: 10 minutos.
 */
export class ScraperApudActa extends BaseScraperDocumental {
  private readonly url =
    'https://sedejudicial.justicia.es/-/apoderamiento-apud-acta'

  constructor(serialNumber: string, config?: Partial<ConfigScraping>) {
    super(serialNumber, {
      ...config,
      // Timeout extendido: 10 minutos para intervencion manual
      timeoutGlobal: 600_000,
    })
  }

  get nombre(): string {
    return 'Apud Acta'
  }

  async ejecutar(): Promise<ResultadoScraping> {
    log.info(`[${this.nombre}] Iniciando navegacion al portal de Apud Acta`)

    // Paso 1: Navegar al portal publico
    await this.navegar(this.url)
    await this.delay(2000)
    log.info(`[${this.nombre}] Portal cargado`)

    // Paso 2: Aceptar solo cookies necesarias
    // Selector real: button con texto "Aceptar solo cookies necesarias"
    const cookiesCerradas = await this.ejecutarJs<boolean>(`
      (function() {
        var botones = document.querySelectorAll('button');
        for (var i = 0; i < botones.length; i++) {
          var texto = (botones[i].textContent || '').trim();
          if (texto.includes('Aceptar solo cookies necesarias') || texto.includes('Aceptar todas')) {
            botones[i].click();
            return true;
          }
        }
        return false;
      })()
    `)
    if (cookiesCerradas) {
      log.info(`[${this.nombre}] Banner de cookies cerrado`)
      await this.delay(500)
    }

    // Paso 3: Click en "ACCEDER AL SERVICIO" con Cl@ve
    // Selector real: a[href*="sedjudeselectortipousuarioweb"][href*="Apud"]
    const accesoClave = await this.ejecutarJs<boolean>(`
      (function() {
        var enlace = document.querySelector('a[href*="sedjudeselectortipousuarioweb"]');
        if (enlace) { enlace.click(); return true; }
        // Fallback: buscar por texto
        var links = document.querySelectorAll('a');
        for (var i = 0; i < links.length; i++) {
          if ((links[i].textContent || '').includes('ACCEDER AL SERVICIO')) {
            links[i].click();
            return true;
          }
        }
        return false;
      })()
    `)

    if (!accesoClave) {
      throw new Error('Boton ACCEDER AL SERVICIO no encontrado')
    }
    log.info(`[${this.nombre}] Acceso Cl@ve iniciado, esperando pasarela...`)

    // Paso 4: Manejar pasarela Cl@ve → certificado electronico
    // La pasarela redirige a pasarela.clave.gob.es con 3 opciones
    // manejarPasarelaClave() usa selectedIdP('AFIRMA') o click en boton certificado
    await this.delay(3000)
    const loginOk = await this.manejarPasarelaClave(15_000, 30_000)
    if (!loginOk) {
      throw new Error('Autenticacion Cl@ve fallo en Sede Judicial')
    }
    log.info(`[${this.nombre}] Autenticacion Cl@ve completada`)

    // Paso 5: Esperar redireccion al Area Privada
    // URL post-login: sedejudicial.justicia.es/group/guest/apoderamiento-apud-acta
    await this.delay(3000)

    // Paso 6: Verificar que estamos en el Area Privada
    const enAreaPrivada = await this.ejecutarJs<boolean>(`
      (function() {
        var url = window.location.href;
        var tieneTitulo = !!document.querySelector('h1, .apud-acta-title, [class*="apudacta"]');
        var tieneFormulario = !!document.querySelector('select, [id*="apudacta"]');
        return url.includes('group/guest') || url.includes('area-privada') || tieneTitulo || tieneFormulario;
      })()
    `)

    if (!enAreaPrivada) {
      log.warn(`[${this.nombre}] No se confirmo Area Privada, puede requerir navegacion adicional`)
    } else {
      log.info(`[${this.nombre}] Area Privada de Sede Judicial cargada`)
    }

    // Paso 7: El servicio requiere intervencion manual
    // - "NUEVO APODERAMIENTO" para crear (18 pasos con datos del caso)
    // - "BUSCAR" para buscar existentes (selects: En calidad de, Estados)
    log.info(
      `[${this.nombre}] Apud Acta listo — ventana abierta para intervencion manual`,
    )

    return {
      exito: true,
      datos: {
        semiAutomatico: true,
        mensaje: 'Area Privada de Sede Judicial cargada. Formulario de Apud Acta disponible.',
      },
    }
  }
}
