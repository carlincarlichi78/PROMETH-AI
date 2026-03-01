import { join } from 'path'
import log from 'electron-log'
import { BaseScraperDocumental } from '../base-scraper-documental'
import type { ResultadoScraping } from '../../tipos'

/**
 * Scraper para obtener certificado literal de nacimiento.
 *
 * Flujo (mapeado en Chrome 2026-02):
 * 1. Navegar a sede.mjusticia.gob.es SERECI con idMateria=NAC
 * 2. Redirige a pasarela Cl@ve → click "DNIe / Certificado electronico"
 *    (selectedIdP('AFIRMA') + idpRedirect.submit())
 * 3. Auth certificado → redirige de vuelta a sede.mjusticia.gob.es
 * 4. Descarga AUTOMATICA del PDF (will-download se dispara solo post-login)
 * 5. Fallback: pagina muestra "Descargar Certificado" (button submit) por si no descargo
 *
 * Auth: Cl@ve (pasarela.clave.gob.es) → DNIe/certificado electronico
 */
export class ScraperCertificadoNacimiento extends BaseScraperDocumental {
  private readonly url =
    'https://sede.mjusticia.gob.es/sereci/clave/solicitarCertificadoSolicitudLiteral?idMateria=NAC'

  get nombre(): string {
    return 'Certificado Nacimiento'
  }

  async ejecutar(): Promise<ResultadoScraping> {
    log.info(`[${this.nombre}] Iniciando descarga de certificado de nacimiento`)

    const nombreArchivo = this.nombreConFecha('Certificado_Nacimiento')

    // Configurar will-download ANTES de navegar (descarga automatica post-login)
    const esperaDescarga = this.configurarDescargaEnSesion(nombreArchivo, 60_000)

    // Paso 1: Navegar al formulario SERECI
    await this.navegar(this.url)
    await this.delay(3000)

    // Paso 2: Manejar pasarela Cl@ve
    const urlActual = this.obtenerURL()
    log.info(`[${this.nombre}] URL tras navegar: ${urlActual}`)

    if (urlActual.includes('clave.gob.es') || urlActual.includes('pasarela')) {
      log.info(`[${this.nombre}] Pasarela Cl@ve detectada`)
      await this.manejarPasarelaClave(15_000, 30_000)
      await this.delay(5000)
    }

    // Esperar redireccion post-login a sede.mjusticia.gob.es
    const urlPostLogin = this.obtenerURL()
    log.info(`[${this.nombre}] URL post-login: ${urlPostLogin}`)

    if (urlPostLogin.includes('clave.gob.es')) {
      log.info(`[${this.nombre}] Aun en Cl@ve — esperando redireccion...`)
      const inicio = Date.now()
      while (Date.now() - inicio < 20_000) {
        await this.delay(1000)
        const url = this.obtenerURL()
        if (url.includes('sede.mjusticia.gob.es')) {
          log.info(`[${this.nombre}] Redireccion completada: ${url}`)
          break
        }
      }
      await this.delay(3000)
    }

    // Paso 3: Esperar descarga automatica (se dispara sola post-login)
    try {
      const ruta = await esperaDescarga
      log.info(`[${this.nombre}] Certificado descargado automaticamente: ${ruta}`)
      return { exito: true, rutaDescarga: ruta, datos: { rutasArchivos: [ruta] } }
    } catch {
      log.warn(`[${this.nombre}] Descarga automatica no se disparo — intentando boton`)
    }

    await this.capturarPantalla('01-post-login')

    // Paso 4 (fallback): Click en "Descargar Certificado" (button type="submit")
    try {
      const tieneBoton = await this.ejecutarJs<boolean>(`
        (function() {
          var btns = document.querySelectorAll('button[type="submit"], input[type="submit"]');
          for (var i = 0; i < btns.length; i++) {
            var t = (btns[i].textContent || btns[i].value || '').toLowerCase();
            if (t.includes('descargar')) return true;
          }
          return false;
        })()
      `)

      if (tieneBoton) {
        log.info(`[${this.nombre}] Boton "Descargar Certificado" encontrado`)
        const ruta = await this.descargarConPromesa(
          () => this.ejecutarJs<void>(`
            (function() {
              var btns = document.querySelectorAll('button[type="submit"], input[type="submit"]');
              for (var i = 0; i < btns.length; i++) {
                var t = (btns[i].textContent || btns[i].value || '').toLowerCase();
                if (t.includes('descargar')) { btns[i].click(); return; }
              }
            })()
          `),
          nombreArchivo,
          30_000,
        )
        log.info(`[${this.nombre}] Certificado descargado via boton: ${ruta}`)
        return { exito: true, rutaDescarga: ruta, datos: { rutasArchivos: [ruta] } }
      }
    } catch (err) {
      log.warn(`[${this.nombre}] Descarga via boton fallo: ${(err as Error).message}`)
    }

    // Fallback final: printToPdf
    log.warn(`[${this.nombre}] Usando printToPdf como ultimo recurso`)
    await this.capturarPantalla('fallback-printToPdf')
    const rutaPdf = await this.printToPdf(nombreArchivo)
    return { exito: true, rutaDescarga: rutaPdf, datos: { rutasArchivos: [rutaPdf] } }
  }

  /** Registra listener will-download en la sesion ANTES de navegar */
  private configurarDescargaEnSesion(
    nombreArchivo: string,
    timeout: number,
  ): Promise<string> {
    if (!this.window || this.window.isDestroyed()) {
      return Promise.reject(new Error('Navegador no inicializado'))
    }

    const rutaDestino = join(this.carpetaDescargas, nombreArchivo)
    const sesion = this.window.webContents.session

    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        sesion.removeListener('will-download', onDescarga)
        reject(new Error('Timeout esperando descarga automatica'))
      }, timeout)

      const onDescarga = (_event: Electron.Event, item: Electron.DownloadItem): void => {
        item.setSavePath(rutaDestino)
        item.on('done', (_e, state) => {
          clearTimeout(timer)
          sesion.removeListener('will-download', onDescarga)
          if (state === 'completed') resolve(rutaDestino)
          else reject(new Error(`Descarga: ${state}`))
        })
      }

      sesion.on('will-download', onDescarga)
    })
  }
}
