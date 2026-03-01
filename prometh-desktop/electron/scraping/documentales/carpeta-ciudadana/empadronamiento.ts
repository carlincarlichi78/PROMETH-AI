import log from 'electron-log'
import { BaseScraperDocumental } from '../base-scraper-documental'
import type { ResultadoScraping } from '../../tipos'
import { loginCarpetaCiudadana } from './login-carpeta'

/**
 * Scraper para descargar justificante de empadronamiento desde Carpeta Ciudadana.
 *
 * Flujo (mapeado en Chrome 2026-02):
 * 1. Login Carpeta Ciudadana (cookies → Cl@ve → "DNIe / Certificado electronico")
 * 2. Navegar a /carpeta/mcc/domicilio (SPA Angular — click interno, no URL directa)
 * 3. Pagina muestra datos del padron: direccion, CP, municipio, provincia, fecha variacion
 * 4. Click en boton "Descargar justificante PDF" → will-download
 *
 * Nota: la nueva Carpeta Ciudadana (2026) es SPA Angular.
 * La navegacion directa por URL redirige a /home. Hay que navegar internamente
 * clickando el enlace a[href="/carpeta/mcc/domicilio"] desde la home.
 *
 * Auth: Cl@ve via Carpeta Ciudadana
 */
export class ScraperEmpadronamiento extends BaseScraperDocumental {
  private readonly urlBase = 'https://carpetaciudadana.gob.es'
  private readonly seccionUrl = '/carpeta/mcc/domicilio'

  get nombre(): string {
    return 'Empadronamiento'
  }

  async ejecutar(): Promise<ResultadoScraping> {
    log.info(`[${this.nombre}] Iniciando descarga de justificante de empadronamiento`)

    // Paso 1: Login en Carpeta Ciudadana
    await this.navegar(this.urlBase)
    await this.delay(2000)
    await loginCarpetaCiudadana(this)
    await this.delay(3000)

    // Cerrar modal de personalizacion si aparece
    await this.cerrarModalPersonalizacion()

    // Paso 2: Navegar a seccion domicilio via SPA (click interno)
    const navegado = await this.navegarSeccionSPA(this.seccionUrl, 10_000)
    if (!navegado) {
      // Fallback: navegacion directa
      await this.navegar(`${this.urlBase}${this.seccionUrl}`)
      await this.delay(5000)
    }

    // Esperar contenido
    await this.esperarContenidoDomicilio(20_000)
    await this.capturarPantalla('01-contenido')

    // Paso 3: Buscar boton "Descargar justificante PDF" (interfaz 2026)
    const nombreArchivo = this.nombreConFecha('Empadronamiento')

    // Estrategia 1: boton "Descargar justificante PDF"
    try {
      const tieneBoton = await this.ejecutarJs<boolean>(`
        (function() {
          var btns = document.querySelectorAll('button');
          for (var i = 0; i < btns.length; i++) {
            var t = (btns[i].textContent || '').toLowerCase();
            if (t.includes('descargar') && (t.includes('justificante') || t.includes('pdf'))) {
              return true;
            }
          }
          return false;
        })()
      `)

      if (tieneBoton) {
        log.info(`[${this.nombre}] Boton "Descargar justificante PDF" encontrado`)
        const ruta = await this.descargarConPromesa(
          () => this.ejecutarJs<void>(`
            (function() {
              var btns = document.querySelectorAll('button');
              for (var i = 0; i < btns.length; i++) {
                var t = (btns[i].textContent || '').toLowerCase();
                if (t.includes('descargar') && (t.includes('justificante') || t.includes('pdf'))) {
                  btns[i].click(); return;
                }
              }
            })()
          `),
          nombreArchivo,
          30_000,
        )
        log.info(`[${this.nombre}] Justificante descargado: ${ruta}`)
        return { exito: true, rutaDescarga: ruta, datos: { rutasArchivos: [ruta] } }
      }
    } catch (err) {
      log.warn(`[${this.nombre}] Descarga via boton fallo: ${(err as Error).message}`)
    }

    // Estrategia 2: .fa-download (interfaz antigua Findiur)
    try {
      const tieneIcono = await this.ejecutarJs<boolean>(`
        !!(document.querySelector('.fa-download') || document.querySelector('a[download]'))
      `)
      if (tieneIcono) {
        const ruta = await this.descargarConPromesa(
          () => this.ejecutarJs<void>(`
            (function() {
              var el = document.querySelector('.fa-download');
              if (el) { (el.closest('a') || el.parentElement || el).click(); return; }
              el = document.querySelector('a[download]');
              if (el) { el.click(); }
            })()
          `),
          nombreArchivo,
          30_000,
        )
        log.info(`[${this.nombre}] Justificante descargado via .fa-download: ${ruta}`)
        return { exito: true, rutaDescarga: ruta, datos: { rutasArchivos: [ruta] } }
      }
    } catch {
      log.warn(`[${this.nombre}] .fa-download no encontrado`)
    }

    // Estrategia 3: cualquier boton/enlace con texto "descargar"
    try {
      const encontrado = await this.ejecutarJs<boolean>(`
        (function() {
          var elementos = document.querySelectorAll('a, button');
          for (var i = 0; i < elementos.length; i++) {
            var t = (elementos[i].textContent || '').toLowerCase();
            if (t.includes('descargar')) {
              elementos[i].setAttribute('data-cg-download', 'true');
              return true;
            }
          }
          return false;
        })()
      `)
      if (encontrado) {
        const ruta = await this.descargarConPromesa(
          () => this.clickElemento('[data-cg-download="true"]'),
          nombreArchivo,
          30_000,
        )
        log.info(`[${this.nombre}] Justificante descargado via texto descargar: ${ruta}`)
        return { exito: true, rutaDescarga: ruta, datos: { rutasArchivos: [ruta] } }
      }
    } catch {
      log.warn(`[${this.nombre}] Enlace descargar generico no encontrado`)
    }

    // Fallback: printToPdf
    log.warn(`[${this.nombre}] Usando printToPdf como ultimo recurso`)
    await this.capturarPantalla('fallback-printToPdf')
    const rutaPdf = await this.printToPdf(nombreArchivo)
    return { exito: true, rutaDescarga: rutaPdf, datos: { rutasArchivos: [rutaPdf] } }
  }

