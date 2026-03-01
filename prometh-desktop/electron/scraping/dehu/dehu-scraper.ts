import log from 'electron-log'
import { join } from 'path'
import { writeFileSync } from 'fs'
import { BaseScraper } from '../base-scraper'
import type { ResultadoScraping, ConfigScraping } from '../tipos'
import {
  MetodoConsulta,
  type NotificacionDEHU,
  type ResultadoConsultaDEHU,
  type ConfigCertificadoDehu,
  EstadoAltaDehu,
} from './tipos-dehu'

/**
 * URL directa a notificaciones pendientes de DEHU.
 * Findiur usa exactamente esta URL: https://dehu.redsara.es/es/notifications
 */
const URL_DEHU_NOTIFICACIONES = 'https://dehu.redsara.es/es/notifications'

/**
 * Timeout global de 5 minutos para DEHU (igual que Findiur: GLOBAL_TIMEOUT = 300000).
 * DEHU es un portal lento que necesita tiempo extra.
 */
const GLOBAL_TIMEOUT_DEHU = 300_000

/**
 * Scraper BrowserWindow para el portal web de DEHU.
 * Replica exacta de la metodologia de Findiur DehuUnifiedScraper.ts:
 *
 * Flujo:
 * 1. Navegar a https://dehu.redsara.es/es/notifications
 * 2. Esperar a que aparezca app-public-view
 * 3. Hacer clic en dnt-button.access-btn (boton "Acceder" dentro de Shadow DOM)
 * 4. Esperar pagina de login Cl@ve — usar selectedIdP('AFIRMA') para seleccionar certificado
 * 5. select-client-certificate se dispara automaticamente
 * 6. Esperar redireccion y carga de app-home-view o dnt-sidebar
 * 7. Navegar a /es/notifications → extraer pendientes
 * 8. Navegar a /es/notifications?realized=true → extraer realizadas
 * 9. Navegar a /es/communications → extraer comunicaciones
 *
 * DEHU usa Web Components con Shadow DOM extensivamente:
 * - dnt-table tiene shadowRoot con tr.dnt-table__row
 * - td[data-label] con contenido en shadowRoot interno
 * - Filas de expansion para datos adicionales (concepto, fechas)
 */
export class DehuScraper extends BaseScraper {
  private readonly configDehu: ConfigCertificadoDehu

  /** Token capturado via interceptor de red (mas fiable que localStorage) */
  private tokenInterceptado: string | null = null

  constructor(
    configDehu: ConfigCertificadoDehu,
    configScraping?: Partial<ConfigScraping>,
  ) {
    super(configDehu.certificadoSerial, {
      ...configScraping,
      // DEHU necesita 5 minutos como Findiur
      timeoutGlobal: GLOBAL_TIMEOUT_DEHU,
      // Ventana visible para diagnostico — DEHU es lento y complejo
      headless: false,
    })
    this.configDehu = configDehu
  }

  get nombre(): string {
    return `DEHU (${this.serialNumber})`
  }

  /**
   * Ejecuta el scraping completo del portal DEHU.
   * Replica DehuUnifiedScraper.scrape() de Findiur.
   */
  async ejecutar(): Promise<ResultadoScraping> {
    log.info(`[${this.nombre}] Iniciando scraping DEHU web (metodologia Findiur)`)

    // PASO 1: LOGIN — hasta 3 intentos (igual que Findiur)
    const loggedIn = await this.intentarLogin(3)
    if (!loggedIn) {
      return {
        exito: false,
        error: 'No se pudo iniciar sesion en DEHU',
      }
    }

    // PASO 2: Seleccionar entidad empresa si hay CIF configurado
    await this.seleccionarEntidadEmpresa()

    // PASO 3: Extraer datos de las 3 secciones
    const pendientes = await this.extraerSeccion(
      'PENDIENTES',
      URL_DEHU_NOTIFICACIONES,
      'app-notifications-list',
      'dnt-table',
    )

    const realizadas = await this.extraerSeccion(
      'REALIZADAS',
      'https://dehu.redsara.es/es/notifications?realized=true',
      'app-notifications-list',
      '#tablaNotificacionesRealizadas',
    )

    const comunicaciones = await this.extraerSeccion(
      'COMUNICACIONES',
      'https://dehu.redsara.es/es/communications',
      'app-communications-list-view',
      '#tablaComunicaciones',
    )

    const todasNotificaciones = [...pendientes, ...realizadas, ...comunicaciones]
    log.info(
      `[${this.nombre}] Total: ${todasNotificaciones.length} (${pendientes.length} pend + ${realizadas.length} real + ${comunicaciones.length} comun)`,
    )

    // Construir resultado
    const resultado: ResultadoConsultaDEHU = {
      exito: true,
      metodo: MetodoConsulta.PUPPETEER,
      certificadoSerial: this.configDehu.certificadoSerial,
      estadoAlta: EstadoAltaDehu.NO_ALTA,
      notificaciones: todasNotificaciones.filter((n) => n.tipo === 'Notificacion'),
      comunicaciones: todasNotificaciones.filter((n) => n.tipo === 'Comunicacion'),
      fechaConsulta: new Date().toISOString(),
    }

    return {
      exito: true,
      datos: resultado,
    }
  }

  /**
   * Proceso de login con reintentos.
   * Flujo: DEHU public → click Acceder → Cl@ve pasarela → cert → DEHU autenticado.
   *
   * Deteccion basada en URL (no en selectores fragiles como 'main'):
   * 1. Navegar a DEHU, verificar si ya estamos logueados
   * 2. Click Acceder → esperar navegacion fuera de DEHU
   * 3. En Cl@ve: selectedIdP('AFIRMA') → select-client-certificate
   * 4. Esperar redireccion de vuelta a DEHU autenticado
   */
  private async intentarLogin(maxIntentos: number): Promise<boolean> {
    for (let intento = 1; intento <= maxIntentos; intento++) {
      try {
        log.info(`[${this.nombre}] Intento login ${intento}/${maxIntentos}`)

        // PASO 1: Navegar a DEHU
        await this.navegarConReintentos(URL_DEHU_NOTIFICACIONES)
        await this.esperar(3000)

        // Verificar si ya estamos logueados (sesion previa o redireccion auto)
        const yaLogueado = await this.verificarSesionActiva()
        if (yaLogueado) {
          log.info(`[${this.nombre}] Ya autenticado en DEHU`)
          return true
        }

        // PASO 2: Buscar y click boton Acceder
        await this.esperarElemento('app-public-view', 15_000)
        await this.esperar(2000)

        const clickedAcceder = await this.ejecutarJS<boolean>(`
          (function() {
            var dntBtn = document.querySelector('dnt-button.access-btn');
            if (dntBtn) {
              if (dntBtn.shadowRoot && dntBtn.shadowRoot.querySelector('button')) {
                dntBtn.shadowRoot.querySelector('button').click();
              } else {
                dntBtn.click();
              }
              return true;
            }
            return false;
          })()
        `)

        if (!clickedAcceder) {
          throw new Error('No se encontro boton Acceder en DEHU')
        }

        log.info(`[${this.nombre}] Boton Acceder clickeado, esperando navegacion...`)
        await this.esperar(5000)

        // PASO 3: Detectar donde estamos tras el click
        const urlPostClick = this.window ? this.obtenerURL() : ''
        log.info(`[${this.nombre}] URL post-click: ${urlPostClick}`)

        if (urlPostClick.includes('clave.gob.es')) {
          // Estamos en Cl@ve — manejar autenticacion
          log.info(`[${this.nombre}] Pasarela Cl@ve detectada`)
          const pasoClave = await this.manejarPasarelaClave(5_000, 45_000)
          if (!pasoClave) {
            throw new Error('Cl@ve pasarela no pudo completar autenticacion')
          }
        } else if (urlPostClick.includes('dehu.redsara.es')) {
          // Puede que ya estemos autenticados (cert auto-seleccionado rapido)
          const logueadoPost = await this.verificarSesionActiva()
          if (logueadoPost) {
            log.info(`[${this.nombre}] Login exitoso (auto-cert rapido)`)
            return true
          }
          // Aun en DEHU sin autenticar, esperar un poco mas
          await this.esperar(5000)
          const urlSegunda = this.window ? this.obtenerURL() : ''
          if (urlSegunda.includes('clave.gob.es')) {
            const pasoClave = await this.manejarPasarelaClave(5_000, 45_000)
            if (!pasoClave) {
              throw new Error('Cl@ve pasarela no pudo completar autenticacion (2do intento)')
            }
          }
        } else {
          // URL desconocida — puede ser pasarela intermediaria
          log.info(`[${this.nombre}] URL desconocida post-click, intentando Cl@ve`)
          const pasoClave = await this.manejarPasarelaClave(15_000, 45_000)
          if (!pasoClave) {
            // Comprobar si por casualidad ya estamos autenticados
            const logueadoFinal = await this.verificarSesionActiva()
            if (logueadoFinal) {
              log.info(`[${this.nombre}] Login exitoso tras URL desconocida`)
              return true
            }
            throw new Error(`URL inesperada post-login: ${urlPostClick}`)
          }
        }

        // PASO 4: Esperar vista autenticada de DEHU
        await this.esperar(3000)

        // Verificar con polling — DEHU puede tardar en cargar la vista autenticada
        const autenticado = await this.esperarSesionActiva(30_000)
        if (autenticado) {
          log.info(`[${this.nombre}] Login exitoso`)
          return true
        }

        throw new Error('No se detecto vista autenticada tras login')
      } catch (error) {
        const msg = error instanceof Error ? error.message : String(error)
        log.warn(`[${this.nombre}] Intento login ${intento} fallido: ${msg}`)
        try { await this.capturarPantalla(`dehu_login_fail_${intento}`) } catch { /* ignorar */ }
        if (intento < maxIntentos) {
          await this.esperar(3000)
        }
      }
    }

    return false
  }

