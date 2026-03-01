import log from 'electron-log'
import { BaseScraperDocumental } from '../base-scraper-documental'
import type { ResultadoScraping } from '../../tipos'

/**
 * Scraper para consultar deudas pendientes con Hacienda.
 *
 * Flujo (mapeado desde analisis Findiur):
 * 1. Navegar a AEAT ConsultaDdas con faccion=CONS_DDAS
 * 2. Auth SSL/TLS directo (select-client-certificate)
 * 3. Se carga pagina con la consulta de deudas
 * 4. printToPDF de la pagina de resultado
 *
 * Diferencia con DEUDAS_AEAT: aquel obtiene certificado de estar al corriente,
 * este consulta deudas pendientes concretas (importes, expedientes).
 *
 * Auth: SSL/TLS directo (como DatosFiscales, IAE)
 * Metodo: printToPDF
 */
export class ScraperDeudasHacienda extends BaseScraperDocumental {
  private readonly url =
    'https://www1.agenciatributaria.gob.es/wlpl/SRVO-JDIT/ConsultaDdas?faccion=CONS_DDAS'

  get nombre(): string {
    return 'Deudas Hacienda'
  }

  async ejecutar(): Promise<ResultadoScraping> {
    log.info(`[${this.nombre}] Iniciando consulta de deudas con Hacienda`)

    // Paso 1: Navegar a la pagina de consulta de deudas
    await this.navegar(this.url)
    await this.delay(5000)

    const urlPostAuth = this.obtenerURL()
    log.info(`[${this.nombre}] URL post-auth: ${urlPostAuth}`)

    // Paso 2: Verificar que la pagina cargo correctamente
    const tieneDatos = await this.ejecutarJs<boolean>(`
      (function() {
        var body = document.body.innerText || '';
        // La pagina muestra datos de deudas o un mensaje de sin deudas
        return body.length > 100;
      })()
    `)

    if (!tieneDatos) {
      log.warn(`[${this.nombre}] Pagina sin contenido — posible error de auth`)
      await this.capturarPantalla('01-sin-datos')
    } else {
      log.info(`[${this.nombre}] Datos de deudas cargados`)
    }

    await this.capturarPantalla('02-resultado')

    // Paso 3: Generar PDF de la pagina de consulta
    const nombreArchivo = this.nombreConFecha('Deudas_Hacienda')
    const rutaPdf = await this.printToPdf(nombreArchivo)

    log.info(`[${this.nombre}] PDF generado: ${rutaPdf}`)

    return {
      exito: true,
      rutaDescarga: rutaPdf,
      datos: { rutasArchivos: [rutaPdf] },
    }
  }
}
