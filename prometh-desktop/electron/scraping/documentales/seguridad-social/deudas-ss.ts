import log from 'electron-log'
import { BaseScraperDocumental } from '../base-scraper-documental'
import type { ResultadoScraping, ConfigScraping } from '../../tipos'
import { loginSeguridadSocial } from './login-ss'

/** Datos extra opcionales para DeudasSS */
interface DatosExtraDeudasSS {
  /** Tipo de certificado SS (1=Generico, 2-7 especificos). Default: '1' */
  tipoCertificado?: string
}

/**
 * Scraper para obtener certificado de deudas con la Seguridad Social.
 *
 * Flujo mapeado (Chrome MCP 2026-02-21):
 * 1. Navegar a URL ProsaInternet → redirige a idp.seg-social.es/PGIS/Login
 * 2. Login SS via IPCE (certificado digital)
 * 3. Formulario: radio input[name="certificado"][value="1"] "Generico" (pre-seleccionado)
 *    → click "Continuar" (button[type="submit"] name="SPM.ACC.CONTINUAR")
 * 4. Confirmacion "Seleccion de certificado": 7 tipos listados
 *    → click "Imprimir" (button#ENVIO_10[name="SPM.ACC.IMPRIMIR"] class="pr_btnGeneral")
 * 5. Resultado: "El documento se ha generado correctamente."
 *    → enlace a.pr_enlaceDocumento target="_blank" href="/ProsaInternet/ViewDoc..."
 *    → click dispara window.open → setWindowOpenHandler → downloadURL → will-download PDF
 *
 * Auth: SS IPCE (pasarela idp.seg-social.es, no Cl@ve)
 * Nota: El tipo de certificado se puede parametrizar via datosExtra.tipoCertificado (1-7)
 */
export class ScraperDeudasSS extends BaseScraperDocumental {
  private readonly url =
    'https://sp.seg-social.es/ProsaInternet/OnlineAccess?ARQ.SPM.ACTION=LOGIN&ARQ.SPM.APPTYPE=SERVICE&ARQ.IDAPP=AECPSED1&PAUC.NIVEL=1&PAUC.TIPO_IDENTIFICACION=2'

  private readonly datosExtra: DatosExtraDeudasSS

  constructor(
    serialNumber: string,
    config?: Partial<ConfigScraping>,
    datosExtra?: DatosExtraDeudasSS,
  ) {
    super(serialNumber, config)
    this.datosExtra = datosExtra ?? {}
  }

  get nombre(): string {
    return 'Deudas SS'
  }

