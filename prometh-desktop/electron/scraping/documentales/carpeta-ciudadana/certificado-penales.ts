import { join } from 'path'
import { writeFileSync } from 'fs'
import log from 'electron-log'
import { BaseScraperDocumental } from '../base-scraper-documental'
import type { ResultadoScraping } from '../../tipos'
import { loginCarpetaCiudadana } from './login-carpeta'

/**
 * Scraper para descargar certificado de antecedentes penales desde Carpeta Ciudadana.
 *
 * Flujo REAL mapeado con Chrome MCP (2026-02-21):
 * 1. Login Carpeta Ciudadana (boton "Acceder a la Carpeta" → Cl@ve → cert electronico)
 * 2. Home autenticado (carpetaciudadana.gob.es/carpeta/mcc/home)
 * 3. Navegar a /carpeta/mcc/antecedentes-penales (SPA Angular — click enlace interno)
 * 4. Pagina muestra: "A fecha DD/MM/AAAA no constan antecedentes penales"
 * 5. Boton "Descargar justificante PDF" (button con i.fa-download)
 *    → Angular hace GET /api/antecedentes-penales/justificante → blob PDF
 *    → NO dispara will-download (es descarga AJAX, no navegacion)
 *
 * SOLUCION: Fetch directo del PDF desde el contexto del renderer via executeJavaScript.
 * La sesion autenticada (cookies) se comparte, asi que el fetch funciona.
 *
 * Auth: Cl@ve via Carpeta Ciudadana → certificado electronico
 */
export class ScraperCertificadoPenales extends BaseScraperDocumental {
  private readonly urlBase = 'https://carpetaciudadana.gob.es'
  private readonly seccionUrl = '/carpeta/mcc/antecedentes-penales'
  private readonly apiJustificante = '/api/antecedentes-penales/justificante'

  get nombre(): string {
    return 'Certificado Penales'
  }

