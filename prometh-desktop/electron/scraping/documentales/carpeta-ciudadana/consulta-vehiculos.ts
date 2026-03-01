import log from 'electron-log'
import { BaseScraperDocumental } from '../base-scraper-documental'
import type { ResultadoScraping } from '../../tipos'
import { loginCarpetaCiudadana } from './login-carpeta'

/**
 * Scraper para consultar vehiculos desde Carpeta Ciudadana y DGT.
 * Genera 2 PDFs: uno de Carpeta Ciudadana y otro de la sede de la DGT.
 * Metodo: PRINT_TO_PDF (no hay descarga directa).
 */
export class ScraperConsultaVehiculos extends BaseScraperDocumental {
  private readonly urlInicio = 'https://carpetaciudadana.gob.es'
  private readonly urlVehiculos =
    'https://carpetaciudadana.gob.es/carpeta/datos/vehiculos/consulta.htm?idioma=es'
  private readonly urlDgt =
    'https://sede.dgt.gob.es/es/mi_dgt/mis-vehiculos/'

  get nombre(): string {
    return 'Consulta Vehiculos'
  }

  async ejecutar(): Promise<ResultadoScraping> {
    log.info(`[${this.nombre}] Iniciando consulta de vehiculos`)

    // Paso 1: Login en Carpeta Ciudadana
    await this.navegar(this.urlInicio)
    await loginCarpetaCiudadana(this)

    // Paso 2: Navegar a consulta de vehiculos en Carpeta Ciudadana
    await this.navegar(this.urlVehiculos)

    // Esperar contenido real (no solo app-root que esta en la home tambien)
    await this.esperarContenidoReal(30_000)
    log.info(`[${this.nombre}] Pagina de vehiculos (Carpeta) cargada`)

    // Paso 3: Generar PDF de Carpeta Ciudadana
    const nombreCarpeta = this.nombreConFecha('Consulta_Vehiculos_CarpetaCiudadana')
    const rutaCarpeta = await this.printToPdf(nombreCarpeta)
    log.info(`[${this.nombre}] PDF Carpeta Ciudadana: ${rutaCarpeta}`)

    // Paso 4: Navegar a sede DGT
    await this.navegar(this.urlDgt)
    // DGT: esperar contenido especifico
    await this.delay(5000)
    const urlDgt = await this.obtenerURL()
    log.info(`[${this.nombre}] URL DGT: ${urlDgt}`)

    // Si redirige a login, intentar con certificado
    if (urlDgt.includes('clave.gob.es') || urlDgt.includes('pasarela')) {
      await this.manejarPasarelaClave()
      await this.delay(5000)
    }

    log.info(`[${this.nombre}] Pagina de vehiculos (DGT) cargada`)

    // Paso 5: Generar PDF de DGT
    const nombreDgt = this.nombreConFecha('Consulta_Vehiculos_DGT')
    const rutaDgt = await this.printToPdf(nombreDgt)
    log.info(`[${this.nombre}] PDF DGT: ${rutaDgt}`)

    return {
      exito: true,
      rutaDescarga: rutaCarpeta,
      datos: { rutasArchivos: [rutaCarpeta, rutaDgt] },
    }
  }

  /** Espera que la pagina tenga contenido real, no la home generica */
  private async esperarContenidoReal(timeout: number): Promise<void> {
    const inicio = Date.now()
    while (Date.now() - inicio < timeout) {
      const url = await this.obtenerURL()
      // Si estamos en la URL correcta
      if (url.includes('vehiculos') || url.includes('datos')) {
        // Verificar que tiene contenido de vehiculos (tabla, datos, etc.)
        const tieneContenido = await this.ejecutarJs(`
          !!(document.querySelector('table') ||
             document.querySelector('.datos-vehiculo') ||
             document.querySelector('.vehicle') ||
             document.querySelector('[class*="vehiculo"]') ||
             document.querySelector('.mat-table') ||
             (document.body.innerText && document.body.innerText.length > 500))
        `)
        if (tieneContenido) return
      }
      // Si nos redirigieron a la home
      if (url === 'https://carpetaciudadana.gob.es/' || url.includes('/public')) {
        log.warn(`[${this.nombre}] Redirigido a home — reintentando navegacion`)
        await this.navegar(this.urlVehiculos)
        await this.delay(3000)
      }
      await this.delay(1000)
    }
    // Si el timeout expira, imprimir de todas formas
    log.warn(`[${this.nombre}] Timeout esperando contenido real — imprimiendo lo disponible`)
  }
}
