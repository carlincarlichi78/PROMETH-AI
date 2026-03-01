import log from 'electron-log'
import { BaseScraperNotificaciones } from '../base-scraper-notificaciones'
import { PortalNotificaciones } from '../tipos-notificaciones'
import type { NotificacionPortal } from '../tipos-notificaciones'
import type { ConfigScraping } from '../../tipos'

/**
 * URL de acceso directo a "Consultar y firmar notificaciones telematicas".
 * Redirige automaticamente al portal de login (idp.seg-social.es/PGIS/Login).
 * Tras autenticacion con certificado, vuelve al listado de notificaciones.
 */
const URL_NOTIFICACIONES =
  'https://sede.seg-social.gob.es/wps/portal/sede/Seguridad/PortalRedirectorN2A?idApp=323&idContenido=7a65cc68-f663-4b4f-bbdb-82dba341160f&idPagina=com.ss.sede.NotificacionesTelematicas&N2&A'

/**
 * Selectores CSS para la pasarela de login y la tabla de notificaciones.
 *
 * Flujo:
 * 1. Redireccion a idp.seg-social.es/PGIS/Login
 * 2. Click en boton "DNIe o certificado" (#IPCEIdP)
 * 3. Seleccion automatica del certificado (BrowserWindow + select-client-certificate)
 * 4. Redireccion al listado de notificaciones
 * 5. Extraccion de filas de la tabla
 */
const SELECTORES = {
  /** Boton de login con certificado en la pasarela de autenticacion */
  botonCertificado: 'button#IPCEIdP, button[formaction*="IPCE"]',

  /** Indicador post-login: elementos que solo aparecen autenticado */
  indicadorLogin:
    '.nombre-usuario, .datos-usuario, #contenidoPrincipal, .breadcrumb, #mainContent',

  /** Tabla de notificaciones — contenedor principal */
  tablaNotificaciones:
    'table.tablaDatos, table.tabla-notificaciones, #tablaNotificaciones, .resultado-consulta table, table[summary*="notificacion"], table.tablaListadoPaginada',

  /** Filas de datos en la tabla */
  filasTabla:
    'table.tablaDatos tbody tr, table.tabla-notificaciones tbody tr, #tablaNotificaciones tbody tr, table.tablaListadoPaginada tbody tr',

  /**
   * Indicador de que no hay notificaciones.
   * En la UI real de SS dice "No existen notificaciones puestas a su disposición"
   */
  sinResultados:
    '.sin-notificaciones, .no-resultados, .mensaje-vacio, #mensajeVacio, .msgInfo',

  /** Formulario de seleccion (nombre propio vs apoderado) */
  selectorTipo: 'select[name*="tipo"], select[name*="representacion"]',
}

const TIMEOUT_LOGIN = 30_000
const TIMEOUT_REDIRECCION = 20_000
const TIMEOUT_TABLA = 15_000

/**
 * Scraper de notificaciones telematicas de la Seguridad Social.
 *
 * Portal: sede.seg-social.gob.es
 * Servicio: "Consultar y firmar notificaciones telematicas"
 * Auth: certificado electronico via pasarela idp.seg-social.es o Cl@ve
 *
 * Columnas de la tabla:
 * 1. Prestacion/procedimiento
 * 2. Materia
 * 3. Fecha puesta a disposicion
 * 4. Destinatario
 * 5. Estado
 * 6. Fecha/hora vencimiento
 */
export class ScraperSeguridadSocial extends BaseScraperNotificaciones {
  protected readonly urlPortal = URL_NOTIFICACIONES
  protected readonly portal = PortalNotificaciones.SEGURIDAD_SOCIAL

  constructor(serialNumber: string, configScraping?: Partial<ConfigScraping>) {
    // SS necesita mas tiempo — login tiene muchas redirecciones
    super(serialNumber, { ...configScraping, timeoutGlobal: 120_000 })
  }

  get nombre(): string {
    return 'SS-Notificaciones'
  }

