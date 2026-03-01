import log from 'electron-log'
import { BaseScraperDocumental } from '../base-scraper-documental'
import type { ResultadoScraping } from '../../tipos'
import { loginSeguridadSocial } from './login-ss'

/**
 * Scraper para descargar el informe de vida laboral desde la Seguridad Social.
 *
 * Flujo Findiur (patron correcto):
 * 1. Navegar a importass → pagina vida laboral
 * 2. Cerrar cookies con AceptarCookies()
 * 3. Click en clickBotonConsultar() (funcion JS del portal)
 * 4. Login SS via IPCE (certificado electronico)
 * 5. Click en button[value='AC_DESC_VIDA_LABORAL'] → will-download
 *
 * Auth: SS IPCE
 */
export class ScraperVidaLaboral extends BaseScraperDocumental {
  private readonly url =
    'https://portal.seg-social.gob.es/wps/portal/importass/importass/Categorias/Vida+laboral+e+informes/Informes+sobre+tu+situacion+laboral/Informe+de+tu+vida+laboral'

  get nombre(): string {
    return 'Vida Laboral'
  }

  async ejecutar(): Promise<ResultadoScraping> {
    log.info(`[${this.nombre}] Iniciando descarga de vida laboral`)

    // Paso 1: Navegar al portal de vida laboral
    await this.navegar(this.url)
    await this.delay(3000)

    // Paso 2: Cerrar cookies (patron Findiur: llamar AceptarCookies() del portal)
    await this.ejecutarJs<void>(`
      (function() {
        if (typeof AceptarCookies === 'function') { AceptarCookies(); return; }
        var btn = document.querySelector('#cookies button, #onetrust-accept-btn-handler');
        if (btn) btn.click();
        var botones = document.querySelectorAll('button');
        for (var i = 0; i < botones.length; i++) {
          var t = (botones[i].textContent || '').toLowerCase();
          if (t.includes('rechazar todas') || t.includes('aceptar todas')) {
            botones[i].click(); return;
          }
        }
      })()
    `).catch(() => { /* cookies puede no existir */ })
    await this.delay(1500)

    // Paso 3: Click en "Consultar vida laboral" (patron Findiur: clickBotonConsultar())
    await this.ejecutarJs<void>(`
      (function() {
        if (typeof clickBotonConsultar === 'function') { clickBotonConsultar(); return; }
        var botones = document.querySelectorAll('button, a');
        for (var i = 0; i < botones.length; i++) {
          var t = (botones[i].textContent || '').toLowerCase();
          if (t.includes('consultar vida laboral') || t.includes('acceder al servicio') ||
              t.includes('obtener informe')) {
            botones[i].click(); return;
          }
        }
      })()
    `).catch(() => { /* puede no existir */ })
    await this.delay(3000)

    // Paso 4: Login con certificado electronico via pasarela SS
    await loginSeguridadSocial(this)
    await this.delay(5000)

    const urlPostLogin = this.obtenerURL()
    log.info(`[${this.nombre}] URL post-login: ${urlPostLogin}`)

    // Paso 5: Buscar boton de descarga especifico de Findiur
    const nombreArchivo = this.nombreConFecha('Vida_Laboral')

    // Intentar selector exacto Findiur: button[value='AC_DESC_VIDA_LABORAL']
    const tieneBotonDescarga = await this.ejecutarJs<boolean>(`
      !!(document.querySelector("button[value='AC_DESC_VIDA_LABORAL']") ||
         document.querySelector("button[name='AC_DESC_VIDA_LABORAL']") ||
         document.querySelector("input[value='AC_DESC_VIDA_LABORAL']"))
    `)

    if (tieneBotonDescarga) {
      log.info(`[${this.nombre}] Boton AC_DESC_VIDA_LABORAL encontrado — descargando`)
      try {
        const ruta = await this.descargarConPromesa(
          () => this.clickElemento(
            "button[value='AC_DESC_VIDA_LABORAL'], button[name='AC_DESC_VIDA_LABORAL'], input[value='AC_DESC_VIDA_LABORAL']",
          ),
          nombreArchivo,
          30_000,
        )
        log.info(`[${this.nombre}] Informe descargado: ${ruta}`)
        return { exito: true, rutaDescarga: ruta, datos: { rutasArchivos: [ruta] } }
      } catch (err) {
        log.warn(`[${this.nombre}] will-download fallo con boton especifico: ${(err as Error).message}`)
      }
    }

    // Buscar cualquier boton de descarga por texto
    const selectorDescarga = await this.buscarBotonDescarga()
    if (selectorDescarga) {
      log.info(`[${this.nombre}] Boton descarga generico: ${selectorDescarga}`)
      try {
        const ruta = await this.descargarConPromesa(
          () => this.clickElemento(selectorDescarga),
          nombreArchivo,
          30_000,
        )
        log.info(`[${this.nombre}] Informe descargado: ${ruta}`)
        return { exito: true, rutaDescarga: ruta, datos: { rutasArchivos: [ruta] } }
      } catch (err) {
        log.warn(`[${this.nombre}] will-download generico fallo: ${(err as Error).message}`)
      }
    }

    // Fallback: printToPdf (ultimo recurso)
    log.warn(`[${this.nombre}] Usando printToPdf como ultimo recurso`)
    await this.capturarPantalla('fallback-printToPdf')
    const rutaPdf = await this.printToPdf(nombreArchivo)
    return { exito: true, rutaDescarga: rutaPdf, datos: { rutasArchivos: [rutaPdf] } }
  }

  private async buscarBotonDescarga(): Promise<string | null> {
    const encontrado = await this.ejecutarJs<boolean>(`
      (function() {
        var elementos = document.querySelectorAll('button, a, input[type="submit"]');
        for (var i = 0; i < elementos.length; i++) {
          var t = (elementos[i].textContent || elementos[i].value || '').toLowerCase();
          if (t.includes('descargar') || t.includes('obtener informe') ||
              t.includes('generar informe') || t.includes('descargar pdf')) {
            elementos[i].setAttribute('data-cg-download', 'true');
            return true;
          }
        }
        return false;
      })()
    `)
    return encontrado ? '[data-cg-download="true"]' : null
  }
}
