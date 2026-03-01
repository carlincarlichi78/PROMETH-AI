import { BrowserWindow, session, type Certificate, type DownloadItem } from 'electron'
import { join } from 'path'
import { mkdirSync, existsSync, writeFileSync } from 'fs'
import { app } from 'electron'
import log from 'electron-log'
import type { ResultadoScraping, ConfigScraping } from '../tipos'
import { CONFIG_DEFAULT } from '../tipos'

/** User agents para rotacion */
const USER_AGENTS = [
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0',
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0',
]

/**
 * Clase base para scrapers documentales que usan BrowserWindow de Electron.
 * A diferencia de BaseScraper (Puppeteer), usa:
 * - select-client-certificate para autenticacion automatica con certificado
 * - will-download para descargas nativas
 * - printToPDF para generar PDFs de paginas renderizadas
 */
export abstract class BaseScraperDocumental {
  protected window: BrowserWindow | null = null
  protected ventanasHijas: BrowserWindow[] = []

  readonly serialNumber: string
  readonly config: ConfigScraping
  readonly carpetaDescargas: string

  constructor(serialNumber: string, config?: Partial<ConfigScraping>) {
    this.serialNumber = serialNumber
    this.config = { ...CONFIG_DEFAULT, ...config }

    const baseDescargas =
      this.config.carpetaDescargas ||
      join(app.getPath('documents'), 'CertiGestor', 'descargas')
    // Usar nombre legible del titular si esta disponible, sino serialNumber
    const subcarpeta = this.config.nombreCarpeta || serialNumber
    this.carpetaDescargas = join(baseDescargas, subcarpeta)

    if (!existsSync(this.carpetaDescargas)) {
      mkdirSync(this.carpetaDescargas, { recursive: true })
    }
  }

  /** Nombre descriptivo del scraper para logs */
  abstract get nombre(): string

  /** Logica especifica de cada scraper */
  abstract ejecutar(): Promise<ResultadoScraping>