  /**
   * Verifica si hay sesion activa en DEHU (usuario logueado).
   * Comprueba multiples indicadores: header usuario, sidebar, home view.
   */
  private async verificarSesionActiva(): Promise<boolean> {
    if (!this.window || this.window.isDestroyed()) return false
    try {
      return await this.ejecutarJS<boolean>(`
        (function() {
          return !!(
            document.querySelector('dnt-header-item[type="user"]') ||
            document.querySelector('app-home-view') ||
            document.querySelector('dnt-sidebar') ||
            document.querySelector('app-notifications-list')
          );
        })()
      `)
    } catch {
      return false
    }
  }

  /**
   * Espera con polling a que haya sesion activa en DEHU.
   */
  private async esperarSesionActiva(timeout: number): Promise<boolean> {
    const inicio = Date.now()
    while (Date.now() - inicio < timeout) {
      // Verificar que seguimos en DEHU
      if (this.window && !this.window.isDestroyed()) {
        const url = this.obtenerURL()
        if (url.includes('dehu.redsara.es')) {
          const activa = await this.verificarSesionActiva()
          if (activa) return true
        }
      }
      await this.esperar(1000)
    }
    return false
  }

  /**
   * Extrae notificaciones de una seccion especifica de DEHU.
   * Replica DehuUnifiedScraper pasos 2-4.
   */
  private async extraerSeccion(
    tipo: 'PENDIENTES' | 'REALIZADAS' | 'COMUNICACIONES',
    url: string,
    viewSelector: string,
    tableSelector: string,
  ): Promise<NotificacionDEHU[]> {
    try {
      log.info(`[${this.nombre}] Extrayendo ${tipo}...`)
      await this.navegarConReintentos(url)

      // Esperar componente de vista
      await this.esperarElemento(viewSelector, 20_000)

      // Para REALIZADAS: el SPA puede no activar la pestaña via URL
      // Hacer click en la pestaña "Notificaciones realizadas" para asegurar
      if (tipo === 'REALIZADAS') {
        await this.clickPestanaRealizadas()
      }

      // Esperar tabla (puede no existir si no hay datos)
      const hayTabla = await this.waitForTable(tableSelector, 10000)
      if (!hayTabla) {
        log.info(`[${this.nombre}] ${tipo}: sin tabla visible`)
        return []
      }

      await this.esperar(4000)

      // Extraer datos via Shadow DOM (replica exacta de Findiur extractNotificationsData)
      const rawResults = await this.extractNotificationsData(tipo, tableSelector)
      log.info(`[${this.nombre}] ${tipo}: ${rawResults.length} resultados`)
      return rawResults
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error)
      log.error(`[${this.nombre}] Error extrayendo ${tipo}: ${msg}`)
      return []
    }
  }

  /**
   * Hace click en la pestaña "Notificaciones realizadas" del SPA DEHU.
   * Necesario porque la navegacion por URL no siempre activa la pestaña.
   */
  private async clickPestanaRealizadas(): Promise<void> {
    if (!this.window || this.window.isDestroyed()) return

    try {
      await this.ejecutarJS<boolean>(`
        (function() {
          // Buscar tab "Notificaciones realizadas" por rol o texto
          var tabs = document.querySelectorAll('[role="tab"]');
          for (var i = 0; i < tabs.length; i++) {
            if (tabs[i].textContent && tabs[i].textContent.includes('realizadas')) {
              tabs[i].click();
              return true;
            }
          }
          // Fallback: buscar por texto en cualquier elemento clickeable
          var links = document.querySelectorAll('a, button, [role="tab"], li');
          for (var j = 0; j < links.length; j++) {
            var text = links[j].textContent || '';
            if (text.toLowerCase().includes('notificaciones realizadas')) {
              links[j].click();
              return true;
            }
          }
          return false;
        })()
      `)
      await this.esperar(2000)
      log.info(`[${this.nombre}] Click en pestaña "Notificaciones realizadas"`)
    } catch (error) {
      log.warn(`[${this.nombre}] No se pudo hacer click en pestaña realizadas: ${error}`)
    }
  }

  /**
   * Click en tab "Notificaciones pendientes" — SPA navigation sin recargar pagina.
   * CRITICO: NO usar navegarConReintentos() porque rompe la sesion TLS.
   */
  private async clickPestanaPendientes(): Promise<void> {
    if (!this.window || this.window.isDestroyed()) return

    try {
      await this.ejecutarJS<boolean>(`
        (function() {
          var tabs = document.querySelectorAll('[role="tab"]');
          for (var i = 0; i < tabs.length; i++) {
            var texto = (tabs[i].textContent || '').toLowerCase();
            if (texto.includes('pendiente')) {
              tabs[i].click();
              return true;
            }
          }
          // Fallback: buscar por texto en cualquier elemento clickeable
          var links = document.querySelectorAll('a, button, [role="tab"], li');
          for (var j = 0; j < links.length; j++) {
            var text = (links[j].textContent || '').toLowerCase();
            if (text.includes('notificaciones pendientes')) {
              links[j].click();
              return true;
            }
          }
          return false;
        })()
      `)
      await this.esperar(2000)
      log.info(`[${this.nombre}] Click en pestaña "Notificaciones pendientes"`)
    } catch (error) {
      log.warn(`[${this.nombre}] No se pudo hacer click en pestaña pendientes: ${error}`)
    }
  }

  /**
   * Espera a que la tabla tenga al menos 1 fila de datos (no solo el skeleton/loading).
   * Util despues de cambiar tab — el SPA hace una API call que puede tardar.
   * onBeforeRequest ya ha modificado los parametros (publicId + fecha extendida).
   */
  private async esperarTablaConDatos(tableSelector: string, timeout: number): Promise<number> {
    if (!this.window || this.window.isDestroyed()) return 0

    const inicio = Date.now()
    let ultimoConteo = 0

    while (Date.now() - inicio < timeout) {
      try {
        const filas = await this.ejecutarJS<number>(`
          (function() {
            var table = document.querySelector('${tableSelector.replace(/'/g, "\\'")}');
            if (!table || !table.shadowRoot) return 0;
            var rows = table.shadowRoot.querySelectorAll('tr.dnt-table__row');
            var dataRows = Array.from(rows).filter(function(r) {
              return !r.classList.contains('dnt-table__row-expansion');
            });
            return dataRows.length;
          })()
        `)

        ultimoConteo = filas
        if (filas > 0) {
          log.info(`[${this.nombre}] Tabla cargada con ${filas} filas en ${Date.now() - inicio}ms`)
          return filas
        }
      } catch { /* ignorar */ }
      await this.esperar(500)
    }

    log.warn(`[${this.nombre}] Timeout ${timeout}ms esperando datos en tabla. Ultimo conteo: ${ultimoConteo}`)
    return ultimoConteo
  }

  /**
   * Click en enlace "Notificaciones" del nav superior del SPA.
   * Navegacion interna Angular (history.pushState) — NO recarga la pagina.
   */
  private async clickNavNotificaciones(): Promise<void> {
    if (!this.window || this.window.isDestroyed()) return
    try {
      await this.ejecutarJS<boolean>(`
        (function() {
          // Buscar enlace en la barra de navegacion superior
          var links = document.querySelectorAll('a[href*="/notifications"], a[routerLink*="/notifications"]');
          for (var i = 0; i < links.length; i++) {
            var text = (links[i].textContent || '').toLowerCase();
            if (text.includes('notificacion')) {
              links[i].click();
              return true;
            }
          }
          // Fallback: buscar en nav items
          var navItems = document.querySelectorAll('nav a, .nav-item a, dnt-sidebar a, [role="navigation"] a');
          for (var j = 0; j < navItems.length; j++) {
            var href = navItems[j].getAttribute('href') || '';
            if (href.includes('/notifications')) {
              navItems[j].click();
              return true;
            }
          }
          return false;
        })()
      `)
      await this.esperar(2000)
      log.info(`[${this.nombre}] Click nav "Notificaciones"`)
    } catch (err) {
      log.warn(`[${this.nombre}] No se pudo click nav Notificaciones: ${err}`)
    }
  }

  /**
   * Click en enlace "Comunicaciones" del nav superior del SPA.
   * Navegacion interna Angular (history.pushState) — NO recarga la pagina.
   */
  private async clickNavComunicaciones(): Promise<void> {
    if (!this.window || this.window.isDestroyed()) return
    try {
      await this.ejecutarJS<boolean>(`
        (function() {
          var links = document.querySelectorAll('a[href*="/communications"], a[routerLink*="/communications"]');
          for (var i = 0; i < links.length; i++) {
            var text = (links[i].textContent || '').toLowerCase();
            if (text.includes('comunicacion')) {
              links[i].click();
              return true;
            }
          }
          var navItems = document.querySelectorAll('nav a, .nav-item a, dnt-sidebar a, [role="navigation"] a');
          for (var j = 0; j < navItems.length; j++) {
            var href = navItems[j].getAttribute('href') || '';
            if (href.includes('/communications')) {
              navItems[j].click();
              return true;
            }
          }
          return false;
        })()
      `)
      await this.esperar(2000)
      log.info(`[${this.nombre}] Click nav "Comunicaciones"`)
    } catch (err) {
      log.warn(`[${this.nombre}] No se pudo click nav Comunicaciones: ${err}`)
    }
  }

  /**
   * Espera a que una tabla sea visible (con offset > 0).
   * Replica DehuUnifiedScraper.waitForTable().
   */
  private async waitForTable(tableSelector: string, timeout: number): Promise<boolean> {
    if (!this.window || this.window.isDestroyed()) return false

    return await this.ejecutarJS<boolean>(`
      new Promise((resolve) => {
        var startTime = Date.now();
        var check = function() {
          var table = document.querySelector('${tableSelector.replace(/'/g, "\\'")}');
          if (table && (table.offsetHeight > 0 || table.getClientRects().length > 0)) return resolve(true);
          if (Date.now() - startTime > ${timeout}) return resolve(false);
          setTimeout(check, 200);
        };
        check();
      })
    `)
  }

  /**
   * Extrae datos de notificaciones de la tabla DEHU usando Shadow DOM.
   * Replica EXACTA de Findiur DehuUnifiedScraper.extractNotificationsData().
   * DEHU usa Web Components con shadowRoot — no se pueden leer con querySelector normal.
   */
  private async extractNotificationsData(
    type: 'PENDIENTES' | 'REALIZADAS' | 'COMUNICACIONES',
    tableSelector: string,
  ): Promise<NotificacionDEHU[]> {
    if (!this.window || this.window.isDestroyed()) return []

    const rawResults = await this.ejecutarJS<Array<{
      id: string
      titulo: string
      titular: string
      ambito: string
      disposicion: string
      estado: string
      tipo: string
      fechaLeida: string | null
    } | null>>(`
      (async function(type, tableSelector) {
        try {
          var sleep = function(ms) { return new Promise(function(r) { setTimeout(r, ms); }); };
          var attempts = 0;
          var table = null;

          while (attempts < 20) {
            table = document.querySelector(tableSelector);
            if (table && table.shadowRoot) break;
            await sleep(300);
            attempts++;
          }

          if (!table || !table.shadowRoot) return [];

          var allRows = Array.from(
            table.shadowRoot.querySelectorAll('tr.dnt-table__row')
          );

          var mainRows = allRows.filter(function(r) {
            return !r.classList.contains('dnt-table__row-expansion');
          });

          if (mainRows.length === 0) return [];

          return mainRows.map(function(row) {
            try {
              var getCell = function(label) {
                var td = row.querySelector('td[data-label="' + label + '"]');
                if (!td) return null;
                if (td.shadowRoot) {
                  var inner = td.shadowRoot.querySelector('.dnt-table__cell-content');
                  return inner ? inner.innerText.trim() : td.innerText.trim();
                }
                return td.innerText.trim();
              };

              var id = getCell('Identificador');
              var titular = getCell('Titular');
              var ambito = getCell('Organismo emisor');
              var estadoText = getCell('Estado');

              // FECHA DISPOSICION — logica exacta de Findiur
              var disposicion = '';
              var fechaDispCell = getCell('Fecha disposición');
              if (fechaDispCell) disposicion = fechaDispCell;

              var nextRow = row.nextElementSibling;
              var isExpansion = nextRow && nextRow.classList.contains('dnt-table__row-expansion');

              if ((!disposicion || disposicion === '') && isExpansion) {
                var ps = Array.from(nextRow.querySelectorAll('p'));
                var labelP = ps.find(function(p) { return p.innerText.includes('Fecha disposición'); });
                if (labelP) {
                  if (labelP.nextSibling && labelP.nextSibling.nodeType === Node.TEXT_NODE) {
                    var text = labelP.nextSibling.textContent.trim();
                    var match = text.match(/(\\d{2})[\\/-](\\d{2})[\\/-](\\d{4})/);
                    if (match) disposicion = match[0];
                  }
                  if (!disposicion && labelP.parentElement) {
                    var fullText = labelP.parentElement.innerText;
                    var parts = fullText.split('Fecha disposición');
                    if (parts.length > 1) {
                      var textAfterLabel = parts[1];
                      var match2 = textAfterLabel.match(/(\\d{2})[\\/-](\\d{2})[\\/-](\\d{4})/);
                      if (match2) disposicion = match2[0];
                    }
                  }
                }
              }

              // Normalizar DD-MM-YYYY
              if (disposicion) {
                var matchNorm = disposicion.match(/(\\d{2})[\\/-](\\d{2})[\\/-](\\d{4})/);
                if (matchNorm) {
                  disposicion = matchNorm[1] + '-' + matchNorm[2] + '-' + matchNorm[3];
                }
              }

              // TITULO / CONCEPTO desde expansion
              var titulo = '';
              var fechaLeida = null;
              var isLeida = false;

              if (nextRow && nextRow.classList.contains('dnt-table__row-expansion')) {
                var labels = Array.from(nextRow.querySelectorAll('.dnt-txt-body-350'));
                var conceptoLabel = labels.find(function(el) { return el.innerText.trim() === 'Concepto'; });
                if (conceptoLabel) {
                  var valueEl = conceptoLabel.nextElementSibling;
                  if (valueEl) titulo = valueEl.innerText.trim();
                }
                if (type === 'COMUNICACIONES') {
                  var leidaLabel = labels.find(function(el) { return el.innerText.trim() === 'Fecha leída'; });
                  if (leidaLabel) {
                    var containerText = leidaLabel.parentElement ? leidaLabel.parentElement.innerText : '';
                    var matchLeida = containerText.match(/(\\d{2})[\\/-](\\d{2})[\\/-](\\d{4})/);
                    if (matchLeida) fechaLeida = matchLeida[1] + '-' + matchLeida[2] + '-' + matchLeida[3];
                  }
                }
              }

              if (!titulo) {
                var td = row.querySelector('td[data-label="Organismo emisor"]');
                if (td && td.shadowRoot) {
                  var content = td.shadowRoot.querySelector('.dnt-table__cell-content');
                  var original = content ? content.getAttribute('data-original-text-concept') : null;
                  if (original) titulo = original.trim();
                }
              }
              if (!titulo) titulo = ambito || 'Sin titulo';

              // ESTADO — logica exacta de Findiur
              var estadoFinal = 'Pendiente';
              var tipoNotif = 'Notificacion';

              if (type === 'PENDIENTES') {
                estadoFinal = 'Pendiente de abrir';
              } else if (type === 'REALIZADAS') {
                estadoFinal = estadoText || 'Abierta Externamente';
              } else if (type === 'COMUNICACIONES') {
                tipoNotif = 'Comunicacion';
                if (fechaLeida || (estadoText && estadoText.toLowerCase().includes('leída'))) {
                  estadoFinal = 'Archivada';
                  isLeida = true;
                } else {
                  estadoFinal = 'Pendiente de abrir';
                }
              }

              return {
                id: id,
                titulo: titulo,
                titular: titular,
                ambito: ambito,
                disposicion: disposicion,
                estado: estadoFinal,
                tipo: tipoNotif,
                fechaLeida: fechaLeida
              };
            } catch (rowErr) {
              return null;
            }
          });
        } catch (e) {
          return [];
        }
      })('${type}', '${tableSelector.replace(/'/g, "\\'")}')
    `)

    if (!rawResults || !Array.isArray(rawResults)) return []

    // Convertir a NotificacionDEHU
    const notificaciones: NotificacionDEHU[] = []
    for (const raw of rawResults) {
      if (!raw || !raw.id) continue

      notificaciones.push({
        idDehu: raw.id,
        tipo: raw.tipo as 'Notificacion' | 'Comunicacion',
        titulo: raw.titulo,
        titular: raw.titular || this.serialNumber,
        ambito: raw.ambito || '',
        organismo: raw.ambito || 'DEHU',
        fechaDisposicion: this.normalizarFecha(raw.disposicion),
        fechaCaducidad: null,
        estado: raw.estado,
        rutaPdfLocal: null,
      })
    }

    return notificaciones
  }

  /**
   * Configura un interceptor de red para capturar el token Bearer
   * que el SPA DEHU usa en sus peticiones API internas.
   *
   * El SPA Angular almacena el token en memoria (no en localStorage).
   * La unica forma fiable de obtenerlo es interceptar las peticiones
   * HTTP que el propio SPA hace al cargar la pagina de notificaciones.
   *
   * @returns Funcion de limpieza para desactivar el interceptor
   */
  private configurarInterceptorToken(): () => void {
    if (!this.window || this.window.isDestroyed()) return () => {}

    const webSession = this.window.webContents.session
    this.tokenInterceptado = null

    // Capturar Bearer token de las API calls que el SPA hace al navegar.
    // NO usamos onBeforeRequest (causa loops infinitos y filtra resultados).
    webSession.webRequest.onBeforeSendHeaders(
      { urls: ['*://dehu.redsara.es/*'] },
      (details, callback) => {
        if (details.url.includes('/api/')) {
          const auth = details.requestHeaders['Authorization'] ||
                       details.requestHeaders['authorization']
          if (auth && auth.startsWith('Bearer ')) {
            if (!this.tokenInterceptado) {
              this.tokenInterceptado = auth.replace(/^Bearer\s+/i, '')
              log.info(`[${this.nombre}] Token interceptado: ${this.tokenInterceptado.substring(0, 40)}...`)
            }
          }
        }
        callback({ requestHeaders: details.requestHeaders })
      },
    )

    return () => {
      try {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        webSession.webRequest.onBeforeSendHeaders(null as any)
      } catch { /* session puede estar destruida */ }
    }
  }

  /**
   * Ejecuta login + descarga de PDF para una notificacion.
   * Punto de entrada publico para el IPC handler — maneja el ciclo
   * completo: inicializar navegador, login, descarga, cierre.
   */
  async runDescargarPdf(notificacion: NotificacionDEHU): Promise<string | null> {
    let timeoutHandle: ReturnType<typeof setTimeout> | null = null

    const timeoutPromise = new Promise<never>((_, reject) => {
      timeoutHandle = setTimeout(() => {
        reject(new Error(`Timeout global descarga PDF (${this.config.timeoutGlobal / 1000}s)`))
      }, this.config.timeoutGlobal)
    })

    const descargarPromise = async (): Promise<string | null> => {
      await this.inicializarNavegador()
      const loggedIn = await this.intentarLogin(3)
      if (!loggedIn) {
        throw new Error('No se pudo iniciar sesion en DEHU (login fallido tras 3 intentos)')
      }
      return await this.descargarPdf(notificacion)
    }

    try {
      return await Promise.race([descargarPromise(), timeoutPromise])
    } finally {
      if (timeoutHandle) clearTimeout(timeoutHandle)
      await this.cerrarNavegador()
    }
  }

  /**
   * Descarga el PDF de una notificacion individual.
   * Requiere que el navegador este inicializado y logueado.
   *
   * DEHU tiene TLS session binding: solo requests desde el renderer que hizo
   * el handshake Cl@ve funcionan.
   *
   * API DEHU (de config/env.json):
   *   host: https://dehu.redsara.es/api/
   *   realized: GET v1/realized_notifications/:sentReference/document
   *   pending:  (no hay endpoint /document para pendientes — solo metadata)
   *   comms:    GET v1/communications/:sentReference/document
   *
   * El sentReference ES el idDehu (ej: N276297762), NO un UUID interno.
   * No necesitamos navegar a la pagina de detalle — fetch directo con el idDehu.
   *
   * Flujo v1.0.87:
   * 1. Navegar a DEHU (para que SPA haga API calls → captura token)
   * 2. fetch() directo a /api/v1/{tipo}/{idDehu}/document
   * 3. Fallback: printToPdf de pagina de detalle
   */
  async descargarPdf(
    notificacion: NotificacionDEHU,
  ): Promise<string | null> {
    if (!this.window || this.window.isDestroyed()) {
      throw new Error('Navegador no inicializado o destruido')
    }

    const idDehu = notificacion.idDehu
    log.info(`[${this.nombre}] === DESCARGA PDF v1.0.88 === idDehu=${idDehu}, estado=${notificacion.estado}, tipo=${notificacion.tipo}`)

    // Ruta destino
    const idSanitizado = idDehu.replace(/[^a-zA-Z0-9-_]/g, '_')
    const nombreArchivo = `DEHU_${idSanitizado}.pdf`
    const rutaDestino = join(this.carpetaDescargas, nombreArchivo)

    // Interceptor: captura Bearer token de las API calls del SPA
    const limpiarInterceptor = this.configurarInterceptorToken()

    try {
      // PASO 1: Navegar a notificaciones para que el SPA se inicialice y capture el token
      await this.navegarConReintentos(URL_DEHU_NOTIFICACIONES)
      await this.esperar(3000)

      // Esperar a que el SPA haga al menos una API call (token se captura via onBeforeSendHeaders)
      const tokenListo = await this.esperarToken(15000)
      log.info(`[${this.nombre}] Token capturado: ${tokenListo ? 'SI' : 'NO'}`)

      // PASO 2: Buscar sentReference via API list
      // El identifier (N276297762) NO es el sentReference.
      // Hay que listar notificaciones y buscar la que tiene identifier == idDehu
      // para extraer su sentReference (UUID hex largo).
      const esComunicacion = notificacion.tipo === 'Comunicacion'
      const esPendiente = notificacion.estado === 'Pendiente de abrir' || notificacion.estado === 'Pendiente'

      const sentReference = await this.buscarSentReference(idDehu, esComunicacion, esPendiente)

      if (sentReference) {
        log.info(`[${this.nombre}] [PASO 2] sentReference encontrado: ${sentReference}`)

        // PASO 3: Descargar documento con sentReference
        const urlsProbar: string[] = []
        if (esComunicacion) {
          urlsProbar.push(`/api/v1/communications/${sentReference}/document`)
        } else if (esPendiente) {
          urlsProbar.push(`/api/v1/notifications/${sentReference}/voucher`)
        } else {
          urlsProbar.push(`/api/v1/realized_notifications/${sentReference}/document`)
        }
        // Fallback: probar otros tipos
        if (!esComunicacion) urlsProbar.push(`/api/v1/communications/${sentReference}/document`)
        if (!esPendiente) urlsProbar.push(`/api/v1/notifications/${sentReference}/voucher`)

        for (const apiPath of urlsProbar) {
          log.info(`[${this.nombre}] [PASO 3] Intentando: ${apiPath}`)
          const ok = await this.descargarViaFetchEnPagina(idDehu, apiPath, rutaDestino)
          if (ok) return rutaDestino
        }
      } else {
        log.warn(`[${this.nombre}] [PASO 2] No se encontro sentReference para ${idDehu}`)
      }

      // PASO 4: Fallback — navegar a detalle y printToPdf
      log.info(`[${this.nombre}] [PASO 4] Fallback printToPdf...`)
      const sentRefParaUrl = sentReference || idDehu
      const urlDetalle = esComunicacion
        ? `https://dehu.redsara.es/es/communications/${sentRefParaUrl}`
        : esPendiente
          ? `https://dehu.redsara.es/es/notifications/pending/${sentRefParaUrl}`
          : `https://dehu.redsara.es/es/notifications/realized/${sentRefParaUrl}`

      try {
        await this.navegarConReintentos(urlDetalle)
        await this.esperar(5000)
      } catch (err) {
        log.warn(`[${this.nombre}] No se pudo navegar a detalle: ${err}`)
      }

      const printOk = await this.descargarViaPrintToPdf(rutaDestino)
      if (printOk) return rutaDestino

      throw new Error(`No se pudo descargar PDF de ${idDehu}`)
    } finally {
      limpiarInterceptor()
    }
  }

  /**
   * Espera hasta que el interceptor capture un Bearer token.
   */
  private async esperarToken(timeout: number): Promise<boolean> {
    const inicio = Date.now()
    while (Date.now() - inicio < timeout) {
      if (this.tokenInterceptado) return true
      await this.esperar(500)
    }
    return !!this.tokenInterceptado
  }

  /**
   * Busca el sentReference de una notificacion via API list.
   * El identifier (N276297762) NO es el sentReference — hay que listar y buscar.
   * La API requiere TODOS los params del filtro (incluso vacios) y rango max ~30 dias.
   */
  private async buscarSentReference(
    idDehu: string,
    esComunicacion: boolean,
    esPendiente: boolean,
  ): Promise<string | null> {
    if (!this.window || this.window.isDestroyed()) return null

    const tokenEscapado = this.tokenInterceptado
      ? this.tokenInterceptado.replace(/'/g, "\\'")
      : ''
    const idEscapado = idDehu.replace(/'/g, "\\'")

    // Rango de fechas: ultimos 30 dias (maximo permitido por la API)
    const hoy = new Date()
    const hace30 = new Date(hoy.getTime() - 30 * 24 * 60 * 60 * 1000)
    const formatFecha = (d: Date) => `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}/${d.getFullYear()}`
    const fechaDesde = formatFecha(hace30)
    const fechaHasta = formatFecha(hoy)

    // Determinar endpoint segun tipo
    let listUrl: string
    if (esComunicacion) {
      listUrl = `/api/v1/communications?page=1&limit=50`
    } else if (esPendiente) {
      listUrl = `/api/v1/notifications?page=1&limit=50`
    } else {
      listUrl = `/api/v1/realized_notifications?emitterEntityCode=&state=&publicId=&titularNif=&bondType=&vinculoReceptor=&postalDelivery=&finalDate%5Bleft_date%5D=${encodeURIComponent(fechaDesde)}&finalDate%5Bright_date%5D=${encodeURIComponent(fechaHasta)}&expirationDate%5Bleft_date%5D=&expirationDate%5Bright_date%5D=&page=1&limit=50`
    }

    log.info(`[${this.nombre}] Buscando sentReference de ${idDehu} via: ${listUrl.substring(0, 100)}...`)

    try {
      const resultado = await this.ejecutarJS<{ sentReference: string | null; total: number; error?: string }>(`
        (async function() {
          try {
            var token = '${tokenEscapado}' || null;
            if (!token) {
              var keys = Object.keys(localStorage);
              for (var i = 0; i < keys.length; i++) {
                var val = localStorage.getItem(keys[i]);
                if (val && val.length > 100 && /^eyJ/.test(val)) { token = val; break; }
              }
            }
            if (!token) return { sentReference: null, total: 0, error: 'Sin token' };

            var response = await fetch('${listUrl}', {
              headers: { 'Authorization': 'Bearer ' + token, 'Accept': 'application/json' }
            });
            if (!response.ok) {
              var errText = '';
              try { errText = await response.text(); } catch(e) {}
              return { sentReference: null, total: 0, error: 'HTTP ' + response.status + ': ' + errText.substring(0, 200) };
            }

            var data = await response.json();
            var items = data.items || data.content || [];
            if (!Array.isArray(items)) {
              for (var k in data) {
                if (Array.isArray(data[k])) { items = data[k]; break; }
              }
            }

            for (var idx = 0; idx < items.length; idx++) {
              var item = items[idx];
              if (item.identifier === '${idEscapado}' || item.publicId === '${idEscapado}') {
                return { sentReference: item.sentReference || null, total: items.length };
              }
            }
            return { sentReference: null, total: items.length };
          } catch (e) {
            return { sentReference: null, total: 0, error: e.message || String(e) };
          }
        })()
      `)

      if (resultado.error) {
        log.warn(`[${this.nombre}] buscarSentReference error: ${resultado.error}`)
      }
      if (resultado.sentReference) {
        log.info(`[${this.nombre}] ${idDehu} → sentReference=${resultado.sentReference} (de ${resultado.total} items)`)
      } else {
        log.warn(`[${this.nombre}] ${idDehu} no encontrado en ${resultado.total} items`)
      }
      return resultado.sentReference
    } catch (error) {
      log.error(`[${this.nombre}] buscarSentReference exception: ${error}`)
      return null
    }
  }

  /**
   * Descarga PDF via fetch() en el contexto de la pagina principal (patron Findiur).
   *
   * DEHU tiene TLS session binding: solo requests desde el renderer que hizo
   * el handshake Cl@ve funcionan. fetch() en executeJavaScript es same-origin
   * (dehu.redsara.es → dehu.redsara.es/api) asi que CSP no bloquea.
   *
   * El SPA Angular almacena el Bearer token — lo buscamos en localStorage/sessionStorage.
   * Como fallback usamos el token capturado por onBeforeSendHeaders.
   */
  private async descargarViaFetchEnPagina(
    _idDehu: string,
    apiPath: string,
    rutaDestino: string,
  ): Promise<boolean> {
    if (!this.window || this.window.isDestroyed()) return false

    // Token capturado por interceptor — se pasa al JS como fallback
    const tokenEscapado = this.tokenInterceptado
      ? this.tokenInterceptado.replace(/'/g, "\\'")
      : ''

    log.info(`[${this.nombre}] fetch en pagina: ${apiPath} (token interceptado: ${tokenEscapado ? 'SI' : 'NO'})`)

    try {
      const resultado = await this.ejecutarJS<{ base64?: string; nombre?: string; error?: string; status?: number }>(`
        (async function() {
          try {
            // Buscar Bearer token: interceptado > localStorage > sessionStorage
            var token = '${tokenEscapado}' || null;

            if (!token) {
              var keys = Object.keys(localStorage);
              for (var i = 0; i < keys.length; i++) {
                var val = localStorage.getItem(keys[i]);
                if (val && val.length > 100 && /^eyJ/.test(val)) {
                  token = val;
                  break;
                }
              }
            }

            if (!token) {
              var keys2 = Object.keys(sessionStorage);
              for (var j = 0; j < keys2.length; j++) {
                var val2 = sessionStorage.getItem(keys2[j]);
                if (val2 && val2.length > 100 && /^eyJ/.test(val2)) {
                  token = val2;
                  break;
                }
              }
            }

            if (!token) {
              return { error: 'No se encontro token Bearer' };
            }

            var response = await fetch('${apiPath}', {
              method: 'GET',
              headers: {
                'Authorization': 'Bearer ' + token,
                'Accept': 'application/json'
              }
            });

            if (!response.ok) {
              var errorText = '';
              try { errorText = await response.text(); } catch(e) {}
              return { error: 'HTTP ' + response.status + ': ' + errorText.substring(0, 200), status: response.status };
            }

            var data = await response.json();

            // El SPA Angular devuelve: { documentContent: { content, name, mimeType } }
            // o directamente: { content, name, mimeType }
            var base64 = null;
            var nombre = null;
            if (data.documentContent && data.documentContent.content) {
              base64 = data.documentContent.content;
              nombre = data.documentContent.name || null;
            } else if (data.content) {
              base64 = data.content;
              nombre = data.name || null;
            } else if (data.data) {
              base64 = data.data;
            } else if (data.document) {
              base64 = data.document;
            } else if (data.pdf) {
              base64 = data.pdf;
            }

            if (!base64) {
              return { error: 'JSON sin campo content. Keys: ' + Object.keys(data).join(',') + ' | ' + JSON.stringify(data).substring(0, 300) };
            }

            return { base64: base64, nombre: nombre };
          } catch (e) {
            return { error: e.message || String(e) };
          }
        })()
      `)

      if (resultado.error) {
        log.error(`[${this.nombre}] fetch error (${apiPath}): ${resultado.error}`)
        return false
      }

      if (!resultado.base64) {
        log.error(`[${this.nombre}] fetch sin base64`)
        return false
      }

      if (resultado.nombre) {
        log.info(`[${this.nombre}] Documento nombre del servidor: ${resultado.nombre}`)
      }

      const pdfBuffer = Buffer.from(resultado.base64, 'base64')
      if (pdfBuffer.length < 100) {
        log.error(`[${this.nombre}] PDF demasiado pequeno: ${pdfBuffer.length} bytes`)
        return false
      }

      if (!pdfBuffer.subarray(0, 5).toString('utf-8').startsWith('%PDF')) {
        log.warn(`[${this.nombre}] Buffer no empieza con %PDF, primeros bytes: ${pdfBuffer.subarray(0, 20).toString('hex')}`)
      }

      writeFileSync(rutaDestino, pdfBuffer)
      log.info(`[${this.nombre}] PDF guardado (${pdfBuffer.length} bytes): ${rutaDestino}`)
      return true
    } catch (error) {
      log.error(`[${this.nombre}] Error descargarViaFetchEnPagina: ${error}`)
      return false
    }
  }


  /**
   * Fallback: si la API falla, captura la pagina de detalle como PDF
   * usando printToPdf del webContents de Electron.
   */
  private async descargarViaPrintToPdf(rutaDestino: string): Promise<boolean> {
    if (!this.window || this.window.isDestroyed()) return false

    try {
      const data = await this.window.webContents.printToPDF({
        printBackground: true,
        landscape: false,
      })
      writeFileSync(rutaDestino, data)
      log.info(`[${this.nombre}] Fallback printToPdf guardado (${data.length} bytes): ${rutaDestino}`)
      return true
    } catch (error) {
      log.error(`[${this.nombre}] Fallback printToPdf fallo: ${error}`)
      return false
    }
  }

  /**
   * Diagnostica el contexto de la pagina DEHU tras login.
   * Busca: titular activo, selector de representado, heading, NIF visible.
   * Esto ayuda a identificar si estamos viendo notificaciones del titular correcto.
   */
  private async diagnosticarContextoPagina(): Promise<{
    heading: string
    nifVisible: string
    nifsEnPagina: string[]
    tieneSelectRepresentado: boolean
    filtrosEncontrados: string[]
    textoHeader: string
    tablesCount: number
    filasEnTabla: number
    urlActual: string
  }> {
    if (!this.window || this.window.isDestroyed()) {
      return { heading: 'N/A', nifVisible: 'N/A', nifsEnPagina: [], tieneSelectRepresentado: false, filtrosEncontrados: [], textoHeader: 'N/A', tablesCount: 0, filasEnTabla: 0, urlActual: 'N/A' }
    }

    return await this.ejecutarJS<{
      heading: string
      nifVisible: string
      nifsEnPagina: string[]
      tieneSelectRepresentado: boolean
      filtrosEncontrados: string[]
      textoHeader: string
      tablesCount: number
      filasEnTabla: number
      urlActual: string
    }>(`
      (function() {
        // Heading principal
        var h1 = document.querySelector('h1, h2, .title, [class*="title"]');
        var heading = h1 ? h1.innerText.trim().substring(0, 100) : '';

        // Buscar TODOS los NIF/CIF en texto visible de la pagina
        var bodyText = document.body.innerText || '';
        var nifRegex = /[A-HJ-NP-SUVW]\\d{7}[A-J0-9]|\\d{8}[A-Z]/g;
        var nifsEncontrados = [];
        var match;
        while ((match = nifRegex.exec(bodyText)) !== null) {
          if (nifsEncontrados.indexOf(match[0]) === -1) nifsEncontrados.push(match[0]);
        }
        var nifVisible = nifsEncontrados.length > 0 ? nifsEncontrados[0] : '';

        // Buscar selector de representado/poderdante/titular
        var textosBuscados = ['representad', 'poderdante', 'nombre de', 'actuar como', 'cambiar titular', 'en nombre', 'nif titular'];
        var tieneSelect = false;
        var filtrosInfo = [];

        // Buscar selects, listbox, combobox
        var selectores = document.querySelectorAll('select, [role="listbox"], [role="combobox"], dnt-select, .dropdown, [class*="dropdown"], [class*="selector"], [class*="filter"]');
        for (var s = 0; s < selectores.length; s++) {
          var selText = (selectores[s].textContent || selectores[s].getAttribute('aria-label') || selectores[s].className || '').substring(0, 60);
          filtrosInfo.push('SEL:' + selectores[s].tagName + '[' + selText + ']');
          tieneSelect = true;
        }

        // Buscar inputs de filtro
        var inputs = document.querySelectorAll('input[type="text"], input[type="search"], input:not([type]), dnt-input');
        for (var inp = 0; inp < inputs.length; inp++) {
          var placeholder = inputs[inp].getAttribute('placeholder') || '';
          var name = inputs[inp].getAttribute('name') || '';
          var ariaLabel = inputs[inp].getAttribute('aria-label') || '';
          var id = inputs[inp].id || '';
          filtrosInfo.push('INP:' + inputs[inp].tagName + '[ph=' + placeholder + ',name=' + name + ',aria=' + ariaLabel + ',id=' + id + ']');
        }

        // Buscar botones/links con texto de cambio de titular
        var links = document.querySelectorAll('a, button, [role="button"], dnt-button');
        for (var i = 0; i < links.length; i++) {
          var linkText = (links[i].innerText || links[i].textContent || '').toLowerCase().trim();
          for (var j = 0; j < textosBuscados.length; j++) {
            if (linkText.includes(textosBuscados[j])) {
              tieneSelect = true;
              filtrosInfo.push('BTN:' + links[i].tagName + '[' + linkText.substring(0, 40) + ']');
              break;
            }
          }
        }

        // Buscar labels que contengan texto de filtro
        var labels = document.querySelectorAll('label, .label, [class*="label"]');
        for (var lb = 0; lb < labels.length; lb++) {
          var lblText = (labels[lb].textContent || '').toLowerCase().trim();
          for (var lt = 0; lt < textosBuscados.length; lt++) {
            if (lblText.includes(textosBuscados[lt])) {
              filtrosInfo.push('LBL:[' + lblText.substring(0, 40) + ']');
              break;
            }
          }
        }

        // Texto del header (sidebar/navbar) — incluir usuario/entidad
        var headerEl = document.querySelector('dnt-header, dnt-sidebar, nav, header, [class*="header"]');
        var textoHeader = headerEl ? headerEl.innerText.trim().substring(0, 300) : '';

        // Contar tablas dnt-table
        var tablesCount = document.querySelectorAll('dnt-table').length;

        // Contar filas en la primera tabla visible
        var filasEnTabla = 0;
        var primeraTabla = document.querySelector('dnt-table');
        if (primeraTabla && primeraTabla.shadowRoot) {
          filasEnTabla = primeraTabla.shadowRoot.querySelectorAll('tr.dnt-table__row').length;
        }

        return {
          heading: heading,
          nifVisible: nifVisible,
          nifsEnPagina: nifsEncontrados.slice(0, 5),
          tieneSelectRepresentado: tieneSelect,
          filtrosEncontrados: filtrosInfo.slice(0, 15),
          textoHeader: textoHeader,
          tablesCount: tablesCount,
          filasEnTabla: filasEnTabla,
          urlActual: window.location.href,
        };
      })()
    `)
  }

  /**
   * Selecciona la entidad empresa en DEHU tras login.
   * Cuando el certificado representa a una persona juridica (empresa), DEHU muestra
   * por defecto las notificaciones del titular personal (DNI). Esta funcion usa el
   * filtro "En nombre de" / "NIF titular" para cambiar a la entidad empresa (CIF).
   *
   * Estrategias:
   * 1. Buscar input/select "En nombre de" o "NIF titular" → establecer CIF
   * 2. Buscar dnt-select/dropdown con opciones de entidad → seleccionar por CIF
   * 3. Buscar link/boton de cambio de entidad en header → click + seleccionar
   *
   * @returns true si se cambio la entidad, false si no fue necesario o no se encontro
   */
  private async seleccionarEntidadEmpresa(): Promise<boolean> {
    const cifEmpresa = this.configDehu.nifEmpresa
    if (!cifEmpresa) {
      log.info(`[${this.nombre}] Sin CIF empresa configurado, usando entidad por defecto`)
      return false
    }

    if (!this.window || this.window.isDestroyed()) return false

    log.info(`[${this.nombre}] Intentando seleccionar entidad empresa: ${cifEmpresa}`)

    // Esperar a que la pagina cargue completamente tras login
    await this.esperar(2000)

    // ESTRATEGIA 1: Buscar filtro de busqueda avanzada / filtros visibles
    const resultadoFiltro = await this.ejecutarJS<{
      estrategia: string
      exito: boolean
      detalle: string
    }>(`
      (function() {
        var CIF = '${cifEmpresa}';

        // Helper: disparar eventos de input en un elemento
        function dispararEventosInput(el) {
          el.dispatchEvent(new Event('input', { bubbles: true }));
          el.dispatchEvent(new Event('change', { bubbles: true }));
          el.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true }));
        }

        // Helper: buscar en Shadow DOMs recursivamente
        function querySelectorDeep(selector) {
          var result = document.querySelector(selector);
          if (result) return result;
          var allHosts = document.querySelectorAll('*');
          for (var i = 0; i < allHosts.length; i++) {
            if (allHosts[i].shadowRoot) {
              var found = allHosts[i].shadowRoot.querySelector(selector);
              if (found) return found;
            }
          }
          return null;
        }

        // Helper: buscar todos los inputs (incluyendo Shadow DOM)
        function encontrarTodosInputs() {
          var inputs = Array.from(document.querySelectorAll('input, select, dnt-input, dnt-select'));
          var allHosts = document.querySelectorAll('*');
          for (var i = 0; i < allHosts.length; i++) {
            if (allHosts[i].shadowRoot) {
              var shadowInputs = allHosts[i].shadowRoot.querySelectorAll('input, select');
              inputs = inputs.concat(Array.from(shadowInputs));
            }
          }
          return inputs;
        }

        // ---- Estrategia 1: Buscar input/label "En nombre de" o "NIF" ----
        var labels = document.querySelectorAll('label, .label, [class*="label"], span, p');
        for (var i = 0; i < labels.length; i++) {
          var txt = (labels[i].textContent || '').toLowerCase();
          if (txt.includes('en nombre de') || txt.includes('nif titular') || txt.includes('nif del titular')) {
            // Buscar input asociado: por for=, siguiente hermano, o hijo
            var inputId = labels[i].getAttribute('for');
            var input = inputId ? document.getElementById(inputId) : null;
            if (!input) input = labels[i].querySelector('input, select');
            if (!input) input = labels[i].nextElementSibling;
            if (input && (input.tagName === 'INPUT' || input.tagName === 'SELECT')) {
              input.value = CIF;
              input.focus();
              dispararEventosInput(input);
              return { estrategia: 'label-input', exito: true, detalle: 'Label: ' + txt.substring(0, 50) };
            }
          }
        }

        // ---- Estrategia 2: Buscar dnt-select o select con opciones de entidad ----
        var selects = document.querySelectorAll('select, dnt-select, [role="listbox"], [role="combobox"]');
        for (var j = 0; j < selects.length; j++) {
          var sel = selects[j];
          var opciones = sel.querySelectorAll('option, [role="option"]');
          for (var k = 0; k < opciones.length; k++) {
            var optText = (opciones[k].textContent || '').toUpperCase();
            if (optText.includes(CIF)) {
              if (sel.tagName === 'SELECT') {
                sel.value = opciones[k].value || opciones[k].textContent;
                dispararEventosInput(sel);
              } else {
                opciones[k].click();
              }
              return { estrategia: 'select-opcion', exito: true, detalle: 'Opcion: ' + optText.substring(0, 50) };
            }
          }
        }

        // ---- Estrategia 3: Buscar input de busqueda general y escribir CIF ----
        var inputsBusqueda = encontrarTodosInputs();
        for (var m = 0; m < inputsBusqueda.length; m++) {
          var inp = inputsBusqueda[m];
          var placeholder = (inp.getAttribute('placeholder') || '').toLowerCase();
          var name = (inp.getAttribute('name') || '').toLowerCase();
          var ariaLabel = (inp.getAttribute('aria-label') || '').toLowerCase();
          if (placeholder.includes('nif') || placeholder.includes('nombre') || placeholder.includes('buscar') ||
              name.includes('nif') || name.includes('titular') ||
              ariaLabel.includes('nif') || ariaLabel.includes('nombre') || ariaLabel.includes('titular')) {
            if (inp.shadowRoot) {
              var innerInput = inp.shadowRoot.querySelector('input');
              if (innerInput) {
                innerInput.value = CIF;
                innerInput.focus();
                dispararEventosInput(innerInput);
                return { estrategia: 'input-busqueda-shadow', exito: true, detalle: 'Input: ' + (placeholder || name || ariaLabel) };
              }
            }
            inp.value = CIF;
            inp.focus();
            dispararEventosInput(inp);
            return { estrategia: 'input-busqueda', exito: true, detalle: 'Input: ' + (placeholder || name || ariaLabel) };
          }
        }

        // ---- Estrategia 4: Buscar dnt-header-item con menu de usuario/entidad ----
        var headerItems = document.querySelectorAll('dnt-header-item, [class*="user"], [class*="entity"]');
        var entidadInfo = [];
        for (var n = 0; n < headerItems.length; n++) {
          var txt2 = (headerItems[n].textContent || '');
          entidadInfo.push(txt2.substring(0, 60));
          // Si tiene un link/boton para cambiar entidad
          var changeBtn = headerItems[n].querySelector('a, button, [role="button"]');
          if (changeBtn) {
            var btnText = (changeBtn.textContent || '').toLowerCase();
            if (btnText.includes('cambiar') || btnText.includes('representad') || btnText.includes('entidad')) {
              changeBtn.click();
              return { estrategia: 'header-cambiar', exito: true, detalle: 'Boton: ' + btnText };
            }
          }
        }

        // No se encontro filtro — recopilar info diagnostica
        var allInputsInfo = [];
        var allInputs = encontrarTodosInputs();
        for (var p = 0; p < Math.min(allInputs.length, 10); p++) {
          allInputsInfo.push(allInputs[p].tagName + '[' +
            (allInputs[p].getAttribute('placeholder') || allInputs[p].getAttribute('name') || allInputs[p].getAttribute('aria-label') || allInputs[p].className || '') + ']');
        }

        return {
          estrategia: 'ninguna',
          exito: false,
          detalle: 'inputs=' + allInputsInfo.join('; ') + ' | header=' + entidadInfo.join('; ')
        };
      })()
    `)

    log.info(`[${this.nombre}] Seleccion entidad: estrategia=${resultadoFiltro.estrategia} exito=${resultadoFiltro.exito} detalle=${resultadoFiltro.detalle}`)

    if (resultadoFiltro.exito) {
      // Esperar a que se aplique el filtro y se recargue la tabla
      await this.esperar(3000)

      // Buscar y hacer click en boton de buscar/aplicar si existe
      try {
        await this.ejecutarJS<void>(`
          (function() {
            var botones = document.querySelectorAll('button, dnt-button, [role="button"], input[type="submit"]');
            for (var i = 0; i < botones.length; i++) {
              var texto = (botones[i].textContent || '').toLowerCase();
              if (texto.includes('buscar') || texto.includes('filtrar') || texto.includes('aplicar') || texto.includes('search')) {
                if (botones[i].shadowRoot) {
                  var innerBtn = botones[i].shadowRoot.querySelector('button');
                  if (innerBtn) { innerBtn.click(); return; }
                }
                botones[i].click();
                return;
              }
            }
            // Fallback: submit del form mas cercano
            var forms = document.querySelectorAll('form');
            if (forms.length > 0) {
              forms[0].dispatchEvent(new Event('submit', { bubbles: true }));
            }
          })()
        `)
        await this.esperar(3000)
      } catch {
        // No hay boton de buscar — el filtro puede aplicarse automaticamente
      }

      // Capturar screenshot post-filtro
      try { await this.capturarPantalla('dehu_05_post_filtro_entidad') } catch { /* ignorar */ }

      log.info(`[${this.nombre}] Filtro entidad empresa aplicado`)
      return true
    }

    // Si no se encontro filtro, intentar agregar NIF como parametro en la URL
    if (this.window && !this.window.isDestroyed()) {
      const urlActual = await this.ejecutarJS<string>('window.location.href')
      // Solo si estamos en la pagina de notificaciones
      if (urlActual.includes('/notifications') && !urlActual.includes('nifTitular=')) {
        const urlConFiltro = urlActual.includes('?')
          ? `${urlActual}&nifTitular=${cifEmpresa}`
          : `${urlActual}?nifTitular=${cifEmpresa}`

        log.info(`[${this.nombre}] Intentando filtro por URL: ${urlConFiltro}`)
        await this.navegarConReintentos(urlConFiltro)
        await this.esperar(5000)
        try { await this.capturarPantalla('dehu_05_post_url_filtro') } catch { /* ignorar */ }
      }
    }

    return false
  }


  private normalizarFecha(fecha: string): string {
    if (!fecha) return new Date().toISOString()
    // DD-MM-YYYY o DD/MM/YYYY → ISO
    const partes = fecha.match(/(\d{2})[-/](\d{2})[-/](\d{4})/)
    if (partes) {
      return new Date(
        `${partes[3]}-${partes[2]}-${partes[1]}T00:00:00.000Z`,
      ).toISOString()
    }
    try {
      return new Date(fecha).toISOString()
    } catch {
      return new Date().toISOString()
    }
  }
}
