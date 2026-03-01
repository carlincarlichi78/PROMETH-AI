import { BrowserWindow, session, type Certificate } from 'electron'
import { join } from 'path'
import { mkdirSync, existsSync, writeFileSync } from 'fs'
import { app } from 'electron'
import log from 'electron-log'
import type { ResultadoScraping, ConfigScraping } from './tipos'
import { CONFIG_DEFAULT } from './tipos'

const DELAY_BASE_RETRY = 5_000 // 5s base para backoff exponencial

/** User agents para rotacion (mismo patron que Findiur) */
const USER_AGENTS = [
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0',
]

/**
 * Clase base abstracta para todos los scrapers.
 * Metodologia identica a Findiur BaseScrapper.ts:
 * - BrowserWindow con session aislada por particion temporal
 * - select-client-certificate para autenticacion automatica
 * - loadUrlAndHandleRedirects con eventos did-finish-load/did-fail-load/did-redirect-navigation
 * - GLOBAL_TIMEOUT con Promise.race
 * - Limpieza completa de session al cerrar (cookies, localStorage, indexDB, etc.)
 * - Tracking de ventanas hijas (popups)
 */
export abstract class BaseScraper {
  protected window: BrowserWindow | null = null
  private childWindows: BrowserWindow[] = []

  readonly serialNumber: string
  readonly config: ConfigScraping
  readonly carpetaDescargas: string

  constructor(serialNumber: string, config?: Partial<ConfigScraping>) {
    this.serialNumber = serialNumber
    this.config = { ...CONFIG_DEFAULT, ...config }

    // Carpeta de descargas por certificado (usa nombre legible si disponible)
    const baseDescargas =
      this.config.carpetaDescargas ||
      join(app.getPath('documents'), 'CertiGestor', 'descargas')
    const subcarpeta = this.config.nombreCarpeta || serialNumber
    this.carpetaDescargas = join(baseDescargas, subcarpeta)

    if (!existsSync(this.carpetaDescargas)) {
      mkdirSync(this.carpetaDescargas, { recursive: true })
    }
  }

  /**
   * Nombre descriptivo del scraper para logs y UI.
   */
  abstract get nombre(): string

  /**
   * Logica especifica del scraper. Debe ser implementada por cada scraper.
   */
  abstract ejecutar(): Promise<ResultadoScraping>

