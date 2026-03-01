import log from 'electron-log'
import { BaseScraperDocumental } from '../base-scraper-documental'
import type { ResultadoScraping } from '../../tipos'

/**
 * Scraper para descargar el certificado integrado de prestaciones del INSS.
 *
 * Flujo (mapeado en Chrome 2026-02):
 * 1. Navegar a TUSS (sede-tu.seg-social.gob.es) → CertificadoIntegradoPrestaciones
 * 2. Si aparece pasarela idp.seg-social.es → login IPCE certificado
 * 3. Pagina muestra lista de tipos de certificado como enlaces directos PDF
 * 4. Click en enlace con tipoCertificado!certIntegradoPrestaciones → will-download
 *
 * La pagina TUSS muestra 9 tipos de certificado, todos como enlaces directos:
 * - certImporteCobroResumen1001
 * - certImporteCobroDesglosado1002
 * - noPensionista1003
 * - certPensionesBajaSuspendidas1004
 * - certBeneDeducciones1005
 * - certSinImportes1006
 * - certRevalorizacion
 * - certIntegradoPrestaciones (el que descargamos por defecto)
 *
 * Auth: SS IPCE (pasarela idp.seg-social.es)
 */
export class ScraperCertificadoINSS extends BaseScraperDocumental {
  private readonly url =
    'https://sede-tu.seg-social.gob.es/wps/myportal/tussR/tuss/TrabajoPensiones/Pensiones/CertificadoIntegradoPrestaciones'

  get nombre(): string {
    return 'Certificado INSS'
  }