  protected async ejecutarConsulta(): Promise<NotificacionPortal[]> {
    // 1. Navegar a la URL del servicio (redirige a pasarela login)
    log.info(`[${this.nombre}] Navegando a sede SS...`)
    await this.navegar(this.urlPortal)
    await this.esperar(3000) // Esperar redirecciones iniciales

    // 2. Autenticar con certificado
    await this.autenticarConCertificado()

    // 3. Esperar a que cargue la pagina de notificaciones
    await this.esperarPaginaNotificaciones()

    // 4. Verificar si hay notificaciones (por selector CSS o por texto real)
    const haySinResultados = await this.ejecutarJS<boolean>(`
      (function() {
        var selectoresVacio = '${SELECTORES.sinResultados.replace(/'/g, "\\\\'")}';
        if (document.querySelector(selectoresVacio)) return true;
        var bodyText = document.body ? document.body.innerText : '';
        if (bodyText.includes('No existen notificaciones')) return true;
        return false;
      })()
    `)
    if (haySinResultados) {
      log.info(`[${this.nombre}] Sin notificaciones pendientes — portal SS funciona correctamente`)
      return []
    }

    // 5. Extraer notificaciones de la tabla
    return this.extraerNotificaciones()
  }

  /**
   * Autenticacion via pasarela idp.seg-social.es o Cl@ve.
   *
   * Flujo posible 1: SS → idp.seg-social.es → clic #IPCEIdP → select-client-certificate → redirect
   * Flujo posible 2: SS → pasarela.clave.gob.es → selectedIdP('AFIRMA') → select-client-certificate → redirect
   * Flujo posible 3: SS → idp.seg-social.es → clic #IPCEIdP → pasarela.clave.gob.es → selectedIdP('AFIRMA') → redirect
   */
  private async autenticarConCertificado(): Promise<void> {
    if (!this.window) throw new Error('Navegador no inicializado')

    const urlActual = this.obtenerURL()
    log.info(`[${this.nombre}] URL actual: ${urlActual}`)

    // Caso 1: Estamos en pasarela Cl@ve directamente
    if (urlActual.includes('pasarela.clave.gob.es') || urlActual.includes('clave.gob.es')) {
      log.info(`[${this.nombre}] Redirigido a Cl@ve directamente`)
      await this.manejarPasarelaClave(5_000, TIMEOUT_REDIRECCION)
      await this.esperar(3000)
      log.info(`[${this.nombre}] Post-Cl@ve URL: ${this.obtenerURL()}`)
      return
    }

    // Caso 2: Estamos en pasarela SS (idp.seg-social.es)
    const enPasarelaSS =
      urlActual.includes('idp.seg-social.es') ||
      urlActual.includes('PGIS/Login')

    if (enPasarelaSS) {
      log.info(`[${this.nombre}] En pasarela SS — buscando boton certificado`)

      try {
        await this.esperarElemento(SELECTORES.botonCertificado, TIMEOUT_LOGIN)
        await this.clic(SELECTORES.botonCertificado)
        log.info(`[${this.nombre}] Clic en boton certificado SS`)
      } catch {
        log.warn(`[${this.nombre}] Boton certificado SS no encontrado`)
        await this.capturarPantalla('ss-login-sin-boton')
        throw new Error('No se encontro el boton de login con certificado')
      }

      await this.esperar(2000)

      // Verificar si redirigió a Cl@ve (flujo 3)
      const urlPostClic = this.obtenerURL()
      if (urlPostClic.includes('pasarela.clave.gob.es') || urlPostClic.includes('clave.gob.es')) {
        log.info(`[${this.nombre}] Pasarela SS redirigió a Cl@ve`)
        await this.manejarPasarelaClave(10_000, TIMEOUT_REDIRECCION)
      } else {
        // Esperar redireccion directa post-login
        log.info(`[${this.nombre}] Esperando redireccion post-autenticacion SS...`)
        try {
          await this.esperarRedireccion(urlPostClic, TIMEOUT_REDIRECCION)
        } catch {
          log.warn(`[${this.nombre}] Timeout en redireccion post-login SS`)
        }
      }

      await this.esperar(3000)
      log.info(`[${this.nombre}] Post-login URL: ${this.obtenerURL()}`)
      return
    }

    // Caso 3: No en ninguna pasarela — posible sesion activa o URL desconocida
    log.info(`[${this.nombre}] No en pasarela conocida — intentando Cl@ve como fallback`)
    const pasoPorClave = await this.manejarPasarelaClave(5_000, TIMEOUT_REDIRECCION)
    if (!pasoPorClave) {
      log.info(`[${this.nombre}] Sin pasarela detectada — posible sesion activa`)
    }
    await this.esperar(3000)
    log.info(`[${this.nombre}] Post-auth URL: ${this.obtenerURL()}`)
  }

