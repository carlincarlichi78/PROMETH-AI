import log from 'electron-log'
import { BaseScraperDocumental } from '../base-scraper-documental'
import type { ResultadoScraping } from '../../tipos'
import { loginSeguridadSocial } from '../seguridad-social/login-ss'

/**
 * Scraper para obtener informe CNAE Autonomo desde portal Seguridad Social.
 *
 * Flujo mapeado (Chrome MCP 2026-02-21):
 * 1. Navegar a ImportaSS area personal
 * 2. Login SS via IPCE (certificado)
 * 3. Click "Ver tus datos de autonomo" (a.ss-link con ACC_PERFIL_AUTONOMO)
 * 4. Click "Actividades de autonomo" en sidebar (a[href="#datos-actividad"])
 * 5. Click "informe actualizado" (a#autonomo con AC_INFORME_ACTIVIDADES)
 * 6. Pagina "Informe generado" → click #btnDescInformeVariasAct → will-download PDF
 *
 * Auth: SS IPCE
 * Requiere: certificado de autonomo dado de alta en RETA
 */
export class ScraperCnaeAutonomo extends BaseScraperDocumental {
  private readonly url =
    'https://portal.seg-social.gob.es/wps/myportal/importass/importass/personal/'

  get nombre(): string {
    return 'CNAE Autonomo'
  }

