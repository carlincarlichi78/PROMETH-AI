import log from 'electron-log'
import { BaseScraperDocumental } from '../base-scraper-documental'
import type { ResultadoScraping } from '../../tipos'

/**
 * Scraper para obtener certificado de deudas con la AEAT.
 *
 * Flujo Findiur (patron correcto):
 * 1. Navegar al formulario → seleccionar tipo → validar solicitud
 * 2. Click firmar → popup de firma (Conforme + Firmar)
 * 3. Configurar setWindowOpenHandler ANTES de firmar para interceptar popup PDF
 * 4. Tras firmar → AEAT intenta abrir popup con PDF → interceptado → downloadURL → will-download
 *
 * Auth: SSL/TLS directo a www1.agenciatributaria.gob.es (sin Cl@ve)
 */
export class ScraperDeudasAeat extends BaseScraperDocumental {
  private readonly url =
    'https://www1.agenciatributaria.gob.es/wlpl/EMCE-JDIT/ECOTInternetCiudadanosServlet'

  get nombre(): string {
    return 'Deudas AEAT'
  }

  async ejecutar(): Promise<ResultadoScraping> {
    log.info(`[${this.nombre}] Iniciando solicitud de certificado de deudas`)

    // Paso 1: Navegar al formulario de solicitud
    await this.navegar(this.url)
    await this.delay(2000)

    // Paso 2: Seleccionar tipo "Certificado deudas"
    await this.esperarSelector('#fTipoCertificado4')
    await this.clickElemento('#fTipoCertificado4')
    log.info(`[${this.nombre}] Tipo de certificado seleccionado`)

    // Paso 3: Validar solicitud
    await this.clickElemento('#validarSolicitud')
    await this.delay(1000)
    log.info(`[${this.nombre}] Solicitud validada`)

    // Paso 4: Click firmar — preparar listener de popup ANTES del click
    await this.esperarSelector('.AEAT_boton')
    const waitPopupFirma = this.prepararEsperaVentana(30_000)
    await this.clickElemento('.AEAT_boton')

    // Paso 5: Esperar popup de firma y firmar
    const popupFirma = await waitPopupFirma
    log.info(`[${this.nombre}] Popup de firma abierto (id: ${popupFirma.id})`)

    await this.esperarSelectorEnVentana(popupFirma, '#Conforme')
    await this.clickElementoEnVentana(popupFirma, '#Conforme')
    await this.delay(1000)

    // Paso 6: Configurar interceptor de descarga ANTES de firmar
    // Patron Findiur: setWindowOpenHandler intercepta el popup del PDF
    // y lo convierte en descarga via downloadURL → will-download
    const nombreArchivo = this.nombreConFecha('Deudas_AEAT')
    const esperaDescarga = this.configurarInterceptorDescarga(nombreArchivo, 60_000)

    // Firmar — esto dispara que AEAT abra un popup con el PDF
    await this.clickElementoEnVentana(popupFirma, '#Firmar')
    log.info(`[${this.nombre}] Firma enviada — esperando descarga PDF via interceptor...`)

    // Paso 7: Esperar descarga del PDF real
    try {
      const ruta = await esperaDescarga
      log.info(`[${this.nombre}] Certificado descargado: ${ruta}`)
      return { exito: true, rutaDescarga: ruta, datos: { rutasArchivos: [ruta] } }
    } catch (errInterceptor) {
      log.warn(
        `[${this.nombre}] Interceptor no capturo descarga: ${(errInterceptor as Error).message}`,
      )
    }

    // Fallback: buscar enlace #descarga en ventana principal
    await this.delay(3000)
    try {
      await this.esperarSelector('#descarga', 10_000)
      log.info(`[${this.nombre}] Enlace #descarga encontrado — descargando`)
      const ruta = await this.descargarConPromesa(
        () => this.clickElemento('#descarga'),
        nombreArchivo,
        30_000,
      )
      return { exito: true, rutaDescarga: ruta, datos: { rutasArchivos: [ruta] } }
    } catch {
      log.warn(`[${this.nombre}] #descarga no encontrado`)
    }

    // Fallback final: printToPdf (ultimo recurso, PDF de menor calidad)
    log.warn(`[${this.nombre}] Usando printToPdf como ultimo recurso`)
    await this.capturarPantalla('fallback-printToPdf')
    const rutaPdf = await this.printToPdf(nombreArchivo)
    return { exito: true, rutaDescarga: rutaPdf, datos: { rutasArchivos: [rutaPdf] } }
  }
}