  /**
   * Espera a que aparezca la pagina de notificaciones.
   * Busca tabla, mensajes de vacio, o indicadores de sesion.
   * Tambien busca el texto real de la SS: "No existen notificaciones"
   */
  private async esperarPaginaNotificaciones(): Promise<void> {
    if (!this.window) throw new Error('Navegador no inicializado')

    const inicio = Date.now()

    while (Date.now() - inicio < TIMEOUT_TABLA) {
      const encontrado = await this.ejecutarJS<boolean>(`
        (function() {
          // Buscar por selectores CSS
          var selectoresTabla = '${SELECTORES.tablaNotificaciones.replace(/'/g, "\\\\'")}';
          var selectoresVacio = '${SELECTORES.sinResultados.replace(/'/g, "\\\\'")}';
          var selectoresLogin = '${SELECTORES.indicadorLogin.replace(/'/g, "\\\\'")}';

          if (document.querySelector(selectoresTabla)) return true;
          if (document.querySelector(selectoresVacio)) return true;
          if (document.querySelector(selectoresLogin)) return true;

          // Buscar por texto real de la SS (vista en screenshot real)
          var bodyText = document.body ? document.body.innerText : '';
          if (bodyText.includes('No existen notificaciones')) return true;
          if (bodyText.includes('Listado de notificaciones')) return true;
          if (bodyText.includes('Búsqueda de notificaciones')) return true;
          if (bodyText.includes('Notificaciones electrónicas')) return true;

          return false;
        })()
      `)
      if (encontrado) {
        log.info(`[${this.nombre}] Pagina de notificaciones detectada`)
        return
      }
      await this.esperar(500)
    }

    log.warn(`[${this.nombre}] Timeout esperando pagina de notificaciones`)
    await this.capturarPantalla('ss-notif-timeout')
  }