  async ejecutar(): Promise<ResultadoScraping> {
    log.info(`[${this.nombre}] Iniciando consulta de deudas SS`)

    // Paso 1: Navegar — redirige a pasarela SS
    await this.navegar(this.url)
    await this.delay(3000)

    // Paso 2: Login con certificado electronico
    const urlActual = this.obtenerURL()
    log.info(`[${this.nombre}] URL tras navegar: ${urlActual}`)

    if (
      urlActual.includes('idp.seg-social') ||
      urlActual.includes('PGIS/Login') ||
      urlActual.includes('importass')
    ) {
      await loginSeguridadSocial(this)
      await this.delay(5000)
    } else if (urlActual.includes('clave.gob.es')) {
      await this.manejarPasarelaClave()
      await this.delay(5000)
    }

    await this.capturarPantalla('paso-2-post-login')

    // Verificar que estamos en ProsaInternet
    const urlPostLogin = this.obtenerURL()
    log.info(`[${this.nombre}] URL post-login: ${urlPostLogin}`)

    if (!urlPostLogin.includes('ProsaInternet') && !urlPostLogin.includes('sp.seg-social')) {
      await this.navegar(this.url)
      await this.delay(5000)
    }

    // Paso 3: Formulario — radio "Generico" ya seleccionado → click "Continuar"
    // El tipo de certificado se puede cambiar via datosExtra.tipoCertificado
    const tipoCert = this.datosExtra.tipoCertificado ?? '1'
    if (tipoCert !== '1') {
      log.info(`[${this.nombre}] Seleccionando tipo certificado: ${tipoCert}`)
      await this.ejecutarJs<void>(`
        (function() {
          var radio = document.querySelector('input[name="certificado"][value="${tipoCert}"]');
          if (radio) radio.click();
        })()
      `)
      await this.delay(500)
    }

    // Click "Continuar"
    const clicContinuar = await this.ejecutarJs<boolean>(`
      (function() {
        // Selector exacto: button[name="SPM.ACC.CONTINUAR"]
        var btn = document.querySelector('button[name="SPM.ACC.CONTINUAR"]');
        if (btn) { btn.click(); return true; }
        // Fallback: cualquier submit con texto "continuar"
        var btns = document.querySelectorAll('button[type="submit"], input[type="submit"]');
        for (var i = 0; i < btns.length; i++) {
          var t = (btns[i].textContent || btns[i].value || '').toLowerCase();
          if (t.includes('continuar')) { btns[i].click(); return true; }
        }
        return false;
      })()
    `)

    if (clicContinuar) {
      log.info(`[${this.nombre}] Click en Continuar`)
      await this.delay(3000)
    } else {
      log.warn(`[${this.nombre}] Boton Continuar no encontrado — puede que ya paso al paso 4`)
    }

    await this.capturarPantalla('paso-3-post-continuar')

    // Paso 4: Confirmacion — click "Imprimir"
    // Selector: button#ENVIO_10[name="SPM.ACC.IMPRIMIR"] class="pr_btnGeneral"
    const clicImprimir = await this.ejecutarJs<boolean>(`
      (function() {
        // Selector exacto por name
        var btn = document.querySelector('button[name="SPM.ACC.IMPRIMIR"]');
        if (btn) { btn.click(); return true; }
        // Fallback por id
        btn = document.getElementById('ENVIO_10');
        if (btn) { btn.click(); return true; }
        // Fallback por texto
        var btns = document.querySelectorAll('button[type="submit"], input[type="submit"]');
        for (var i = 0; i < btns.length; i++) {
          var t = (btns[i].textContent || btns[i].value || '').toLowerCase();
          if (t.includes('imprimir')) { btns[i].click(); return true; }
        }
        return false;
      })()
    `)

    if (clicImprimir) {
      log.info(`[${this.nombre}] Click en Imprimir`)
      await this.delay(5000)
    } else {
      log.warn(`[${this.nombre}] Boton Imprimir no encontrado`)
      await this.capturarPantalla('error-sin-imprimir')
    }

    await this.capturarPantalla('paso-4-post-imprimir')

    // Paso 5: Resultado — descargar PDF via enlace a.pr_enlaceDocumento (target="_blank")
    // El enlace abre en ventana nueva → necesita setWindowOpenHandler → downloadURL → will-download
    const nombreArchivo = this.nombreConFecha('Deudas_SS')

    // Estrategia 1: configurarInterceptorDescarga + click enlace (maneja target="_blank")
    try {
      await this.esperarSelector('a.pr_enlaceDocumento', 15_000)
      log.info(`[${this.nombre}] Enlace a.pr_enlaceDocumento encontrado`)

      const promesaDescarga = this.configurarInterceptorDescarga(nombreArchivo, 30_000)
      await this.clickElemento('a.pr_enlaceDocumento')
      log.info(`[${this.nombre}] Click en enlace documento — esperando descarga via interceptor`)

      const ruta = await promesaDescarga
      log.info(`[${this.nombre}] Certificado descargado: ${ruta}`)
      return { exito: true, rutaDescarga: ruta, datos: { rutasArchivos: [ruta] } }
    } catch (err) {
      log.warn(`[${this.nombre}] Estrategia 1 fallo: ${(err as Error).message}`)
    }

    // Estrategia 2: enlace ViewDoc con descargarConPromesa (quitar target)
    try {
      const tieneViewDoc = await this.ejecutarJs<boolean>(`
        (function() {
          var link = document.querySelector("a[href*='ViewDoc']");
          if (link) { link.removeAttribute('target'); return true; }
          return false;
        })()
      `)

      if (tieneViewDoc) {
        const ruta = await this.descargarConPromesa(
          () => this.clickElemento("a[href*='ViewDoc']"),
          nombreArchivo,
          30_000,
        )
        log.info(`[${this.nombre}] Certificado descargado via ViewDoc: ${ruta}`)
        return { exito: true, rutaDescarga: ruta, datos: { rutasArchivos: [ruta] } }
      }
    } catch (err) {
      log.warn(`[${this.nombre}] Estrategia 2 fallo: ${(err as Error).message}`)
    }

    // Estrategia 3: buscar enlace con texto "certificado" y usar downloadURL
    try {
      const hrefEnlace = await this.ejecutarJs<string>(`
        (function() {
          var enlaces = document.querySelectorAll('a');
          for (var i = 0; i < enlaces.length; i++) {
            var t = (enlaces[i].textContent || '').toLowerCase();
            if (t.includes('certificado') && !t.includes('informaci')) {
              return enlaces[i].href;
            }
          }
          return '';
        })()
      `)

      if (hrefEnlace) {
        const promesaDescarga = this.configurarInterceptorDescarga(nombreArchivo, 30_000)
        this.window!.webContents.downloadURL(hrefEnlace)
        const ruta = await promesaDescarga
        log.info(`[${this.nombre}] Certificado descargado via downloadURL directo: ${ruta}`)
        return { exito: true, rutaDescarga: ruta, datos: { rutasArchivos: [ruta] } }
      }
    } catch (err) {
      log.warn(`[${this.nombre}] Estrategia 3 fallo: ${(err as Error).message}`)
    }

    // Fallback final: printToPdf
    log.warn(`[${this.nombre}] Usando printToPdf como ultimo recurso`)
    await this.capturarPantalla('fallback-printToPdf')
    const rutaPdf = await this.printToPdf(nombreArchivo)
    return { exito: true, rutaDescarga: rutaPdf, datos: { rutasArchivos: [rutaPdf] } }
  }
}
