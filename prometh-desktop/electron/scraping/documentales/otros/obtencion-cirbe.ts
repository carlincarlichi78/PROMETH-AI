import log from 'electron-log'
import { BaseScraperDocumental } from '../base-scraper-documental'
import type { ResultadoScraping } from '../../tipos'

/**
 * Scraper para descargar informe CIRBE previamente solicitado.
 * Portal: Banco de Espana — Central de Informacion de Riesgos.
 *
 * Flujo real mapeado (Chrome MCP 2026-02-21):
 * 1. Navegar a aps.bde.es → "Pasarela de acceso"
 * 2. Click "Acceder usando certificado" → select-client-certificate
 * 3. Portal CIRBE: pagina inicio con menu SPA
 * 4. Click "Consulta de estado y descarga de informes" (link SPA href="#")
 * 5. Si NO hay solicitudes: "No dispone de solicitudes en curso" → return error
 * 6. Si hay solicitudes: tabla con peticiones completadas/pendientes
 *    - Seleccionar peticion (radio) → click boton descarga → will-download PDF
 *
 * Auth: Pasarela propia BdE → certificado digital (NO Cl@ve)
 * IMPORTANTE: Requiere haber enviado la solicitud previamente (ScraperSolicitudCirbe)
 * y esperar ~15 minutos para que el informe este disponible.
 */
export class ScraperObtencionCirbe extends BaseScraperDocumental {
  private readonly url =
    'https://aps.bde.es/cir_www/cir_wwwias/xml/Arranque.html'

  get nombre(): string {
    return 'Obtencion CIRBE'
  }