  /**
   * Extrae notificaciones de la tabla HTML via executeJavaScript.
   *
   * Columnas esperadas (segun manual de usuario SS):
   * 0: Prestacion/procedimiento
   * 1: Materia
   * 2: Fecha puesta a disposicion
   * 3: Destinatario
   * 4: Estado
   * 5: Fecha/hora vencimiento
   */
  private async extraerNotificaciones(): Promise<NotificacionPortal[]> {
    if (!this.window) return []

    // Verificar si existe la tabla
    const hayTabla = await this.ejecutarJS<boolean>(`
      !!document.querySelector('${SELECTORES.tablaNotificaciones.replace(/'/g, "\\\\'")}')
    `)
    if (!hayTabla) {
      log.warn(`[${this.nombre}] Tabla no encontrada — capturando pantalla`)
      await this.capturarPantalla('ss-notif-sin-tabla')
      return this.extraerDeTablaGenerica()
    }

    // Extraer todas las filas de una sola vez via JS
    const datosFilas = await this.ejecutarJS<Array<{
      prestacion: string
      materia: string
      fechaDisposicion: string
      destinatario: string
      estado: string
      fechaVencimiento: string
      enlace: string
    } | null>>(`
      (function() {
        var filas = document.querySelectorAll('${SELECTORES.filasTabla.replace(/'/g, "\\\\'")}');
        return Array.from(filas).map(function(fila) {
          var celdas = fila.querySelectorAll('td');
          if (celdas.length < 3) return null;
          return {
            prestacion: celdas[0] ? celdas[0].textContent.trim() : '',
            materia: celdas[1] ? celdas[1].textContent.trim() : '',
            fechaDisposicion: celdas[2] ? celdas[2].textContent.trim() : '',
            destinatario: celdas[3] ? celdas[3].textContent.trim() : '',
            estado: celdas[4] ? celdas[4].textContent.trim() : 'Pendiente',
            fechaVencimiento: celdas[5] ? celdas[5].textContent.trim() : '',
            enlace: fila.querySelector('a') ? fila.querySelector('a').getAttribute('href') || '' : '',
          };
        });
      })()
    `)

    if (!datosFilas || datosFilas.length === 0) {
      log.info(`[${this.nombre}] Tabla encontrada pero sin filas`)
      return []
    }

    const resultado: NotificacionPortal[] = []

    for (let i = 0; i < datosFilas.length; i++) {
      const datos = datosFilas[i]
      if (!datos) continue

      const titulo = datos.prestacion
        ? `${datos.prestacion}${datos.materia ? ' — ' + datos.materia : ''}`
        : datos.materia || `Notificacion SS #${i + 1}`

      resultado.push({
        idExterno: this.generarIdExterno(
          datos.enlace || `ss-${i}-${datos.fechaDisposicion}`,
        ),
        portal: this.portal,
        tipo: 'Notificacion',
        titulo,
        organismo: 'Seguridad Social',
        fechaDisposicion: this.normalizarFecha(datos.fechaDisposicion),
        fechaCaducidad: datos.fechaVencimiento
          ? this.normalizarFecha(datos.fechaVencimiento)
          : null,
        estado: datos.estado,
        urlDetalle: datos.enlace || undefined,
        rutaPdfLocal: null,
      })
    }

    log.info(`[${this.nombre}] ${resultado.length} notificaciones extraidas`)
    return resultado
  }

  /**
   * Fallback: busca cualquier tabla en la pagina y extrae datos.
   */
  private async extraerDeTablaGenerica(): Promise<NotificacionPortal[]> {
    if (!this.window) return []

    const datosFilas = await this.ejecutarJS<Array<{
      textos: string[]
      enlace: string
    } | null>>(`
      (function() {
        var filas = document.querySelectorAll('table tbody tr');
        return Array.from(filas).map(function(fila) {
          var celdas = fila.querySelectorAll('td');
          if (celdas.length < 2) return null;
          return {
            textos: Array.from(celdas).map(function(c) { return c.textContent.trim(); }),
            enlace: fila.querySelector('a') ? fila.querySelector('a').getAttribute('href') || '' : '',
          };
        });
      })()
    `)

    if (!datosFilas || datosFilas.length === 0) {
      log.info(`[${this.nombre}] Sin tablas en la pagina`)
      return []
    }

    log.info(
      `[${this.nombre}] Fallback: encontradas ${datosFilas.length} filas en tabla generica`,
    )

    const resultado: NotificacionPortal[] = []

    for (let i = 0; i < datosFilas.length; i++) {
      const datos = datosFilas[i]
      if (!datos || datos.textos.length < 2) continue

      const [prestacion, materia, fecha, , estado, fechaVenc] = datos.textos
      const titulo = prestacion
        ? `${prestacion}${materia ? ' — ' + materia : ''}`
        : `Notificacion SS #${i + 1}`

      resultado.push({
        idExterno: this.generarIdExterno(
          datos.enlace || `ss-gen-${i}-${fecha}`,
        ),
        portal: this.portal,
        tipo: 'Notificacion',
        titulo,
        organismo: 'Seguridad Social',
        fechaDisposicion: this.normalizarFecha(fecha ?? ''),
        fechaCaducidad: fechaVenc
          ? this.normalizarFecha(fechaVenc)
          : null,
        estado: estado || 'Pendiente',
        urlDetalle: datos.enlace || undefined,
        rutaPdfLocal: null,
      })
    }

    log.info(
      `[${this.nombre}] Fallback: ${resultado.length} notificaciones extraidas`,
    )
    return resultado
  }
}