  /**
   * Inicializa BrowserWindow con session temporal y seleccion automatica
   * de certificado por serialNumber.
   */
  async inicializarNavegador(): Promise<void> {
    const particion = `scraper-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
    const sesionTemp = session.fromPartition(particion, { cache: false })

    this.window = new BrowserWindow({
      width: 1200,
      height: 800,
      show: !this.config.headless,
      webPreferences: {
        session: sesionTemp,
        nodeIntegration: false,
        contextIsolation: true,
      },
    })

    // User agent aleatorio
    const userAgent = USER_AGENTS[Math.floor(Math.random() * USER_AGENTS.length)]
    this.window.webContents.setUserAgent(userAgent)

    // Seleccion automatica de certificado por serialNumber
    const targetSerial = this.serialNumber.toLowerCase()
    this.window.webContents.on(
      'select-client-certificate',
      (event, _url, certificateList: Certificate[], callback) => {
        event.preventDefault()
        const seleccionado = certificateList.find(
          (cert) => cert.serialNumber.toLowerCase() === targetSerial,
        )

        if (seleccionado) {
          log.info(
            `[${this.nombre}] Certificado seleccionado: ${seleccionado.subjectName}`,
          )
          callback(seleccionado)
        } else {
          log.error(
            `[${this.nombre}] Certificado ${this.serialNumber} no encontrado. Disponibles: ${certificateList.map((c) => c.serialNumber).join(', ')}`,
          )
          callback(null as unknown as Certificate)
        }
      },
    )

    // Rastrear ventanas hijas (popups de firma)
    this.ventanasHijas = []
    this.window.webContents.on('did-create-window', (childWindow) => {
      log.info(`[${this.nombre}] Popup creado: ${childWindow.id}`)
      this.ventanasHijas.push(childWindow)

      if (this.config.headless && childWindow.isVisible()) {
        childWindow.hide()
      }
      childWindow.webContents.setUserAgent(userAgent)

      childWindow.on('closed', () => {
        this.ventanasHijas = this.ventanasHijas.filter(
          (w) => w !== childWindow && !w.isDestroyed(),
        )
      })
    })

    log.info(`[${this.nombre}] Navegador inicializado — particion: ${particion}`)
  }

  /** Cierra el navegador y limpia recursos */
  async cerrarNavegador(): Promise<void> {
    // Cerrar ventanas hijas
    for (const hijo of this.ventanasHijas) {
      if (hijo && !hijo.isDestroyed()) {
        hijo.removeAllListeners()
        hijo.close()
      }
    }
    this.ventanasHijas = []

    if (this.window && !this.window.isDestroyed()) {
      try {
        const currentSession = this.window.webContents.session
        await currentSession
          .clearStorageData({
            storages: [
              'cookies', 'filesystem', 'indexdb', 'localstorage',
              'shadercache', 'websql', 'serviceworkers', 'cachestorage',
            ],
          })
          .catch((err) =>
            log.warn(`[${this.nombre}] Error limpiando storage: ${(err as Error).message}`),
          )

        this.window.removeAllListeners()
        this.window.webContents.removeAllListeners()
        this.window.close()
      } catch (err) {
        log.warn(
          `[${this.nombre}] Error cerrando navegador: ${(err as Error).message}`,
        )
      } finally {
        this.window = null
      }
    }
  }

  /**
   * Ejecuta el scraper con timeout global y lifecycle completo.
   */
  async run(): Promise<ResultadoScraping> {
    const timeoutMs = this.config.timeoutGlobal

    const logicaPromise = async (): Promise<ResultadoScraping> => {
      try {
        await this.inicializarNavegador()
        return await this.ejecutar()
      } catch (error) {
        const mensaje = error instanceof Error ? error.message : 'Error desconocido'
        log.error(`[${this.nombre}] Error:`, mensaje)
        return { exito: false, error: mensaje }
      }
    }

    const timeoutPromise = new Promise<ResultadoScraping>((resolve) => {
      setTimeout(() => {
        const msg = `Timeout global de ${timeoutMs / 1000}s excedido`
        log.error(`[${this.nombre}] ${msg}`)
        resolve({ exito: false, error: msg })
      }, timeoutMs)
    })

    try {
      return await Promise.race([logicaPromise(), timeoutPromise])
    } finally {
      await this.cerrarNavegador()
    }
  }

  // ── Helpers ─────────────────────────────────────────────

  /** Navega a una URL y espera a que cargue */
  async navegar(url: string): Promise<void> {
    if (!this.window || this.window.isDestroyed()) {
      throw new Error('Navegador no inicializado')
    }

    await new Promise<void>((resolve, reject) => {
      const wc = this.window!.webContents
      let resuelto = false

      const timer = setTimeout(() => {
        if (!resuelto) {
          resuelto = true
          reject(new Error(`Timeout navegando a ${url}`))
        }
      }, this.config.timeoutGlobal)

      const onFinish = (): void => {
        if (resuelto) return
        resuelto = true
        clearTimeout(timer)
        wc.removeListener('did-finish-load', onFinish)
        wc.removeListener('did-fail-load', onFail)
        resolve()
      }

      const onFail = (
        _event: Electron.Event,
        errorCode: number,
        errorDescription: string,
      ): void => {
        // ERR_ABORTED es normal en redirecciones
        if (errorCode === -3) return
        if (resuelto) return
        resuelto = true
        clearTimeout(timer)
        wc.removeListener('did-finish-load', onFinish)
        wc.removeListener('did-fail-load', onFail)
        reject(new Error(`Fallo de carga: ${errorDescription} (${errorCode})`))
      }

      wc.on('did-finish-load', onFinish)
      wc.on('did-fail-load', onFail)

      this.window!.loadURL(url).catch((error: Error) => {
        if (error.message.includes('ERR_ABORTED')) return
        if (!resuelto) {
          resuelto = true
          clearTimeout(timer)
          reject(error)
        }
      })
    })
  }

  /** Espera a que un selector aparezca en la pagina */
  async esperarSelector(selector: string, timeout?: number): Promise<void> {
    if (!this.window || this.window.isDestroyed()) {
      throw new Error('Navegador no inicializado')
    }

    const ms = timeout ?? this.config.timeoutElemento
    const inicio = Date.now()

    while (Date.now() - inicio < ms) {
      const existe = await this.window.webContents.executeJavaScript(
        `!!document.querySelector('${selector.replace(/'/g, "\\'")}')`,
      )
      if (existe) return
      await this.delay(500)
    }

    throw new Error(`Timeout esperando selector: ${selector}`)
  }

  /** Click en un elemento via JavaScript */
  async clickElemento(selector: string): Promise<void> {
    if (!this.window || this.window.isDestroyed()) {
      throw new Error('Navegador no inicializado')
    }

    const existe = await this.window.webContents.executeJavaScript(
      `!!document.querySelector('${selector.replace(/'/g, "\\'")}')`,
    )
    if (!existe) {
      throw new Error(`Elemento no encontrado: ${selector}`)
    }

    await this.window.webContents.executeJavaScript(
      `document.querySelector('${selector.replace(/'/g, "\\'")}').click()`,
    )
  }

  /** Obtiene la URL actual del navegador */
  obtenerURL(): string {
    if (!this.window || this.window.isDestroyed()) {
      throw new Error('Navegador no inicializado')
    }
    return this.window.webContents.getURL()
  }

  /** Obtiene el texto de un elemento */
  async obtenerTexto(selector: string): Promise<string> {
    if (!this.window || this.window.isDestroyed()) {
      throw new Error('Navegador no inicializado')
    }

    return this.window.webContents.executeJavaScript(
      `(document.querySelector('${selector.replace(/'/g, "\\'")}')?.textContent ?? '').trim()`,
    ) as Promise<string>
  }

  /** Ejecuta JavaScript arbitrario en la pagina */
  async ejecutarJs<T = unknown>(codigo: string): Promise<T> {
    if (!this.window || this.window.isDestroyed()) {
      throw new Error('Navegador no inicializado')
    }
    return this.window.webContents.executeJavaScript(codigo) as Promise<T>
  }

  /** Selecciona un valor en un dropdown <select> */
  async seleccionarOpcion(selector: string, valor: string): Promise<void> {
    await this.ejecutarJs(`
      const sel = document.querySelector('${selector.replace(/'/g, "\\'")}');
      if (sel) {
        sel.value = '${valor.replace(/'/g, "\\'")}';
        sel.dispatchEvent(new Event('change', { bubbles: true }));
      }
    `)
  }

  /**
   * Descarga un archivo con will-download.
   * Ejecuta un disparador (funcion que clickea el enlace) y espera la descarga.
   */
  async descargarConPromesa(
    disparador: () => Promise<void>,
    nombreArchivo: string,
    timeout?: number,
  ): Promise<string> {
    if (!this.window || this.window.isDestroyed()) {
      throw new Error('Navegador no inicializado')
    }

    const ms = timeout ?? 30_000
    const rutaDestino = join(this.carpetaDescargas, nombreArchivo)

    return new Promise<string>((resolve, reject) => {
      const timer = setTimeout(() => {
        sesion.removeListener('will-download', onDescarga)
        reject(new Error(`Timeout de descarga: ${nombreArchivo}`))
      }, ms)

      const sesion = this.window!.webContents.session

      const onDescarga = (_event: Electron.Event, item: DownloadItem): void => {
        item.setSavePath(rutaDestino)

        item.on('done', (_e, state) => {
          clearTimeout(timer)
          sesion.removeListener('will-download', onDescarga)

          if (state === 'completed') {
            log.info(`[${this.nombre}] Descargado: ${rutaDestino}`)
            resolve(rutaDestino)
          } else {
            reject(new Error(`Descarga fallida: ${state}`))
          }
        })
      }

      sesion.on('will-download', onDescarga)

      // Ejecutar el disparador (click en enlace de descarga)
      disparador().catch((err) => {
        clearTimeout(timer)
        sesion.removeListener('will-download', onDescarga)
        reject(err)
      })
    })
  }

  /**
   * Genera PDF de la pagina actual via printToPDF.
   */
  async printToPdf(
    nombreArchivo: string,
    opciones?: Electron.PrintToPDFOptions,
  ): Promise<string> {
    if (!this.window || this.window.isDestroyed()) {
      throw new Error('Navegador no inicializado')
    }

    const rutaDestino = join(this.carpetaDescargas, nombreArchivo)
    const buffer = await this.window.webContents.printToPDF({
      printBackground: true,
      landscape: false,
      ...opciones,
    })

    writeFileSync(rutaDestino, buffer)
    log.info(`[${this.nombre}] PDF generado: ${rutaDestino}`)
    return rutaDestino
  }

  /**
   * Prepara la espera de una ventana hija ANTES de hacer el click que la dispara.
   * Devuelve una Promise que se resuelve cuando did-create-window dispara.
   * Uso: const waitPopup = this.prepararEsperaVentana(); await click; const popup = await waitPopup;
   */
  prepararEsperaVentana(timeout?: number): Promise<BrowserWindow> {
    const ms = timeout ?? this.config.timeoutElemento
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        reject(new Error('Timeout esperando nueva ventana'))
      }, ms)

      const handler = (childWindow: BrowserWindow): void => {
        clearTimeout(timer)
        resolve(childWindow)
      }
      // Escuchar UNA sola vez el proximo popup
      this.window!.webContents.once('did-create-window', handler)
    })
  }

  /**
   * Espera a que se abra una nueva ventana hija (popup).
   * DEPRECATED: usar prepararEsperaVentana() antes del click para evitar race conditions.
   */
  async esperarVentanaNueva(timeout?: number): Promise<BrowserWindow> {
    const ms = timeout ?? this.config.timeoutElemento
    const cantidadAnterior = this.ventanasHijas.length

    const inicio = Date.now()
    while (Date.now() - inicio < ms) {
      if (this.ventanasHijas.length > cantidadAnterior) {
        return this.ventanasHijas[this.ventanasHijas.length - 1]
      }
      await this.delay(500)
    }

    throw new Error('Timeout esperando nueva ventana')
  }

  /** Espera un numero de milisegundos */
  async delay(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms))
  }

  /**
   * Intenta cerrar un modal/cookie banner si existe (no falla si no aparece).
   */
  async cerrarModalSiExiste(selector: string): Promise<void> {
    try {
      const existe = await this.ejecutarJs<boolean>(
        `!!document.querySelector('${selector.replace(/'/g, "\\'")}')`,
      )
      if (existe) {
        await this.clickElemento(selector)
        await this.delay(500)
      }
    } catch {
      // Ignorar — el modal puede no existir
    }
  }

  /**
   * Detecta y maneja la pasarela Cl@ve (pasarela.clave.gob.es).
   * Usa selectedIdP('AFIRMA') como metodo primario (patron Findiur),
   * con fallback a busqueda por texto del boton.
   */
  async manejarPasarelaClave(
    timeoutDeteccion = 10_000,
    timeoutPostLogin = 30_000,
  ): Promise<boolean> {
    if (!this.window || this.window.isDestroyed()) return false

    const inicio = Date.now()

    while (Date.now() - inicio < timeoutDeteccion) {
      const url = this.window.webContents.getURL()

      if (url.includes('pasarela.clave.gob.es') || url.includes('clave.gob.es')) {
        log.info(`[${this.nombre}] Pasarela Cl@ve detectada: ${url}`)
        await this.delay(2000)

        // Estrategia 1 (Findiur): selectedIdP('AFIRMA')
        const usadoSelectedIdP = await this.ejecutarJs<boolean>(`
          (function() {
            try {
              if (typeof selectedIdP === 'function') {
                selectedIdP('AFIRMA');
                if (typeof idpRedirect !== 'undefined' && idpRedirect.submit) {
                  idpRedirect.submit();
                }
                return true;
              }
            } catch(e) {}
            return false;
          })()
        `)

        if (usadoSelectedIdP) {
          log.info(`[${this.nombre}] selectedIdP('AFIRMA') ejecutado`)
        } else {
          // Estrategia 2: boton con onclick selectedIdP('AFIRMA')
          const clicBotonAfirma = await this.ejecutarJs<boolean>(`
            (function() {
              var btn = document.querySelector("button[onclick*=\\"selectedIdP('AFIRMA')\\"]");
              if (btn) { btn.click(); return true; }
              return false;
            })()
          `)

          if (clicBotonAfirma) {
            log.info(`[${this.nombre}] Clic en boton AFIRMA por selector`)
          } else {
            // Estrategia 3: buscar por texto
            const clicTexto = await this.ejecutarJs<boolean>(`
              (function() {
                var botones = document.querySelectorAll('article button, button, a.btn');
                for (var i = 0; i < botones.length; i++) {
                  var texto = (botones[i].textContent || '').toLowerCase();
                  if (texto.includes('certificado') || texto.includes('dnie') || texto.includes('afirma')) {
                    botones[i].click();
                    return true;
                  }
                }
                return false;
              })()
            `)

            if (clicTexto) {
              log.info(`[${this.nombre}] Clic en boton certificado por texto`)
            } else {
              log.warn(`[${this.nombre}] No se encontro boton de certificado en Cl@ve`)
              return false
            }
          }
        }

        // Esperar redireccion post-autenticacion
        const urlClave = this.window.webContents.getURL()
        const inicioEspera = Date.now()
        while (Date.now() - inicioEspera < timeoutPostLogin) {
          const urlActual = this.window.webContents.getURL()
          if (urlActual !== urlClave) {
            log.info(`[${this.nombre}] Redireccion post-Cl@ve: ${urlActual}`)
            break
          }
          await this.delay(500)
        }

        await this.delay(3000)
        return true
      }

      await this.delay(500)
    }

    return false
  }

  /**
   * Captura screenshot de la ventana actual para diagnostico.
   * Se guarda en la carpeta de descargas con prefijo debug_.
   */
  async capturarPantalla(paso: string): Promise<void> {
    if (!this.window || this.window.isDestroyed()) return
    try {
      const url = this.window.webContents.getURL()
      const titulo = await this.window.webContents.executeJavaScript('document.title') as string
      const textoBody = await this.window.webContents.executeJavaScript(
        'document.body ? document.body.innerText.substring(0, 500) : "(sin body)"',
      ) as string
      log.info(`[${this.nombre}][DEBUG ${paso}] URL: ${url}`)
      log.info(`[${this.nombre}][DEBUG ${paso}] Titulo: ${titulo}`)
      log.info(`[${this.nombre}][DEBUG ${paso}] Body (500 chars): ${textoBody.replace(/\\n/g, ' ').substring(0, 300)}`)

      const image = await this.window.webContents.capturePage()
      const buffer = image.toPNG()
      const nombreScreenshot = `debug_${this.nombre.replace(/\\s+/g, '_')}_${paso}_${Date.now()}.png`
      // Screenshots de debug van a subcarpeta _debug/ para no mezclar con PDFs finales
      const carpetaDebug = join(this.carpetaDescargas, '_debug')
      if (!existsSync(carpetaDebug)) {
        mkdirSync(carpetaDebug, { recursive: true })
      }
      const ruta = join(carpetaDebug, nombreScreenshot)
      writeFileSync(ruta, buffer)
      log.info(`[${this.nombre}][DEBUG ${paso}] Screenshot: ${ruta}`)
    } catch (err) {
      log.warn(`[${this.nombre}][DEBUG ${paso}] Error capturando pantalla: ${(err as Error).message}`)
    }
  }

  /** Genera nombre de archivo con fecha */
  protected nombreConFecha(base: string, extension = 'pdf'): string {
    const fecha = new Date().toISOString().slice(0, 10) // YYYY-MM-DD
    return `${base}_${fecha}.${extension}`
  }

  // ── Helpers de popups ─────────────────────────────────────

  /** Espera un selector en una ventana hija (popup de firma, etc.) */
  async esperarSelectorEnVentana(
    ventana: BrowserWindow,
    selector: string,
    timeout = 30_000,
  ): Promise<void> {
    const inicio = Date.now()
    const sel = selector.replace(/'/g, "\\'")
    while (Date.now() - inicio < timeout) {
      if (ventana.isDestroyed()) throw new Error('Ventana cerrada')
      const existe = await ventana.webContents.executeJavaScript(
        `!!document.querySelector('${sel}')`,
      )
      if (existe) return
      await this.delay(500)
    }
    throw new Error(`Timeout esperando ${selector} en popup`)
  }

  /** Click en un elemento de una ventana hija */
  async clickElementoEnVentana(
    ventana: BrowserWindow,
    selector: string,
  ): Promise<void> {
    const sel = selector.replace(/'/g, "\\'")
    await ventana.webContents.executeJavaScript(
      `document.querySelector('${sel}').click()`,
    )
  }

  /**
   * Configura interceptor de popups para convertirlos en descargas reales.
   * Patron Findiur: setWindowOpenHandler intercepta window.open del portal,
   * cancela la apertura de la ventana y usa downloadURL para disparar will-download.
   *
   * Devuelve Promise que se resuelve con la ruta del archivo descargado.
   */
  configurarInterceptorDescarga(
    nombreArchivo: string,
    timeout = 30_000,
  ): Promise<string> {
    if (!this.window || this.window.isDestroyed()) {
      throw new Error('Navegador no inicializado')
    }

    const rutaDestino = join(this.carpetaDescargas, nombreArchivo)
    const win = this.window

    return new Promise<string>((resolve, reject) => {
      const timer = setTimeout(() => {
        sesion.removeListener('will-download', onDescarga)
        reject(new Error(`Timeout interceptor descarga: ${nombreArchivo}`))
      }, timeout)

      const sesion = win.webContents.session

      const onDescarga = (_event: Electron.Event, item: DownloadItem): void => {
        item.setSavePath(rutaDestino)
        item.on('done', (_e, state) => {
          clearTimeout(timer)
          sesion.removeListener('will-download', onDescarga)
          if (state === 'completed') {
            log.info(`[${this.nombre}] PDF descargado via interceptor: ${rutaDestino}`)
            resolve(rutaDestino)
          } else {
            reject(new Error(`Descarga fallida: ${state}`))
          }
        })
      }

      sesion.on('will-download', onDescarga)

      // Interceptar window.open: cancelar apertura y forzar descarga
      win.webContents.setWindowOpenHandler(({ url }) => {
        log.info(`[${this.nombre}] Popup interceptado — descargando URL: ${url}`)
        // downloadURL dispara will-download en la misma sesion
        win.webContents.downloadURL(url)
        return { action: 'deny' }
      })
    })
  }

  /**
   * Escucha will-download en una ventana especifica (popup) con timeout.
   */
  esperarDescargaEnVentana(
    ventana: BrowserWindow,
    nombreArchivo: string,
    timeout = 30_000,
  ): Promise<string> {
    const rutaDestino = join(this.carpetaDescargas, nombreArchivo)
    return new Promise<string>((resolve, reject) => {
      const timer = setTimeout(() => {
        sesion.removeListener('will-download', onDescarga)
        reject(new Error('No hubo descarga en ventana'))
      }, timeout)

      const sesion = ventana.webContents.session
      const onDescarga = (_event: Electron.Event, item: DownloadItem): void => {
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

  /**
   * Maneja login en Seguridad Social via IPCE (certificado electronico).
   * Patron Findiur: click en button[formaction*='seleccion=IPCE']
   */
  async manejarLoginSS(timeoutPostLogin = 30_000): Promise<boolean> {
    if (!this.window || this.window.isDestroyed()) return false

    // Buscar boton IPCE (certificado electronico)
    const clicIpce = await this.ejecutarJs<boolean>(`
      (function() {
        var btn = document.querySelector("button[formaction*='seleccion=IPCE']");
        if (btn) { btn.click(); return true; }
        // Fallback: boton con texto "Certificado" o "IPCE"
        var botones = document.querySelectorAll('button, input[type=submit]');
        for (var i = 0; i < botones.length; i++) {
          var t = (botones[i].textContent || botones[i].value || '').toLowerCase();
          if (t.includes('certificado') || t.includes('ipce')) {
            botones[i].click();
            return true;
          }
        }
        return false;
      })()
    `)

    if (!clicIpce) {
      log.warn(`[${this.nombre}] Boton IPCE no encontrado`)
      return false
    }

    log.info(`[${this.nombre}] Login SS via IPCE iniciado`)

    // Esperar redireccion post-login
    const urlAntes = this.window.webContents.getURL()
    const inicio = Date.now()
    while (Date.now() - inicio < timeoutPostLogin) {
      const urlActual = this.window.webContents.getURL()
      if (urlActual !== urlAntes && !urlActual.includes('Login')) {
        log.info(`[${this.nombre}] Login SS completado: ${urlActual}`)
        break
      }
      await this.delay(500)
    }

    await this.delay(3000)
    return true
  }

  /**
   * Patron Carpeta Ciudadana: cookies → identificarse Cl@ve → proteccion datos → navegar
   */
  async loginCarpetaCiudadana(seccionUrl: string): Promise<void> {
    if (!this.window || this.window.isDestroyed()) {
      throw new Error('Navegador no inicializado')
    }

    // 1. Navegar a Carpeta Ciudadana
    await this.navegar('https://carpetaciudadana.gob.es/')
    await this.delay(2000)

    // 2. Aceptar cookies
    await this.cerrarModalSiExiste('button.cc-boton-aceptar')
    await this.delay(500)

    // 3. Click en "Identificate con Cl@ve" (dos posibles selectores)
    const clicAcceso = await this.ejecutarJs<boolean>(`
      (function() {
        var btn = document.querySelector("button.botonIdentificateClave[onclick*='redirect']");
        if (btn) { btn.click(); return true; }
        btn = document.querySelector('#botonIdentificateClave');
        if (btn) { btn.click(); return true; }
        return false;
      })()
    `)

    if (!clicAcceso) {
      throw new Error('Boton de acceso Cl@ve no encontrado en Carpeta Ciudadana')
    }

    // 4. Manejar pasarela Cl@ve
    await this.delay(2000)
    const loginOk = await this.manejarPasarelaClave(15_000, 30_000)
    if (!loginOk) {
      throw new Error('Login Cl@ve en Carpeta Ciudadana fallo')
    }

    // 5. Esperar carga post-login
    await this.esperarSelector('main', 15_000)
    await this.delay(2000)

    // 6. Aceptar terminos proteccion datos si aparecen
    await this.ejecutarJs<void>(`
      (function() {
        // Navegar a pagina de proteccion datos si existe enlace
        var enlace = document.querySelector('a[href*="proteccionDatos"]');
        if (enlace) enlace.click();
      })()
    `).catch(() => { /* puede no existir */ })
    await this.delay(1000)

    // Aceptar si hay botones de condiciones
    await this.ejecutarJs<void>(`
      (function() {
        var btns = document.querySelectorAll('#botonesCondiciones button');
        if (btns.length >= 2) btns[1].click();
        else if (btns.length === 1) btns[0].click();
      })()
    `).catch(() => { /* puede no existir */ })
    await this.delay(1000)

    // 7. Navegar a la seccion solicitada
    await this.navegar(`https://carpetaciudadana.gob.es${seccionUrl}`)
    await this.delay(3000)

    log.info(`[${this.nombre}] Carpeta Ciudadana lista en ${seccionUrl}`)
  }
}
