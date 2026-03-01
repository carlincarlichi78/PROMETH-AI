import log from 'electron-log'
import { BaseScraperDocumental } from '../base-scraper-documental'
import type { ResultadoScraping } from '../../tipos'

/**
 * Scraper para obtener certificado de actividades IAE de la AEAT.
 *
 * Flujo (identico a DeudasAEAT/IRPF):
 * 1. Navegar al servlet directo → formulario auto-rellenado
 * 2. Seleccionar ejercicio fiscal → Validar solicitud
 * 3. Firmar Enviar → popup firma (#Conforme + #Firmar)
 * 4. setWindowOpenHandler intercepta popup PDF → will-download
 *
 * Auth: SSL/TLS directo a www1.agenciatributaria.gob.es (sin Cl@ve)
 */
export class ScraperIaeActividades extends BaseScraperDocumental {
  private readonly url =
    'https://www1.agenciatributaria.gob.es/wlpl/EMCE-JDIT/ServletAaeeGralnternet'

  get nombre(): string {
    return 'Actividades IAE'
  }

  async ejecutar(): Promise<ResultadoScraping> {
    log.info(`[${this.nombre}] Iniciando solicitud de certificado IAE`)

    // Paso 1: Navegar al formulario
    await this.navegar(this.url)
    await this.delay(2000)

    // Paso 2: Verificar que estamos en el formulario correcto
    await this.esperarSelector('#fEjercicio')
    log.info(`[${this.nombre}] Formulario IAE cargado`)

    // Seleccionar ejercicio fiscal actual
    // IAE usa el anio en curso (a diferencia de datos fiscales)
    const anioActual = String(new Date().getFullYear())
    await this.seleccionarOpcion('#fEjercicio', anioActual)
    await this.delay(500)

    // Paso 3: Validar solicitud
    await this.clickElemento('#validarSolicitud')
    log.info(`[${this.nombre}] Solicitud validada — esperando paso 2`)

    // Paso 4: Esperar boton "Firmar Enviar" (clase .AEAT_boton, input[value='Firmar Enviar'])
    await this.esperarSelector("input[value='Firmar Enviar']", 15_000)

    // Preparar popup de firma ANTES del click
    const waitPopupFirma = this.prepararEsperaVentana(30_000)
    await this.clickElemento("input[value='Firmar Enviar']")

    // Paso 5: Popup de firma
    const popupFirma = await waitPopupFirma
    log.info(`[${this.nombre}] Popup de firma abierto`)

    await this.esperarSelectorEnVentana(popupFirma, '#Conforme')
    await this.clickElementoEnVentana(popupFirma, '#Conforme')
    await this.delay(1000)

    // Paso 6: Configurar interceptor ANTES de firmar
    const nombreArchivo = this.nombreConFecha('Actividades_IAE')
    const esperaDescarga = this.configurarInterceptorDescarga(nombreArchivo, 60_000)

    await this.clickElementoEnVentana(popupFirma, '#Firmar')
    log.info(`[${this.nombre}] Firma enviada — esperando descarga PDF...`)

    // Paso 7: Esperar descarga via interceptor
    try {
      const ruta = await esperaDescarga
      log.info(`[${this.nombre}] Certificado IAE descargado: ${ruta}`)
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
      log.info(`[${this.nombre}] Enlace #descarga encontrado`)
      const ruta = await this.descargarConPromesa(
        () => this.clickElemento('#descarga'),
        nombreArchivo,
        30_000,
      )
      return { exito: true, rutaDescarga: ruta, datos: { rutasArchivos: [ruta] } }
    } catch {
      log.warn(`[${this.nombre}] #descarga no encontrado`)
    }

    // Fallback final: printToPdf
    log.warn(`[${this.nombre}] Usando printToPdf como ultimo recurso`)
    await this.capturarPantalla('fallback-printToPdf')
    const rutaPdf = await this.printToPdf(nombreArchivo)
    return { exito: true, rutaDescarga: rutaPdf, datos: { rutasArchivos: [rutaPdf] } }
  }
}