  /** Navega a una seccion de Carpeta Ciudadana via click en enlace SPA */
  private async navegarSeccionSPA(ruta: string, timeout: number): Promise<boolean> {
    const inicio = Date.now()
    while (Date.now() - inicio < timeout) {
      const clicOk = await this.ejecutarJs<boolean>(`
        (function() {
          var a = document.querySelector('a[href="${ruta}"]');
          if (a) { a.click(); return true; }
          return false;
        })()
      `)
      if (clicOk) {
        log.info(`[${this.nombre}] Click SPA en ${ruta}`)
        await this.delay(5000)
        return true
      }
      await this.delay(1000)
    }
    log.warn(`[${this.nombre}] Enlace SPA ${ruta} no encontrado`)
    return false
  }

  /** Espera a que cargue el contenido del domicilio */
  private async esperarContenidoDomicilio(timeout: number): Promise<void> {
    const inicio = Date.now()
    while (Date.now() - inicio < timeout) {
      const tiene = await this.ejecutarJs<boolean>(`
        (function() {
          var body = document.body ? document.body.innerText : '';
          return body.includes('domicilio') || body.includes('padrón') ||
                 body.includes('padron') || body.includes('Descargar justificante');
        })()
      `)
      if (tiene) return
      await this.delay(1000)
    }
    log.warn(`[${this.nombre}] Timeout esperando contenido domicilio`)
  }

  /** Cierra modal de personalizacion de Carpeta Ciudadana si aparece */
  private async cerrarModalPersonalizacion(): Promise<void> {
    try {
      await this.ejecutarJs<void>(`
        (function() {
          var btns = document.querySelectorAll('button');
          for (var i = 0; i < btns.length; i++) {
            var t = (btns[i].textContent || '').toLowerCase();
            if (t.includes('personalizar en otro momento')) {
              btns[i].click(); return;
            }
          }
        })()
      `)
      await this.delay(500)
    } catch {
      // Ignorar
    }
  }
}