  async ejecutar(): Promise<ResultadoScraping> {
    log.info(`[${this.nombre}] Iniciando descarga de certificado de penales`)

    // Paso 1: Login en Carpeta Ciudadana
    await this.navegar(this.urlBase)
    await this.delay(2000)
    await loginCarpetaCiudadana(this)
    await this.delay(3000)

    // Cerrar modal de personalizacion si aparece
    await this.cerrarModalPersonalizacion()

    // Paso 2: Navegar a antecedentes penales via SPA Angular
    // Intentar primero navegacion directa por URL
    await this.navegar(`${this.urlBase}${this.seccionUrl}`)
    await this.delay(5000)

    // Verificar si redigirio a home (SPA Angular redirige si no encuentra ruta)
    const urlActual = this.obtenerURL()
    log.info(`[${this.nombre}] URL actual: ${urlActual}`)

    if (urlActual.includes('/mcc/home') && !urlActual.includes('antecedentes')) {
      // SPA Angular: necesitamos click interno en el enlace
      log.info(`[${this.nombre}] Redirigido a home — intentando click en enlace interno`)
      const clicEnlace = await this.ejecutarJs<boolean>(`
        (function() {
          var a = document.querySelector('a[href*="antecedentes-penales"]');
          if (a) { a.click(); return true; }
          return false;
        })()
      `)
      if (clicEnlace) {
        log.info(`[${this.nombre}] Click en enlace antecedentes-penales`)
        await this.delay(5000)
      } else {
        log.warn(`[${this.nombre}] Enlace antecedentes-penales no encontrado en home`)
      }
    }

    // Paso 3: Esperar contenido de la consulta
    await this.esperarContenidoPenales(20_000)
    await this.capturarPantalla('01-contenido')

    // Paso 4: Descargar PDF via fetch directo (la descarga Angular es AJAX, no will-download)
    const nombreArchivo = this.nombreConFecha('Certificado_Penales')
    const rutaDestino = join(this.carpetaDescargas, nombreArchivo)

    // Estrategia 1: fetch del endpoint API directamente desde el renderer
    try {
      const base64Pdf = await this.ejecutarJs<string>(`
        (async function() {
          try {
            var resp = await fetch('${this.apiJustificante}', {
              credentials: 'include',
              headers: { 'Accept': 'application/pdf' }
            });
            if (!resp.ok) return 'ERROR:' + resp.status;
            var blob = await resp.blob();
            var reader = new FileReader();
            return new Promise(function(resolve) {
              reader.onloadend = function() {
                // data:application/pdf;base64,XXXX → extraer solo la parte base64
                var result = reader.result;
                if (typeof result === 'string' && result.includes(',')) {
                  resolve(result.split(',')[1]);
                } else {
                  resolve('ERROR:no-base64');
                }
              };
              reader.readAsDataURL(blob);
            });
          } catch(e) {
            return 'ERROR:' + e.message;
          }
        })()
      `)

      if (base64Pdf && !base64Pdf.startsWith('ERROR:')) {
        const buffer = Buffer.from(base64Pdf, 'base64')
        writeFileSync(rutaDestino, buffer)
        log.info(`[${this.nombre}] Certificado descargado via fetch API: ${rutaDestino} (${buffer.length} bytes)`)
        return { exito: true, rutaDescarga: rutaDestino, datos: { rutasArchivos: [rutaDestino] } }
      }
      log.warn(`[${this.nombre}] Fetch API fallo: ${base64Pdf}`)
    } catch (err) {
      log.warn(`[${this.nombre}] Fetch API error: ${(err as Error).message}`)
    }

    // Estrategia 2: Click en boton + capturar blob via monkey-patch
    try {
      const base64Pdf = await this.ejecutarJs<string>(`
        (async function() {
          // Monkey-patch URL.createObjectURL para capturar el blob
          var capturedBlob = null;
          var origCreate = URL.createObjectURL;
          URL.createObjectURL = function(blob) {
            capturedBlob = blob;
            return origCreate.call(URL, blob);
          };

          // Click el boton de descarga
          var btns = document.querySelectorAll('button');
          for (var i = 0; i < btns.length; i++) {
            var t = (btns[i].textContent || '').toLowerCase();
            if (t.includes('descargar') && (t.includes('justificante') || t.includes('pdf'))) {
              btns[i].click();
              break;
            }
          }

          // Esperar a que Angular haga el fetch y cree el blob
          var intentos = 0;
          while (!capturedBlob && intentos < 50) {
            await new Promise(function(r) { setTimeout(r, 200); });
            intentos++;
          }

          URL.createObjectURL = origCreate;

          if (!capturedBlob) return 'ERROR:no-blob';

          var reader = new FileReader();
          return new Promise(function(resolve) {
            reader.onloadend = function() {
              var result = reader.result;
              if (typeof result === 'string' && result.includes(',')) {
                resolve(result.split(',')[1]);
              } else {
                resolve('ERROR:no-base64');
              }
            };
            reader.readAsDataURL(capturedBlob);
          });
        })()
      `)

      if (base64Pdf && !base64Pdf.startsWith('ERROR:')) {
        const buffer = Buffer.from(base64Pdf, 'base64')
        writeFileSync(rutaDestino, buffer)
        log.info(`[${this.nombre}] Certificado capturado via monkey-patch: ${rutaDestino} (${buffer.length} bytes)`)
        return { exito: true, rutaDescarga: rutaDestino, datos: { rutasArchivos: [rutaDestino] } }
      }
      log.warn(`[${this.nombre}] Monkey-patch fallo: ${base64Pdf}`)
    } catch (err) {
      log.warn(`[${this.nombre}] Monkey-patch error: ${(err as Error).message}`)
    }

    // Fallback: printToPdf de la pagina actual
    log.warn(`[${this.nombre}] Usando printToPdf como ultimo recurso`)
    await this.capturarPantalla('fallback-printToPdf')
    const rutaPdf = await this.printToPdf(nombreArchivo)
    return { exito: true, rutaDescarga: rutaPdf, datos: { rutasArchivos: [rutaPdf] } }
  }

  /** Espera a que cargue el contenido de antecedentes penales */
  private async esperarContenidoPenales(timeout: number): Promise<void> {
    const inicio = Date.now()
    while (Date.now() - inicio < timeout) {
      const tiene = await this.ejecutarJs<boolean>(`
        (function() {
          var body = document.body ? document.body.innerText : '';
          return body.includes('penales') || body.includes('antecedentes') ||
                 body.includes('Descargar justificante');
        })()
      `)
      if (tiene) return
      await this.delay(1000)
    }
    log.warn(`[${this.nombre}] Timeout esperando contenido de penales`)
  }

  /** Cierra modal de personalizacion de Carpeta Ciudadana si aparece */
  private async cerrarModalPersonalizacion(): Promise<void> {
    try {
      const tieneModal = await this.ejecutarJs<boolean>(`
        (function() {
          var btns = document.querySelectorAll('button');
          for (var i = 0; i < btns.length; i++) {
            var t = (btns[i].textContent || '').toLowerCase();
            if (t.includes('personalizar en otro momento')) {
              btns[i].click(); return true;
            }
          }
          return false;
        })()
      `)
      if (tieneModal) {
        log.info(`[${this.nombre}] Modal de personalizacion cerrado`)
        await this.delay(500)
      }
    } catch {
      // Ignorar — el modal puede no existir
    }
  }
}
