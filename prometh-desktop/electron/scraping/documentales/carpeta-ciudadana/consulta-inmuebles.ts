import { type BrowserWindow } from 'electron'
import { join } from 'path'
import { writeFileSync } from 'fs'
import log from 'electron-log'
import { BaseScraperDocumental } from '../base-scraper-documental'
import type { ResultadoScraping } from '../../tipos'
import { loginCarpetaCiudadana } from './login-carpeta'

/**
 * Scraper para consultar bienes inmuebles desde Carpeta Ciudadana.
 *
 * Flujo observado en produccion:
 * 1. Login Cl@ve → navegar a /mcc/bienes-inmuebles
 * 2. Esperar SPA Angular con datos del Catastro
 * 3. Click boton "Descargar certificacion catastral" → abre popup con blob URL
 * 4. El popup dispara will-download con blob URL ("Certificacion catastral de titularidad.pdf")
 * 5. Capturar via will-download en sesion principal (la sesion es compartida con popups)
 * 6. Si will-download no se dispara, fallback a printToPdf del popup
 *
 * Nota: NO se puede usar sedecatastro.gob.es porque usa autenticacion
 * SSL/TLS directa (no Cl@ve), incompatible con BrowserWindow.
 */
export class ScraperConsultaInmuebles extends BaseScraperDocumental {
  private readonly urlInicio = 'https://carpetaciudadana.gob.es'
  private readonly urlInmuebles =
    'https://carpetaciudadana.gob.es/carpeta/mcc/bienes-inmuebles'

  get nombre(): string {
    return 'Consulta Inmuebles'
  }

  async ejecutar(): Promise<ResultadoScraping> {
    log.info(`[${this.nombre}] Iniciando consulta de inmuebles via Carpeta Ciudadana (v1.0.31)`)

    // Paso 1: Login en Carpeta Ciudadana
    await this.navegar(this.urlInicio)
    await this.delay(3000)
    await this.capturarPantalla('01-pagina-inicial')
    await loginCarpetaCiudadana(this)
    await this.capturarPantalla('02-post-login')

    // Paso 2: Navegar a la seccion de bienes inmuebles
    await this.navegar(this.urlInmuebles)
    await this.delay(3000)
    await this.capturarPantalla('03-inmuebles-navegado')

    // Paso 3: Esperar contenido real de inmuebles (SPA Angular)
    const contenidoCargado = await this.esperarContenidoInmuebles(60_000)

    // Debug: capturar estado final
    await this.capturarPantalla('04-contenido-final')
    const textoFinal = await this.ejecutarJs<string>(`
      (document.body.innerText || '').substring(0, 800)
    `)
    log.info(`[${this.nombre}] Texto final (800 chars): ${textoFinal}`)

    // Listar botones para debug
    const botonesInfo = await this.ejecutarJs<string>(`
      (function() {
        var resultado = [];
        var botones = document.querySelectorAll('button');
        for (var i = 0; i < botones.length; i++) {
          var texto = (botones[i].textContent || '').trim().substring(0, 80);
          if (texto.length > 0) {
            resultado.push({ tag: 'BUTTON', texto: texto, id: botones[i].id || '' });
          }
        }
        return JSON.stringify(resultado);
      })()
    `)
    log.info(`[${this.nombre}] Botones: ${botonesInfo}`)

    // Paso 4: Validar contenido
    if (!contenidoCargado) {
      const esValido = await this.validarContenidoMinimo()
      if (!esValido) {
        log.error(`[${this.nombre}] No se pudo cargar contenido de inmuebles`)
        await this.capturarPantalla('05-contenido-invalido')
        return {
          exito: false,
          error: 'No se pudo cargar la informacion de inmuebles. La pagina no cargo el contenido del Catastro.',
          datos: {},
        }
      }
    }

    const nombreArchivo = this.nombreConFecha('Consulta_Inmuebles')

    // Paso 5: Intentar descargar el PDF oficial del Catastro via boton
    const tieneBotonCatastral = await this.ejecutarJs<boolean>(`
      !!(function() {
        var botones = document.querySelectorAll('button');
        for (var i = 0; i < botones.length; i++) {
          var texto = (botones[i].textContent || '').toLowerCase();
          if (texto.includes('descargar certificaci') || texto.includes('certificación catastral') ||
              texto.includes('certificacion catastral')) {
            return true;
          }
        }
        return false;
      })()
    `)

    if (tieneBotonCatastral) {
      log.info(`[${this.nombre}] Boton "Descargar certificacion catastral" encontrado`)
      try {
        const resultado = await this.descargarCertificacionCatastral(nombreArchivo)
        if (resultado) return resultado
      } catch (err) {
        log.warn(`[${this.nombre}] Descarga certificacion catastral fallo: ${(err as Error).message}`)
      }
    } else {
      log.warn(`[${this.nombre}] No se encontro boton de descarga catastral`)
    }

    // Paso 6: Fallback — printToPdf de la pagina principal con contenido de inmuebles
    log.info(`[${this.nombre}] Fallback: printToPdf de pagina principal`)
    await this.capturarPantalla('07-fallback-pdf')
    const rutaDescarga = await this.printToPdf(nombreArchivo)
    log.info(`[${this.nombre}] PDF generado (fallback): ${rutaDescarga}`)

    return {
      exito: true,
      rutaDescarga,
      datos: { rutasArchivos: [rutaDescarga] },
    }
  }