  async ejecutar(): Promise<ResultadoScraping> {
    log.info(`[${this.nombre}] Iniciando consulta CNAE autonomo`)

    // Paso 1: Navegar al area personal de ImportaSS
    await this.navegar(this.url)
    await this.delay(3000)

    // Cerrar cookies si aparecen
    await this.cerrarModalSiExiste('#cookies button, .cookie-accept, #onetrust-accept-btn-handler')

    // Paso 2: Login con certificado electronico
    await loginSeguridadSocial(this)
    await this.delay(5000)

    const urlPostLogin = this.obtenerURL()
    log.info(`[${this.nombre}] URL post-login: ${urlPostLogin}`)

    // Si no estamos en el area personal, navegar directamente
    if (!urlPostLogin.includes('personal')) {
      await this.navegar(this.url)
      await this.delay(5000)
    }

    await this.capturarPantalla('paso-2-area-personal')

    // Paso 3: Click "Ver tus datos de autonomo"
    // Selector: a.ss-link con title que contiene "perfil de trabajo autonomo"
    // o href que contiene ACC_PERFIL_AUTONOMO
    const clicAutonomo = await this.ejecutarJs<boolean>(`
      (function() {
        // Buscar por href que contiene ACC_PERFIL_AUTONOMO
        var links = document.querySelectorAll('a.ss-link');
        for (var i = 0; i < links.length; i++) {
          var href = links[i].getAttribute('href') || '';
          if (href.includes('ACC_PERFIL_AUTONOMO') || href.includes('accion!ACC_PERFIL_AUTONOMO')) {
            links[i].click();
            return true;
          }
        }
        // Fallback: buscar por title
        for (var j = 0; j < links.length; j++) {
          var title = (links[j].getAttribute('title') || '').toLowerCase();
          if (title.includes('perfil de trabajo aut') || title.includes('datos de aut')) {
            links[j].click();
            return true;
          }
        }
        // Fallback: buscar por texto
        links = document.querySelectorAll('a');
        for (var k = 0; k < links.length; k++) {
          var texto = (links[k].textContent || '').toLowerCase();
          if (texto.includes('tus datos de aut') || texto.includes('ver tus datos de aut')) {
            links[k].click();
            return true;
          }
        }
        return false;
      })()
    `)

    if (!clicAutonomo) {
      log.error(`[${this.nombre}] Enlace "Ver tus datos de autonomo" no encontrado`)
      await this.capturarPantalla('error-sin-enlace-autonomo')
      return {
        exito: false,
        error: 'No se encontro el enlace de datos de autonomo. ¿El certificado es de un trabajador autonomo?',
        datos: {},
      }
    }

    log.info(`[${this.nombre}] Click en "Ver tus datos de autonomo"`)
    await this.delay(5000)
    await this.capturarPantalla('paso-3-datos-autonomo')

    // Paso 4: Click "Actividades de autonomo" en sidebar
    // Selector: a con href="#datos-actividad" o texto "Actividades de autonomo"
    const clicActividades = await this.ejecutarJs<boolean>(`
      (function() {
        // Buscar por href anchor #datos-actividad
        var link = document.querySelector('a[href="#datos-actividad"]');
        if (link) { link.click(); return true; }
        // Fallback: buscar por texto en sidebar links
        var links = document.querySelectorAll('a.ss-link');
        for (var i = 0; i < links.length; i++) {
          var texto = (links[i].textContent || '').toLowerCase();
          if (texto.includes('actividades de aut')) {
            links[i].click();
            return true;
          }
        }
        return false;
      })()
    `)

    if (!clicActividades) {
      log.warn(`[${this.nombre}] Enlace "Actividades de autonomo" no encontrado en sidebar`)
      await this.capturarPantalla('error-sin-sidebar-actividades')
    } else {
      log.info(`[${this.nombre}] Click en "Actividades de autonomo"`)
    }

    await this.delay(3000)
    await this.capturarPantalla('paso-4-seccion-actividades')

    // Paso 5: Click "informe actualizado" (a#autonomo con AC_INFORME_ACTIVIDADES)
    const clicInforme = await this.ejecutarJs<boolean>(`
      (function() {
        // Selector directo: a#autonomo con title "Descargar resguardo actividades declaradas"
        var link = document.querySelector('a#autonomo');
        if (link) { link.click(); return true; }
        // Fallback: buscar por href que contiene AC_INFORME_ACTIVIDADES
        var links = document.querySelectorAll('a.ss-link');
        for (var i = 0; i < links.length; i++) {
          var href = links[i].getAttribute('href') || '';
          if (href.includes('AC_INFORME_ACTIVIDADES') || href.includes('accion!AC_INFORME_ACTIVIDADES')) {
            links[i].click();
            return true;
          }
        }
        // Fallback: buscar por texto "informe actualizado"
        links = document.querySelectorAll('a');
        for (var j = 0; j < links.length; j++) {
          var texto = (links[j].textContent || '').toLowerCase();
          if (texto.includes('informe actualizado')) {
            links[j].click();
            return true;
          }
        }
        return false;
      })()
    `)

    if (!clicInforme) {
      log.error(`[${this.nombre}] Enlace "informe actualizado" no encontrado`)
      await this.capturarPantalla('error-sin-enlace-informe')
      return {
        exito: false,
        error: 'No se encontro el enlace para generar el informe de actividades',
        datos: {},
      }
    }

    log.info(`[${this.nombre}] Click en "informe actualizado" — esperando pagina "Informe generado"`)
    await this.delay(5000)
    await this.capturarPantalla('paso-5-informe-generado')

    // Paso 6: Click boton "Descargar informe" (#btnDescInformeVariasAct)
    const nombreArchivo = this.nombreConFecha('Informe_CNAE_Autonomo')

    try {
      // Esperar a que aparezca el boton de descarga
      await this.esperarSelector('#btnDescInformeVariasAct', 15_000)
      log.info(`[${this.nombre}] Boton #btnDescInformeVariasAct encontrado`)

      const ruta = await this.descargarConPromesa(
        async () => {
          await this.clickElemento('#btnDescInformeVariasAct')
          log.info(`[${this.nombre}] Click en "Descargar informe" — esperando will-download`)
        },
        nombreArchivo,
        30_000,
      )

      log.info(`[${this.nombre}] Informe CNAE descargado: ${ruta}`)
      return { exito: true, rutaDescarga: ruta, datos: { rutasArchivos: [ruta] } }
    } catch (err) {
      log.warn(`[${this.nombre}] will-download fallo: ${(err as Error).message}`)
    }

    // Fallback: buscar boton por texto o clase ss-button
    try {
      const ruta = await this.descargarConPromesa(
        async () => {
          await this.ejecutarJs<void>(`
            (function() {
              var btns = document.querySelectorAll('button.ss-button');
              for (var i = 0; i < btns.length; i++) {
                var texto = (btns[i].textContent || '').toLowerCase();
                if (texto.includes('descargar informe')) {
                  btns[i].click(); return;
                }
              }
            })()
          `)
          log.info(`[${this.nombre}] Fallback: click boton ss-button "Descargar informe"`)
        },
        nombreArchivo,
        30_000,
      )

      log.info(`[${this.nombre}] Descarga via fallback: ${ruta}`)
      return { exito: true, rutaDescarga: ruta, datos: { rutasArchivos: [ruta] } }
    } catch {
      log.warn(`[${this.nombre}] Fallback descarga tambien fallo`)
    }

    // Fallback final: printToPdf de la pagina actual
    log.warn(`[${this.nombre}] Usando printToPdf como ultimo recurso`)
    await this.capturarPantalla('fallback-printToPdf')
    const rutaPdf = await this.printToPdf(nombreArchivo)
    return { exito: true, rutaDescarga: rutaPdf, datos: { rutasArchivos: [rutaPdf] } }
  }
}