  async ejecutar(): Promise<ResultadoScraping> {
    log.info(`[${this.nombre}] Iniciando obtencion de informe CIRBE`)

    // ── Paso 1: Navegar a la pasarela de acceso del BdE ──
    await this.navegar(this.url)
    await this.delay(3000)

    // ── Paso 2: Click "Acceder usando certificado" → select-client-certificate ──
    const urlActual = this.obtenerURL()
    if (urlActual.includes('Arranque.html') && !urlActual.includes('#')) {
      const clicCert = await this.ejecutarJs<boolean>(`
        (function() {
          var enlaces = document.querySelectorAll('a');
          for (var i = 0; i < enlaces.length; i++) {
            var t = (enlaces[i].textContent || '').toLowerCase();
            if (t.includes('acceder usando certificado') || t.includes('certificado electr')) {
              enlaces[i].click();
              return true;
            }
          }
          return false;
        })()
      `)

      if (clicCert) {
        log.info(`[${this.nombre}] Click en "Acceder usando certificado"`)
        await this.delay(5000)
      }
    }

    await this.capturarPantalla('01-post-login')

    // ── Paso 3: Verificar portal CIRBE ──
    await this.delay(2000)
    const textoPortal = await this.ejecutarJs<string>(`
      (document.body.innerText || '').substring(0, 500)
    `)
    if (!textoPortal?.toLowerCase().includes('central de informaci')) {
      log.error(`[${this.nombre}] No parece ser el portal CIRBE`)
      return { exito: false, error: 'No se accedio al portal CIRBE correctamente' }
    }

    // ── Paso 4: Click en "Consulta de estado y descarga de informes" (SPA) ──
    const clicConsulta = await this.ejecutarJs<boolean>(`
      (function() {
        var enlaces = document.querySelectorAll('a');
        for (var i = 0; i < enlaces.length; i++) {
          var t = (enlaces[i].textContent || '').trim().toLowerCase();
          if (t.includes('consulta') && t.includes('descarga') && t.includes('informe')) {
            enlaces[i].click();
            return true;
          }
        }
        return false;
      })()
    `)

    if (!clicConsulta) {
      log.error(`[${this.nombre}] Link "Consulta de estado y descarga" no encontrado`)
      return { exito: false, error: 'No se encontro enlace de consulta/descarga en portal CIRBE' }
    }

    log.info(`[${this.nombre}] Click en "Consulta de estado y descarga"`)
    await this.delay(4000)

    await this.capturarPantalla('02-consulta')

    // ── Paso 5: Verificar si hay solicitudes ──
    const textoConsulta = await this.ejecutarJs<string>(`
      (document.body.innerText || '').toLowerCase()
    `)

    if (textoConsulta?.includes('no dispone de solicitudes')) {
      log.warn(`[${this.nombre}] No hay solicitudes CIRBE pendientes`)
      return {
        exito: false,
        error: 'No hay solicitudes CIRBE en curso. Primero debes solicitar el informe CIRBE (boton "Solicitud CIRBE") y esperar ~15 minutos.',
      }
    }

    // ── Paso 6: Verificar estado de la solicitud ──
    // La tabla tiene columnas: Fecha solicitud | Referencia | Periodo | Estado | Fecha obtencion
    // Estado "Registrada" = aun no lista. Necesita tener "Fecha y hora de obtencion" rellena.
    const estadoSolicitud = await this.ejecutarJs<string>(`
      (function() {
        // Buscar celda de estado en la tabla (columna 4, index 3)
        var celdas = document.querySelectorAll('table td');
        for (var i = 0; i < celdas.length; i++) {
          var t = (celdas[i].textContent || '').trim().toLowerCase();
          if (t === 'registrada' || t === 'en proceso' || t === 'pendiente') {
            return t;
          }
        }
        return '';
      })()
    `)

    // Verificar si tiene fecha de obtencion (columna 5) — si esta vacia, no esta lista
    const fechaObtencion = await this.ejecutarJs<string>(`
      (function() {
        var filas = document.querySelectorAll('table tr');
        for (var i = 1; i < filas.length; i++) {
          var celdas = filas[i].querySelectorAll('td');
          if (celdas.length >= 5) {
            // Columna 5 (index 4) = Fecha y hora de obtencion
            var fecha = (celdas[4].textContent || '').trim();
            if (fecha.length > 0) return fecha;
          }
        }
        return '';
      })()
    `)

    if (estadoSolicitud && !fechaObtencion) {
      log.warn(`[${this.nombre}] Solicitud en estado "${estadoSolicitud}" — aun no lista`)
      return {
        exito: false,
        error: `La solicitud CIRBE esta en estado "${estadoSolicitud}". Espera ~15 minutos hasta que este lista para descarga. Vuelve a intentarlo despues.`,
      }
    }

    log.info(`[${this.nombre}] Solicitud disponible para descarga (fecha obtencion: ${fechaObtencion || 'detectada'})`)

    // ── Paso 7: Seleccionar solicitud y descargar ──
    // Seleccionar primer radio de la tabla
    await this.ejecutarJs(`
      var radio = document.querySelector('table input[type="radio"]');
      if (radio) radio.click();
    `)
    await this.delay(1000)

    log.info(`[${this.nombre}] Solicitud seleccionada en tabla`)

    // ── Paso 8: Buscar boton de descarga ──
    const nombreArchivo = this.nombreConFecha('Informe_CIRBE')

    // Configurar interceptor will-download antes de clicar
    this.configurarInterceptorDescarga()

    try {
      const ruta = await this.descargarConPromesa(
        async () => {
          // Buscar boton de descarga
          const clicked = await this.ejecutarJs<boolean>(`
            (function() {
              var botones = document.querySelectorAll('button, a, input[type="submit"]');
              for (var i = 0; i < botones.length; i++) {
                var t = (botones[i].textContent || botones[i].value || '').toLowerCase();
                if (t.includes('descargar') || t.includes('ver informe') || t.includes('obtener')) {
                  botones[i].click();
                  return true;
                }
              }
              // Fallback: boton con id conocido
              var btn = document.querySelector('#BotonDescargar, #BotonObtener');
              if (btn) { btn.click(); return true; }
              return false;
            })()
          `)
          if (!clicked) {
            log.warn(`[${this.nombre}] Boton de descarga no encontrado — intentando link`)
            // Fallback: buscar link con href que contenga descarga
            await this.ejecutarJs(`
              var links = document.querySelectorAll('a[href]');
              for (var i = 0; i < links.length; i++) {
                var h = links[i].href.toLowerCase();
                if (h.includes('descarg') || h.includes('pdf') || h.includes('informe')) {
                  links[i].click();
                  break;
                }
              }
            `)
          }
        },
        nombreArchivo,
        45_000,
      )

      log.info(`[${this.nombre}] Informe CIRBE descargado: ${ruta}`)
      return {
        exito: true,
        rutaDescarga: ruta,
        datos: { rutasArchivos: [ruta] },
      }
    } catch (err) {
      log.warn(`[${this.nombre}] will-download fallo: ${(err as Error).message}`)
    }

    // ── Fallback: printToPdf ──
    log.warn(`[${this.nombre}] Usando printToPdf como fallback`)
    await this.capturarPantalla('fallback-printToPdf')
    const rutaPdf = await this.printToPdf(nombreArchivo)
    return {
      exito: true,
      rutaDescarga: rutaPdf,
      datos: { rutasArchivos: [rutaPdf] },
    }
  }
}