  /**
   * Descargar el PDF oficial del Catastro:
   *
   * Estrategia 1: Registrar will-download en la sesion ANTES del click.
   *   El boton genera un blob URL que Electron intenta descargar.
   *   Si capturamos will-download, obtenemos el PDF oficial.
   *
   * Estrategia 2: Si will-download no se dispara, buscar popup y printToPdf.
   *
   * Estrategia 3: Si hay popup con blob URL, intentar capturar via fetch.
   */
  private async descargarCertificacionCatastral(
    nombreArchivo: string,
  ): Promise<ResultadoScraping | null> {
    const rutaDestino = join(this.carpetaDescargas, nombreArchivo)

    // Registrar will-download en la sesion PRINCIPAL antes del click
    // Los popups de Carpeta Ciudadana comparten la misma sesion (particion)
    const sesion = this.window.webContents.session

    let descargaCapturada = false
    let rutaFinalDescarga = ''

    const promesaDescarga = new Promise<string>((resolve) => {
      const timer = setTimeout(() => {
        sesion.removeListener('will-download', onDescarga)
        resolve('') // vacio = no hubo descarga
      }, 20_000)

      const onDescarga = (_event: Electron.Event, item: Electron.DownloadItem): void => {
        log.info(`[${this.nombre}] will-download capturado! filename: ${item.getFilename()}, url: ${item.getURL().substring(0, 100)}`)
        item.setSavePath(rutaDestino)
        descargaCapturada = true

        item.on('done', (_e, state) => {
          clearTimeout(timer)
          sesion.removeListener('will-download', onDescarga)
          if (state === 'completed') {
            rutaFinalDescarga = rutaDestino
            log.info(`[${this.nombre}] PDF catastral descargado: ${rutaDestino}`)
            resolve(rutaDestino)
          } else {
            log.warn(`[${this.nombre}] Descarga state: ${state}`)
            resolve('')
          }
        })
      }
      sesion.on('will-download', onDescarga)
    })

    // Preparar listener de popup TAMBIEN (por si abre ventana nueva)
    const waitPopup = this.prepararEsperaVentana(20_000).catch(() => null)

    // Click en el boton de descarga catastral
    await this.ejecutarJs(`
      (function() {
        var botones = document.querySelectorAll('button');
        for (var i = 0; i < botones.length; i++) {
          var texto = (botones[i].textContent || '').toLowerCase();
          if (texto.includes('descargar certificaci') || texto.includes('certificación catastral') ||
              texto.includes('certificacion catastral')) {
            botones[i].click();
            return true;
          }
        }
        return false;
      })()
    `)
    log.info(`[${this.nombre}] Click en boton descarga catastral — esperando descarga o popup...`)
    await this.capturarPantalla('05-post-click-descarga')

    // Esperar resultado: will-download o popup
    const rutaDescargada = await promesaDescarga

    if (rutaDescargada) {
      log.info(`[${this.nombre}] Certificacion catastral obtenida via will-download: ${rutaDescargada}`)
      return { exito: true, rutaDescarga: rutaDescargada, datos: { rutasArchivos: [rutaDescargada] } }
    }

    // Si no hubo will-download, intentar con el popup
    const popup = await waitPopup
    if (popup && !popup.isDestroyed()) {
      log.info(`[${this.nombre}] Popup abierto (id: ${popup.id}) — intentando capturar PDF`)
      return await this.capturarPdfDesdePopup(popup, nombreArchivo)
    }

    log.warn(`[${this.nombre}] Ni will-download ni popup disponible`)
    return null
  }

