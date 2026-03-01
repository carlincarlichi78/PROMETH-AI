import { join } from 'path'
import log from 'electron-log'
import { BaseScraperDocumental } from '../base-scraper-documental'
import type { ResultadoScraping, ConfigScraping } from '../../tipos'

/**
 * Scraper semi-automatico para certificado literal de matrimonio.
 *
 * Flujo REAL mapeado con Chrome MCP (2026-02-21):
 * 1. Navegar a sede.mjusticia.gob.es SERECI con idMateria=MAT
 * 2. Redirige a pasarela Cl@ve → click "DNIe / Certificado electronico"
 * 3. Auth certificado → redirige de vuelta a sede.mjusticia.gob.es
 * 4. Paso 1: Formulario "Ano del matrimonio" (input number) + "Solicitar certificado"
 * 5. Paso 2: Formulario completo:
 *    - Fecha del matrimonio (dd/mm/aaaa) — id="fechaMatrimonio"
 *    - Pais Inscripcion — id="paisInsMatrimonio" (default ESPANA)
 *    - Provincia Inscripcion — id="provinciaInsMatrimonio"
 *    - Municipio Inscripcion — id="municipioInsMatrimonio"
 *    + datos personales pre-rellenados desde certificado
 * 6. Submit "Solicitar certificado" → descarga PDF
 *
 * DIFERENCIA vs Nacimiento: Nacimiento descarga automatico post-login.
 * Matrimonio requiere rellenar datos del hecho (ano, fecha, lugar inscripcion).
 * Por eso es SEMI-AUTOMATICO: el scraper autentica y navega, el usuario rellena.
 *
 * Auth: Cl@ve (pasarela.clave.gob.es) → DNIe/certificado electronico
 */
export class ScraperCertificadoMatrimonio extends BaseScraperDocumental {
  private readonly url =
    'https://sede.mjusticia.gob.es/sereci/clave/solicitarCertificadoSolicitudLiteral?idMateria=MAT'

  constructor(serialNumber: string, config?: Partial<ConfigScraping>) {
    super(serialNumber, {
      ...config,
      // Timeout extendido: 5 minutos para que el usuario rellene el formulario
      timeoutGlobal: 300_000,
    })
  }

  get nombre(): string {
    return 'Certificado Matrimonio'
  }

  async ejecutar(): Promise<ResultadoScraping> {
    log.info(`[${this.nombre}] Iniciando — scraper semi-automatico`)

    const nombreArchivo = this.nombreConFecha('Certificado_Matrimonio')

    // Configurar will-download ANTES de navegar (captura descarga post-formulario)
    const esperaDescarga = this.configurarDescargaEnSesion(nombreArchivo, 300_000)

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

    // Paso 3: Verificar que estamos en el formulario del matrimonio
    const enFormulario = await this.ejecutarJs<boolean>(`
      (function() {
        var titulo = document.body.innerText || '';
        return titulo.includes('matrimonio') || titulo.includes('Matrimonio');
      })()
    `)

    if (enFormulario) {
      log.info(
        `[${this.nombre}] Formulario de matrimonio cargado — esperando intervencion del usuario`,
      )
    } else {
      log.warn(`[${this.nombre}] No se detecto formulario de matrimonio en la pagina`)
    }

    await this.capturarPantalla('01-formulario-matrimonio')

    // Paso 4: Esperar a que el usuario rellene y haga submit
    // will-download se disparara cuando el servidor genere el PDF
    // Timeout: 5 minutos (el usuario necesita rellenar ano + datos + submit x2)
    try {
      const ruta = await esperaDescarga
      log.info(`[${this.nombre}] Certificado descargado: ${ruta}`)
      return { exito: true, rutaDescarga: ruta, datos: { rutasArchivos: [ruta] } }
    } catch {
      log.warn(`[${this.nombre}] Descarga will-download no se disparo — intentando fallback`)
    }

    // Fallback: si no se disparo will-download, intentar boton "Descargar"
    try {
      const tieneBotonDescarga = await this.ejecutarJs<boolean>(`
        (function() {
          var btns = document.querySelectorAll('button[type="submit"], input[type="submit"], a');
          for (var i = 0; i < btns.length; i++) {
            var t = (btns[i].textContent || btns[i].value || '').toLowerCase();
            if (t.includes('descargar')) return true;
          }
          return false;
        })()
      `)

      if (tieneBotonDescarga) {
        log.info(`[${this.nombre}] Boton "Descargar" encontrado — clickeando`)
        const ruta = await this.descargarConPromesa(
          () =>
            this.ejecutarJs<void>(`
            (function() {
              var btns = document.querySelectorAll('button[type="submit"], input[type="submit"], a');
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
      log.warn(`[${this.nombre}] Fallback boton fallo: ${(err as Error).message}`)
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
        reject(new Error('Timeout esperando descarga (5 min)'))
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