  async ejecutar(): Promise<ResultadoScraping> {
    log.info(`[${this.nombre}] Iniciando descarga de certificado INSS`)

    // Paso 1: Navegar a TUSS
    await this.navegar(this.url)
    await this.delay(5000)

    // Paso 2: Manejar login si aparece pasarela SS
    const urlActual = this.obtenerURL()
    log.info(`[${this.nombre}] URL tras navegar: ${urlActual}`)

    if (urlActual.includes('idp.seg-social') || urlActual.includes('PGIS/Login')) {
      log.info(`[${this.nombre}] Pasarela SS detectada — haciendo login IPCE`)
      await this.loginPasarelaSS()
      await this.delay(5000)
    } else if (urlActual.includes('clave.gob.es') || urlActual.includes('pasarela')) {
      await this.manejarPasarelaClave()
      await this.delay(5000)
    }

    // Esperar redireccion post-login
    const urlPostLogin = this.obtenerURL()
    log.info(`[${this.nombre}] URL post-login: ${urlPostLogin}`)

    // Si seguimos en pasarela, esperar redireccion
    if (urlPostLogin.includes('idp.seg-social') || urlPostLogin.includes('ipce.seg-social')) {
      log.info(`[${this.nombre}] Aun en pasarela — esperando redireccion...`)
      const inicio = Date.now()
      while (Date.now() - inicio < 20_000) {
        await this.delay(1000)
        const url = this.obtenerURL()
        if (!url.includes('idp.seg-social') && !url.includes('ipce.seg-social')) {
          log.info(`[${this.nombre}] Redireccion completada: ${url}`)
          break
        }
      }
      await this.delay(3000)
    }

    await this.capturarPantalla('01-post-login')

    // Paso 3: Esperar a que cargue la pagina de certificados TUSS
    // La pagina muestra enlaces directos con aria-label "Se va a descargar un fichero de formato PDF"
    try {
      await this.esperarSelector("a[href*='tipoCertificado']", 20_000)
      log.info(`[${this.nombre}] Enlaces de certificados encontrados`)
    } catch {
      log.warn(`[${this.nombre}] Enlaces tipoCertificado no encontrados — intentando alternativas`)
    }

    await this.capturarPantalla('02-pre-descarga')

    // Paso 4: Descargar el certificado integrado de prestaciones
    const nombreArchivo = this.nombreConFecha('Certificado_INSS')

    // Estrategia 1: enlace con certIntegradoPrestaciones (interfaz TUSS 2026)
    try {
      const tieneEnlace = await this.ejecutarJs<boolean>(`
        !!document.querySelector("a[href*='certIntegradoPrestaciones']")
      `)
      if (tieneEnlace) {
        log.info(`[${this.nombre}] Enlace certIntegradoPrestaciones encontrado`)
        const ruta = await this.descargarConPromesa(
          () => this.clickElemento("a[href*='certIntegradoPrestaciones']"),
          nombreArchivo,
          30_000,
        )
        log.info(`[${this.nombre}] Certificado descargado: ${ruta}`)
        return { exito: true, rutaDescarga: ruta, datos: { rutasArchivos: [ruta] } }
      }
    } catch (err) {
      log.warn(`[${this.nombre}] Descarga certIntegrado fallo: ${(err as Error).message}`)
    }

    // Estrategia 2: enlace con certIntegrado (variante nombre)
    try {
      const tieneEnlace2 = await this.ejecutarJs<boolean>(`
        !!document.querySelector("a[href*='certIntegrado']")
      `)
      if (tieneEnlace2) {
        const ruta = await this.descargarConPromesa(
          () => this.clickElemento("a[href*='certIntegrado']"),
          nombreArchivo,
          30_000,
        )
        log.info(`[${this.nombre}] Certificado descargado via certIntegrado: ${ruta}`)
        return { exito: true, rutaDescarga: ruta, datos: { rutasArchivos: [ruta] } }
      }
    } catch {
      log.warn(`[${this.nombre}] certIntegrado no encontrado`)
    }

    // Estrategia 3: buscar enlace PDF por aria-label
    try {
      const tieneEnlacePdf = await this.ejecutarJs<boolean>(`
        (function() {
          var enlaces = document.querySelectorAll('a[aria-label*="PDF"], a[aria-label*="pdf"]');
          return enlaces.length > 0;
        })()
      `)
      if (tieneEnlacePdf) {
        // Tomar el ultimo enlace PDF (suele ser el integrado)
        const ruta = await this.descargarConPromesa(
          () => this.ejecutarJs<void>(`
            (function() {
              var enlaces = document.querySelectorAll('a[aria-label*="PDF"], a[aria-label*="pdf"]');
              if (enlaces.length > 0) enlaces[enlaces.length - 1].click();
            })()
          `),
          nombreArchivo,
          30_000,
        )
        log.info(`[${this.nombre}] Certificado descargado via aria-label PDF: ${ruta}`)
        return { exito: true, rutaDescarga: ruta, datos: { rutasArchivos: [ruta] } }
      }
    } catch {
      log.warn(`[${this.nombre}] Enlace por aria-label no encontrado`)
    }

    // Estrategia 4: patron Findiur original — .quotation__box3__list
    try {
      const tieneBoxList = await this.ejecutarJs<boolean>(`
        !!document.querySelector('.quotation__box3__list a')
      `)
      if (tieneBoxList) {
        const ruta = await this.descargarConPromesa(
          () => this.clickElemento('.quotation__box3__list a'),
          nombreArchivo,
          30_000,
        )
        log.info(`[${this.nombre}] Certificado descargado via .quotation__box3__list: ${ruta}`)
        return { exito: true, rutaDescarga: ruta, datos: { rutasArchivos: [ruta] } }
      }
    } catch {
      log.warn(`[${this.nombre}] .quotation__box3__list no encontrado`)
    }

    // Fallback: printToPdf
    log.warn(`[${this.nombre}] Usando printToPdf como ultimo recurso`)
    await this.capturarPantalla('fallback-printToPdf')
    const rutaPdf = await this.printToPdf(nombreArchivo)
    return { exito: true, rutaDescarga: rutaPdf, datos: { rutasArchivos: [rutaPdf] } }
  }

  /** Login en la pasarela SS (idp.seg-social.es/PGIS/Login) */
  private async loginPasarelaSS(): Promise<void> {
    // Boton "DNIe o certificado" con ID fijo #IPCEIdP (interfaz 2026)
    try {
      await this.esperarSelector('#IPCEIdP', 10_000)
      await this.clickElemento('#IPCEIdP')
      log.info(`[${this.nombre}] Click en #IPCEIdP`)
      return
    } catch {
      log.warn(`[${this.nombre}] #IPCEIdP no encontrado`)
    }

    // Fallback: buscar por formaction con IPCE
    try {
      await this.esperarSelector("button[formaction*='IPCE']", 5_000)
      await this.clickElemento("button[formaction*='IPCE']")
      log.info(`[${this.nombre}] Click en button[formaction*='IPCE']`)
      return
    } catch {
      log.warn(`[${this.nombre}] button[formaction*='IPCE'] no encontrado`)
    }

    // Fallback: buscar por texto
    await this.ejecutarJs<void>(`
      (function() {
        var btns = document.querySelectorAll('button');
        for (var i = 0; i < btns.length; i++) {
          var t = (btns[i].textContent || '').toLowerCase();
          if (t.includes('dnie') || t.includes('certificado')) {
            btns[i].click(); return;
          }
        }
      })()
    `)
    log.info(`[${this.nombre}] Fallback — click por texto certificado/dnie`)
  }
}