  /**
   * Captura el PDF desde un popup del Catastro:
   * 1. Espera carga del popup
   * 2. Intenta will-download en la sesion del popup
   * 3. Si tiene blob URL, intenta fetch + guardar
   * 4. Fallback: printToPdf del popup
   */
  private async capturarPdfDesdePopup(
    popup: BrowserWindow,
    nombreArchivo: string,
  ): Promise<ResultadoScraping | null> {
    // Esperar a que el popup cargue
    await this.esperarCargaPopup(popup, 30_000)

    const urlPopup = popup.webContents.getURL()
    log.info(`[${this.nombre}] URL popup: ${urlPopup}`)

    // Debug info del popup
    try {
      const titulo = await popup.webContents.executeJavaScript('document.title') as string
      const bodyLen = await popup.webContents.executeJavaScript(
        'document.body ? document.body.innerText.length : 0',
      ) as number
      log.info(`[${this.nombre}] Popup — titulo: "${titulo}", body: ${bodyLen} chars`)
    } catch (e) {
      log.warn(`[${this.nombre}] Error leyendo popup: ${(e as Error).message}`)
    }

    const rutaDestino = join(this.carpetaDescargas, nombreArchivo)

    // Si la URL del popup es un blob, intentar fetch del blob desde el contexto del popup
    if (urlPopup.startsWith('blob:')) {
      log.info(`[${this.nombre}] Popup tiene blob URL — intentando fetch blob`)
      try {
        const base64 = await popup.webContents.executeJavaScript(`
          (async function() {
            try {
              var resp = await fetch('${urlPopup}');
              var blob = await resp.blob();
              var arrayBuffer = await blob.arrayBuffer();
              var bytes = new Uint8Array(arrayBuffer);
              var binary = '';
              for (var i = 0; i < bytes.byteLength; i++) {
                binary += String.fromCharCode(bytes[i]);
              }
              return btoa(binary);
            } catch(e) {
              return 'ERROR:' + e.message;
            }
          })()
        `) as string

        if (base64 && !base64.startsWith('ERROR:')) {
          const buffer = Buffer.from(base64, 'base64')
          writeFileSync(rutaDestino, buffer)
          log.info(`[${this.nombre}] PDF catastral capturado via blob fetch: ${rutaDestino} (${buffer.length} bytes)`)
          return { exito: true, rutaDescarga: rutaDestino, datos: { rutasArchivos: [rutaDestino] } }
        } else {
          log.warn(`[${this.nombre}] Fetch blob fallo: ${base64}`)
        }
      } catch (err) {
        log.warn(`[${this.nombre}] Error fetching blob: ${(err as Error).message}`)
      }
    }

    // Intentar will-download en el popup
    try {
      const ruta = await this.esperarDescargaEnVentana(popup, nombreArchivo, 10_000)
      log.info(`[${this.nombre}] PDF via will-download del popup: ${ruta}`)
      return { exito: true, rutaDescarga: ruta, datos: { rutasArchivos: [ruta] } }
    } catch {
      log.info(`[${this.nombre}] will-download del popup no se disparo`)
    }

    // Fallback: printToPdf del popup
    try {
      const buffer = await popup.webContents.printToPDF({
        printBackground: true,
        landscape: false,
      })
      writeFileSync(rutaDestino, buffer)
      log.info(`[${this.nombre}] PDF via printToPdf del popup: ${rutaDestino}`)
      return { exito: true, rutaDescarga: rutaDestino, datos: { rutasArchivos: [rutaDestino] } }
    } catch (err) {
      log.warn(`[${this.nombre}] printToPdf popup fallo: ${(err as Error).message}`)
    }

    return null
  }

  // ── Espera contenido Angular ──────────────────────────────────