  /**
   * Inicializa BrowserWindow con session temporal y seleccion automatica
   * de certificado. Replica exacta del patron de Findiur BaseScrapper.initializeBrowser().
   */
  async inicializarNavegador(): Promise<void> {
    const particion = `scraper-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
    const sesionTemp = session.fromPartition(particion, { cache: false })

    // Limpiar cache de autenticacion para forzar nueva seleccion de certificado
    // Sin esto, Electron puede reutilizar el cert de una sesion anterior
    await sesionTemp.clearAuthCache()
    await sesionTemp.clearStorageData()

    this.window = new BrowserWindow({
      width: 1280,
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

    // Seleccion automatica de certificado por serialNumber exacto
    // (mismo patron que Findiur BaseScrapper.ts lineas 200-216)
    const targetSerial = this.serialNumber.toLowerCase()

    // Titulo visible con el certificado objetivo para diagnostico
    this.window.setTitle(`[CertiGestor] Cert: ${this.serialNumber}`)

    this.window.webContents.on(
      'select-client-certificate',
      (event, _url, certificateList: Certificate[], callback) => {
        event.preventDefault()
        log.info(
          `[${this.nombre}] === SELECT-CLIENT-CERTIFICATE ===`,
        )
        log.info(
          `[${this.nombre}] URL: ${_url}`,
        )
        log.info(
          `[${this.nombre}] Buscando serial: ${targetSerial}`,
        )
        log.info(
          `[${this.nombre}] Certificados disponibles (${certificateList.length}):`,
        )
        for (const c of certificateList) {
          const esTarget = c.serialNumber.toLowerCase() === targetSerial ? ' <<<< TARGET' : ''
          log.info(`  - ${c.serialNumber} | ${c.subjectName}${esTarget}`)
        }

        const seleccionado = certificateList.find(
          (cert) => cert.serialNumber.toLowerCase() === targetSerial,
        )
        if (seleccionado) {
          log.info(`[${this.nombre}] SELECCIONADO: ${seleccionado.serialNumber} — ${seleccionado.subjectName}`)
          if (this.window && !this.window.isDestroyed()) {
            this.window.setTitle(`[CertiGestor] ${seleccionado.subjectName}`)
          }
          callback(seleccionado)
        } else {
          // NUNCA seleccionar otro cert — cancelar la peticion
          log.error(`[${this.nombre}] CERT ${targetSerial} NO ENCONTRADO — CANCELANDO (no se seleccionara otro)`)
          log.error(`[${this.nombre}] Seriales disponibles: ${certificateList.map(c => c.serialNumber.toLowerCase()).join(', ')}`)
          callback(null as unknown as Certificate)
        }
      },
    )

    // Tracking de ventanas hijas (popups) — patron Findiur
    this.childWindows = []
    this.configurarVentana(this.window, userAgent, sesionTemp)

    log.info(`[${this.nombre}] BrowserWindow iniciado — cert: ${this.serialNumber} — headless: ${this.config.headless}`)
  }

  /**
   * Configura will-download y tracking de popups en una ventana.
   * Se aplica recursivamente: cada popup nuevo tambien queda configurado.
   * Asi se interceptan descargas en cualquier nivel de profundidad (ventana → popup → popup del popup).
   */
  private sesionesConWillDownload = new Set<string>()

  private configurarVentana(
    ventana: BrowserWindow,
    userAgent: string,
    sesion: Electron.Session,
  ): void {
    // Registrar will-download en la sesion (solo una vez por sesion unica)
    const sesionId = sesion.storagePath ?? `session-${ventana.id}`
    if (!this.sesionesConWillDownload.has(sesionId)) {
      this.sesionesConWillDownload.add(sesionId)
      sesion.on('will-download', (_event, item) => {
        const nombreArchivo = item.getFilename()
        const rutaDestino = join(this.carpetaDescargas, nombreArchivo)
        item.setSavePath(rutaDestino)
        log.info(`[${this.nombre}] Descargando (ventana ${ventana.id}): ${nombreArchivo} → ${rutaDestino}`)

        item.once('done', (_ev, state) => {
          if (state === 'completed') {
            log.info(`[${this.nombre}] Descarga completada (ventana ${ventana.id}): ${nombreArchivo}`)
          } else {
            log.warn(`[${this.nombre}] Descarga fallida (ventana ${ventana.id}): ${nombreArchivo} — estado: ${state}`)
          }
        })
      })
    }

    // Tracking de popups + configuracion recursiva
    ventana.webContents.on('did-create-window', (childWindow) => {
      log.info(`[${this.nombre}] Popup creado desde ventana ${ventana.id}: nuevo ID ${childWindow.id}`)
      this.childWindows.push(childWindow)

      if (this.config.headless && childWindow.isVisible()) {
        childWindow.hide()
      }
      childWindow.webContents.setUserAgent(userAgent)

      // Recursivo: configurar will-download + tracking en el popup tambien
      const sesionPopup = childWindow.webContents.session
      this.configurarVentana(childWindow, userAgent, sesionPopup)

      childWindow.on('closed', () => {
        this.childWindows = this.childWindows.filter(
          (win) => win !== childWindow && !win.isDestroyed(),
        )
      })
    })
  }

  /**
   * Cierra el navegador con limpieza completa de session.
   * Replica Findiur BaseScrapper.closeBrowser() — limpia cookies, localStorage, indexDB, etc.
   */
  async cerrarNavegador(): Promise<void> {
    // Cerrar ventanas hijas primero (patron Findiur)
    if (this.childWindows.length > 0) {
      log.info(`[${this.nombre}] Cerrando ${this.childWindows.length} ventana(s) secundaria(s)`)
      for (const win of this.childWindows) {
        if (win && !win.isDestroyed()) {
          win.removeAllListeners()
          win.close()
        }
      }
      this.childWindows = []
    }

    if (this.window && !this.window.isDestroyed()) {
      try {
        // Limpieza completa de session (patron Findiur)
        const currentSession = this.window.webContents.session
        await currentSession.clearStorageData({
          storages: [
            'cookies', 'filesystem', 'indexdb', 'localstorage',
            'shadercache', 'websql', 'serviceworkers', 'cachestorage',
          ],
        }).catch((err) =>
          log.warn(`[${this.nombre}] Error menor limpiando storage: ${err.message}`),
        )

        this.window.removeAllListeners()
        this.window.webContents.removeAllListeners()
        this.window.close()
        log.info(`[${this.nombre}] Navegador cerrado y sesion limpiada`)
      } catch (error) {
        const msg = error instanceof Error ? error.message : String(error)
        log.warn(`[${this.nombre}] Error menor cerrando navegador: ${msg}`)
      } finally {
        this.window = null
      }
    }
  }

  /**
   * Ejecuta una funcion con reintentos y backoff exponencial.
   */
  async ejecutarConReintento<T>(
    fn: () => Promise<T>,
    maxReintentos?: number,
  ): Promise<T> {
    const intentos = maxReintentos ?? this.config.maxReintentos

    for (let intento = 0; intento < intentos; intento++) {
      try {
        return await fn()
      } catch (error) {
        const esUltimoIntento = intento === intentos - 1
        if (esUltimoIntento) throw error

        const delay = DELAY_BASE_RETRY * Math.pow(2, intento)
        log.warn(
          `[${this.nombre}] Intento ${intento + 1}/${intentos} fallido, reintentando en ${delay}ms`,
        )
        await new Promise((resolve) => setTimeout(resolve, delay))
      }
    }

    throw new Error('Se agotaron los reintentos')
  }

  /**
   * Espera a que un elemento aparezca en la pagina.
   * Polling con executeJavaScript (mismo patron que Findiur waitForSelector).
   */
  async esperarElemento(
    selector: string,
    timeout?: number,
  ): Promise<void> {
    if (!this.window || this.window.isDestroyed()) throw new Error('Navegador no inicializado')
    const ms = timeout ?? this.config.timeoutElemento
    const inicio = Date.now()

    return new Promise<void>((resolve, reject) => {
      const check = async () => {
        if (!this.window || this.window.isDestroyed()) {
          return reject(new Error('Ventana destruida durante la espera'))
        }
        if (Date.now() - inicio > ms) {
          return reject(new Error(`Timeout esperando selector: ${selector}`))
        }
        try {
          const encontrado = await this.window.webContents.executeJavaScript(
            `!!document.querySelector('${selector.replace(/'/g, "\\'")}')`,
          )
          if (encontrado) return resolve()
          setTimeout(check, 500)
        } catch {
          setTimeout(check, 500)
        }
      }
      check()
    })
  }

  /**
   * Navega a una URL y espera a que cargue con manejo de redirecciones.
   * Replica Findiur loadUrlAndHandleRedirects() — usa eventos did-finish-load,
   * did-fail-load y did-redirect-navigation con timeout.
   */
  async navegar(url: string): Promise<void> {
    if (!this.window || this.window.isDestroyed()) throw new Error('Navegador no inicializado')
    log.info(`[${this.nombre}] Navegando a: ${url}`)
    await this.loadUrlAndHandleRedirects(this.window, url)
    log.info(`[${this.nombre}] Navegacion completada. URL final: ${this.window.webContents.getURL()}`)
  }

  /**
   * Carga una URL con manejo robusto de redirecciones.
   * Replica exacta de Findiur BaseScrapper.loadUrlAndHandleRedirects():
   * - Listener did-finish-load → resuelve
   * - Listener did-fail-load → rechaza (excepto ERR_ABORTED que indica redireccion)
   * - Listener did-redirect-navigation → reinicia temporizador
   * - Timeout general de navegacion
   */
  private loadUrlAndHandleRedirects(window: BrowserWindow, url: string): Promise<void> {
    return new Promise((resolve, reject) => {
      const wc = window.webContents
      if (wc.isDestroyed()) {
        return reject(new Error('WebContents destruido antes de la navegacion'))
      }

      let isDone = false
      let navigationTimer: ReturnType<typeof setTimeout>

      const cleanup = () => {
        if (navigationTimer) clearTimeout(navigationTimer)
        if (!wc.isDestroyed()) {
          wc.removeListener('did-finish-load', onFinish)
          wc.removeListener('did-fail-load', onFail)
          wc.removeListener('did-redirect-navigation', onRedirect)
        }
      }

      const succeed = () => {
        if (isDone) return
        isDone = true
        cleanup()
        resolve()
      }

      const fail = (error: Error) => {
        if (isDone) return
        isDone = true
        cleanup()
        reject(error)
      }

      const onFinish = () => {
        log.info(`[${this.nombre}] did-finish-load: ${wc.getURL()}`)
        succeed()
      }

      const onFail = (_event: unknown, errorCode: number, errorDescription: string) => {
        // ERR_ABORTED (-3) es normal durante redirecciones, ignorar
        if (errorCode === -3) {
          log.info(`[${this.nombre}] Carga abortada (ERR_ABORTED), esperando redireccion...`)
          return
        }
        fail(new Error(`Fallo de carga: ${errorDescription} (codigo: ${errorCode})`))
      }

      const onRedirect = () => {
        log.info(`[${this.nombre}] Redireccion detectada. Reiniciando temporizador.`)
        if (navigationTimer) clearTimeout(navigationTimer)
        navigationTimer = setTimeout(
          () => fail(new Error('Timeout despues de redireccion')),
          45_000,
        )
      }

      wc.on('did-finish-load', onFinish)
      wc.on('did-fail-load', onFail)
      wc.on('did-redirect-navigation', onRedirect)

      // Timeout general de navegacion
      navigationTimer = setTimeout(
        () => fail(new Error('Timeout general de navegacion')),
        this.config.timeoutGlobal,
      )

      // Iniciar carga — ERR_ABORTED es esperado en redirecciones
      window.loadURL(url).catch((error: { code?: string; message?: string }) => {
        if (error.code === 'ERR_ABORTED') return
        fail(new Error(error.message ?? 'Error cargando URL'))
      })
    })
  }

  /**
   * Navega a una URL con reintentos (3 intentos).
   * Replica Findiur BaseScrapper.loadURLWithRetries().
   */
  async navegarConReintentos(url: string, maxReintentos = 3): Promise<void> {
    if (!this.window || this.window.isDestroyed()) throw new Error('Navegador no inicializado')

    for (let intento = 1; intento <= maxReintentos; intento++) {
      try {
        log.info(`[${this.nombre}] Intento ${intento}/${maxReintentos} de cargar: ${url}`)
        await this.loadUrlAndHandleRedirects(this.window, url)
        log.info(`[${this.nombre}] Carga exitosa en intento ${intento}`)
        return
      } catch (error) {
        const msg = error instanceof Error ? error.message : String(error)
        log.error(`[${this.nombre}] Intento ${intento} fallido: ${msg}`)

        if (this.window && !this.window.isDestroyed()) {
          try { this.window.webContents.stop() } catch { /* ignorar */ }
        }

        if (intento === maxReintentos) {
          throw new Error(`Fallo al cargar ${url} tras ${maxReintentos} intentos: ${msg}`)
        }

        await this.esperar(2000 * intento)
      }
    }
  }

  /**
   * Ejecuta JavaScript en la pagina.
   */
  async ejecutarJS<T>(script: string): Promise<T> {
    if (!this.window || this.window.isDestroyed()) throw new Error('Navegador no inicializado')
    return this.window.webContents.executeJavaScript(script) as Promise<T>
  }

  /**
   * Hace clic en un elemento por selector CSS.
   * Con verificacion previa de existencia (patron Findiur clickElementBySelector).
   */
  async clic(selector: string): Promise<boolean> {
    if (!this.window || this.window.isDestroyed()) throw new Error('Navegador no inicializado')
    const clicked = await this.window.webContents.executeJavaScript(`
      (function() {
        const el = document.querySelector('${selector.replace(/'/g, "\\'")}');
        if (el) { el.click(); return true; }
        return false;
      })()
    `)
    return clicked as boolean
  }

  /**
   * Hace clic en un elemento esperando que aparezca primero.
   * Replica Findiur clickElementBySelector (waitForSelector + click).
   */
  async clicConEspera(selector: string, timeout?: number): Promise<void> {
    await this.esperarElemento(selector, timeout)
    const clicked = await this.clic(selector)
    if (!clicked) {
      throw new Error(`No se pudo hacer clic en: ${selector}`)
    }
  }

  /**
   * Obtiene el HTML de la pagina actual.
   */
  async obtenerHTML(): Promise<string> {
    if (!this.window || this.window.isDestroyed()) throw new Error('Navegador no inicializado')
    return this.window.webContents.executeJavaScript(
      'document.documentElement.outerHTML',
    ) as Promise<string>
  }

  /**
   * Obtiene la URL actual.
   */
  obtenerURL(): string {
    if (!this.window || this.window.isDestroyed()) throw new Error('Navegador no inicializado')
    return this.window.webContents.getURL()
  }

  /**
   * Espera un tiempo determinado.
   */
  async esperar(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms))
  }

  /**
   * Detecta y maneja la pasarela Cl@ve (pasarela.clave.gob.es).
   * Version mejorada que usa selectedIdP('AFIRMA') como en Findiur,
   * ademas de busqueda por texto como fallback.
   *
   * @param timeoutDeteccion - ms para esperar a que aparezca la pasarela (default 10s)
   * @param timeoutPostLogin - ms para esperar redireccion tras seleccion de cert (default 30s)
   * @returns true si paso por Cl@ve, false si no se detecto
   */
  async manejarPasarelaClave(
    timeoutDeteccion = 10_000,
    timeoutPostLogin = 30_000,
  ): Promise<boolean> {
    if (!this.window || this.window.isDestroyed()) return false

    const inicio = Date.now()

    // Esperar a que la URL sea de Cl@ve o timeout
    while (Date.now() - inicio < timeoutDeteccion) {
      const url = this.obtenerURL()

      if (url.includes('pasarela.clave.gob.es') || url.includes('clave.gob.es')) {
        log.info(`[${this.nombre}] Pasarela Cl@ve detectada: ${url}`)

        // Esperar a que cargue la pagina
        await this.esperar(2000)

        // Estrategia 1 (Findiur): Usar selectedIdP('AFIRMA') si existe
        const usadoSelectedIdP = await this.ejecutarJS<boolean>(`
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
          log.info(`[${this.nombre}] selectedIdP('AFIRMA') ejecutado exitosamente`)
        } else {
          // Estrategia 2: Buscar boton con onclick que contenga selectedIdP('AFIRMA')
          const clicBotonAfirma = await this.ejecutarJS<boolean>(`
            (function() {
              const btn = document.querySelector("button[onclick*=\\"selectedIdP('AFIRMA')\\"]");
              if (btn) { btn.click(); return true; }
              return false;
            })()
          `)

          if (clicBotonAfirma) {
            log.info(`[${this.nombre}] Clic en boton AFIRMA por selector`)
          } else {
            // Estrategia 3 (fallback): Buscar por texto "certificado" o "dnie"
            const clicTexto = await this.ejecutarJS<boolean>(`
              (function() {
                const botones = document.querySelectorAll('article button, button, a.btn');
                for (const btn of botones) {
                  const texto = (btn.textContent || '').toLowerCase();
                  if (texto.includes('certificado') || texto.includes('dnie') || texto.includes('afirma')) {
                    btn.click();
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
              await this.capturarPantalla('clave-sin-boton-cert')
              return false
            }
          }
        }

        // Esperar redireccion post-autenticacion
        const urlClave = this.obtenerURL()
        try {
          await this.esperarRedireccion(urlClave, timeoutPostLogin)
          log.info(`[${this.nombre}] Redireccion post-Cl@ve completada: ${this.obtenerURL()}`)
        } catch {
          log.warn(`[${this.nombre}] Timeout esperando redireccion post-Cl@ve`)
          await this.capturarPantalla('clave-timeout-redireccion')
        }

        await this.esperar(3000)
        return true
      }

      await this.esperar(500)
    }

    return false
  }

  /**
   * Espera a que la URL cambie (redireccion post-login).
   */
  async esperarRedireccion(urlOriginal: string, timeout?: number): Promise<void> {
    if (!this.window || this.window.isDestroyed()) throw new Error('Navegador no inicializado')
    const ms = timeout ?? this.config.timeoutGlobal
    const inicio = Date.now()

    while (Date.now() - inicio < ms) {
      const urlActual = this.window.webContents.getURL()
      if (urlActual !== urlOriginal) return
      await new Promise((resolve) => setTimeout(resolve, 500))
    }

    throw new Error(`Timeout esperando redireccion desde ${urlOriginal}`)
  }

  /**
   * Captura screenshot para debug.
   */
  async capturarPantalla(nombre: string): Promise<string> {
    if (!this.window || this.window.isDestroyed()) throw new Error('Navegador no inicializado')
    const ruta = join(this.carpetaDescargas, `${nombre}.png`)
    const imagen = await this.window.webContents.capturePage()
    writeFileSync(ruta, imagen.toPNG())
    log.info(`[${this.nombre}] Screenshot guardado: ${ruta}`)
    return ruta
  }

  /**
   * Ejecuta el scraper completo con GLOBAL_TIMEOUT via Promise.race.
   * Replica Findiur BaseScrapper.run() — Promise.race entre scrape y timeout.
   * El timer se cancela cuando el scrape termina (exito o error).
   */
  async run(): Promise<ResultadoScraping> {
    let timeoutHandle: ReturnType<typeof setTimeout> | null = null

    const timeoutPromise = new Promise<never>((_, reject) => {
      timeoutHandle = setTimeout(() => {
        const msg = `Timeout global de ${this.config.timeoutGlobal / 1000}s excedido para ${this.nombre}`
        log.error(`[${this.nombre}] ${msg}`)
        reject(new Error(msg))
      }, this.config.timeoutGlobal)
    })

    const scrapePromise = async (): Promise<ResultadoScraping> => {
      try {
        await this.inicializarNavegador()
        return await this.ejecutar()
      } catch (error) {
        const mensaje = error instanceof Error ? error.message : 'Error desconocido'
        log.error(`[${this.nombre}] Error en run:`, mensaje)
        try {
          await this.capturarPantalla('error')
        } catch {
          // Ignorar error de screenshot
        }
        return { exito: false, error: mensaje }
      }
    }

    try {
      return await Promise.race([scrapePromise(), timeoutPromise])
    } catch (error) {
      const mensaje = error instanceof Error ? error.message : 'Error desconocido'
      return { exito: false, error: mensaje }
    } finally {
      // Cancelar el timeout para evitar que siga corriendo despues de terminar
      if (timeoutHandle) clearTimeout(timeoutHandle)
      await this.cerrarNavegador()
    }
  }
}