  /**
   * Espera a que la SPA Angular cargue el contenido real de inmuebles.
   * Busca texto especifico del Catastro, NO solo longitud de body.
   */
  private async esperarContenidoInmuebles(timeout: number): Promise<boolean> {
    const inicio = Date.now()
    let intentosRedireccion = 0

    while (Date.now() - inicio < timeout) {
      const url = await this.obtenerURL()

      // Si nos redirigieron a pasarela Cl@ve, re-autenticar
      if (url.includes('clave.gob.es') || url.includes('pasarela')) {
        intentosRedireccion++
        if (intentosRedireccion > 3) {
          log.error(`[${this.nombre}] Demasiados reintentos auth (${intentosRedireccion})`)
          return false
        }
        log.info(`[${this.nombre}] Redirigido a pasarela — re-autenticando (${intentosRedireccion})`)
        await this.manejarPasarelaClave()
        await this.delay(5000)
        await this.navegar(this.urlInmuebles)
        await this.delay(5000)
        continue
      }

      // Si estamos en la home de carpeta, renavegar
      if (url === 'https://carpetaciudadana.gob.es/' ||
          url.includes('/public') ||
          url.includes('/clave.htm') ||
          url.includes('carpetaEmpresa')) {
        log.warn(`[${this.nombre}] Redirigido a home (${url}) — renavegando`)
        await this.navegar(this.urlInmuebles)
        await this.delay(5000)
        continue
      }

      // Verificar si la SPA cargo contenido real de inmuebles
      const resultado = await this.ejecutarJs<string>(`
        (function() {
          var texto = (document.body.innerText || '').toLowerCase();

          var keywords = [
            'bienes inmuebles urbanos',
            'bienes inmuebles rústicos',
            'bienes inmuebles rusticos',
            'referencia catastral',
            'valor catastral',
            'uso principal',
            'superficie construida',
            'superficie suelo',
            'dirección general del catastro',
            'direccion general del catastro',
            'domicilio tributario',
            'clase de inmueble',
            'descargar certificación catastral',
            'descargar certificacion catastral',
            'no se han encontrado inmuebles',
            'no dispone de inmuebles',
          ];

          for (var i = 0; i < keywords.length; i++) {
            if (texto.includes(keywords[i])) {
              return 'FOUND:' + keywords[i];
            }
          }

          // Buscar componentes Angular de inmuebles
          var componentes = document.querySelectorAll('[class*="inmueble"], [class*="catastro"], app-bienes, app-inmuebles');
          if (componentes.length > 0) return 'FOUND:angular-component';

          // Buscar tablas con datos de catastro
          var tablas = document.querySelectorAll('table, .mat-table, mat-table');
          for (var j = 0; j < tablas.length; j++) {
            var ct = (tablas[j].textContent || '').toLowerCase();
            if (ct.includes('catastral') || ct.includes('superficie') || ct.includes('inmueble')) {
              return 'FOUND:table-with-data';
            }
          }

          // Contenido principal
          var main = document.querySelector('main, [role="main"], .main-content, router-outlet + *');
          if (main) {
            var mt = (main.textContent || '').toLowerCase();
            if (mt.length > 100 && (mt.includes('inmueble') || mt.includes('catastro') || mt.includes('urbano'))) {
              return 'FOUND:main-content';
            }
          }

          return 'NOT_FOUND:len=' + texto.length;
        })()
      `)

      log.info(`[${this.nombre}] Check contenido: ${resultado}`)

      if (resultado && resultado.startsWith('FOUND:')) {
        log.info(`[${this.nombre}] Contenido inmuebles detectado: ${resultado}`)
        await this.delay(3000)
        return true
      }

      await this.delay(2000)
    }

    log.warn(`[${this.nombre}] Timeout esperando contenido inmuebles`)
    return false
  }

  // ── Validacion minima ──────────────────────────────────

  private async validarContenidoMinimo(): Promise<boolean> {
    const texto = await this.ejecutarJs<string>(`
      (document.body.innerText || '').substring(0, 2000)
    `)

    if (!texto || texto.length < 100) return false

    const textoLower = texto.toLowerCase()

    const invalidos = [
      'identifícate', 'cl@ve permanente', 'cl@ve móvil',
      'seleccione el método', 'elige tu rol', 'acceder a la carpeta',
    ]
    for (const patron of invalidos) {
      if (textoLower.includes(patron)) {
        log.warn(`[${this.nombre}] Pagina invalida: "${patron}"`)
        return false
      }
    }

    const soloFooter = textoLower.includes('aviso legal') &&
                       !textoLower.includes('inmueble') &&
                       !textoLower.includes('catastro')
    if (soloFooter) {
      log.warn(`[${this.nombre}] Solo footer — sin contenido inmuebles`)
      return false
    }

    log.warn(`[${this.nombre}] Contenido ambiguo — generando PDF`)
    return true
  }

  // ── Helpers popup ──────────────────────────────────────

  private async esperarCargaPopup(ventana: BrowserWindow, timeout: number): Promise<void> {
    await new Promise<void>((resolve) => {
      const timer = setTimeout(resolve, Math.min(timeout, 15_000))
      if (ventana.isDestroyed()) { clearTimeout(timer); resolve(); return }
      ventana.webContents.once('did-finish-load', () => { clearTimeout(timer); resolve() })
      if (!ventana.webContents.isLoading()) { clearTimeout(timer); resolve() }
    })

    const inicio = Date.now()
    while (Date.now() - inicio < timeout) {
      if (ventana.isDestroyed()) break
      try {
        const len = await ventana.webContents.executeJavaScript(
          'document.body ? document.body.innerText.length : 0',
        ) as number
        if (len > 50) {
          log.info(`[${this.nombre}] Popup listo: ${len} chars`)
          break
        }
      } catch { break }
      await this.delay(1000)
    }
    await this.delay(2000)
  }

  // esperarDescargaEnVentana heredado de BaseScraperDocumental
}
