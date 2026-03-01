import log from 'electron-log'
import { BaseScraperDocumental } from '../base-scraper-documental'
import type { ResultadoScraping } from '../../tipos'

/**
 * Scraper para obtener certificados del SEPE (Servicio Publico de Empleo Estatal).
 *
 * Flujo real mapeado (Chrome MCP 2026-02-21):
 * 1. Navegar a sede.sepe.gob.es → Certificados de Prestaciones
 * 2. Click "Certificado digital, DNI electronico o usuario Cl@ve"
 *    → redirige a login SEPE → Cl@ve → select-client-certificate
 * 3. Pagina "Tipos de certificado" con 6 opciones:
 *    - 4 submit buttons (si hay prestaciones): Situacion, Prestacion Actual, Importes Periodo, Importes Anuales
 *    - 2 links: IRPF (CertificadoIRPFWeb), Importes Pendientes (CertBonificacionWEB)
 * 4. IRPF: select año → submit "aceptar" → pagina descarga → submit "Descarga" → PDF will-download
 * 5. Otros tipos: submit → pagina resultado → buscar boton descarga → will-download
 *
 * Auth: Login SEPE → Cl@ve → certificado digital
 */
export class ScraperCertificadoSepe extends BaseScraperDocumental {
  // URL directa a la pagina de autenticacion (atajo al paso de login)
  private readonly urlAuth =
    'https://sede.sepe.gob.es/DServiciosPrestanetWEB/TipoAutenticadoAction.do'

  get nombre(): string {
    return 'Certificado SEPE'
  }

  async ejecutar(): Promise<ResultadoScraping> {
    log.info(`[${this.nombre}] Iniciando descarga de certificado SEPE`)

    // Paso 1: Navegar al SEPE — ir directo a la URL de autenticacion
    await this.navegar(this.urlAuth)
    await this.delay(3000)

    // Paso 2: Manejar cadena de autenticacion
    // La URL de auth redirige a login SEPE → Cl@ve → cert selection → vuelta a SEPE
    const urlPostNav = this.obtenerURL()

    // Si estamos en login SEPE (GesUsuariosSEDE)
    if (urlPostNav.includes('GesUsuarios') || urlPostNav.includes('login_recurso')) {
      log.info(`[${this.nombre}] En pagina login SEPE — buscando opcion certificado digital`)
      await this.clickBotonPorTexto(['certificado digital', 'dnie', 'certificado electr'])
      await this.delay(5000)
    }

    // Si estamos en Cl@ve
    if (this.obtenerURL().includes('clave.gob.es') || this.obtenerURL().includes('pasarela')) {
      await this.manejarPasarelaClave(15_000, 30_000)
      await this.delay(5000)
    }

    // Si hay segundo paso de login SEPE
    const urlPost2 = this.obtenerURL()
    if (urlPost2.includes('GesUsuarios') || urlPost2.includes('login_recurso')) {
      await this.clickBotonPorTexto(['certificado digital', 'dnie'])
      await this.delay(5000)

      // Si redirige a Cl@ve de nuevo
      if (this.obtenerURL().includes('clave.gob.es')) {
        await this.manejarPasarelaClave(15_000, 30_000)
        await this.delay(5000)
      }
    }

    await this.capturarPantalla('01-post-login')

    // Paso 3: Verificar que llegamos a la pagina de tipos de certificado
    // URL esperada: /DServiciosPrestanetWEB/TipoAutenticadoAction.do (post-login)
    const urlTipos = this.obtenerURL()
    log.info(`[${this.nombre}] URL post-login: ${urlTipos}`)

    // Aceptar cookies si aparecen
    await this.cerrarModalSiExiste('.js-cookies-accept')
    await this.cerrarModalSiExiste('#onetrust-accept-btn-handler')
    await this.cerrarModalSiExiste('button[id*="cookie"]')

    // Paso 4: Buscar tipo de certificado IRPF (link a CertificadoIRPFWeb)
    // El IRPF es el unico que siempre esta disponible (no requiere prestaciones activas)
    const tieneIRPF = await this.ejecutarJs<boolean>(`
      (function() {
        var enlaces = document.querySelectorAll('a[href*="CertificadoIRPFWeb"], a[href*="ActionIRPF"]');
        return enlaces.length > 0;
      })()
    `)

    if (tieneIRPF) {
      return await this.descargarIRPF()
    }

    // Fallback: intentar descargar certificado de situacion (submit button)
    const tieneSituacion = await this.ejecutarJs<boolean>(`
      (function() {
        var inputs = document.querySelectorAll('input[type="submit"], button[type="submit"]');
        for (var i = 0; i < inputs.length; i++) {
          var t = (inputs[i].value || inputs[i].textContent || '').toLowerCase();
          if (t.includes('situaci') || t.includes('solicitar')) {
            return true;
          }
        }
        return false;
      })()
    `)

    if (tieneSituacion) {
      return await this.descargarPorSubmit('Situacion')
    }

    // Ultimo recurso: buscar cualquier enlace o boton de descarga
    log.warn(`[${this.nombre}] No se encontraron tipos especificos — buscando descarga generica`)
    return await this.intentarDescargaGenerica()
  }

  /**
   * Descarga certificado IRPF del SEPE.
   * Flujo: click enlace IRPF → select año → submit → pagina descarga → submit "Descarga" → PDF
   */
  private async descargarIRPF(): Promise<ResultadoScraping> {
    log.info(`[${this.nombre}] Descargando certificado IRPF`)

    // Click en enlace IRPF
    await this.ejecutarJs<void>(`
      (function() {
        var enlace = document.querySelector('a[href*="CertificadoIRPFWeb"]') ||
                     document.querySelector('a[href*="ActionIRPF"]');
        if (enlace) enlace.click();
      })()
    `)
    await this.delay(3000)

    await this.capturarPantalla('02-irpf-pagina')

    // Seleccionar año (por defecto el mas reciente — ya viene seleccionado)
    // El select tiene opciones tipo "2024", "2023", etc.
    const anioSeleccionado = await this.ejecutarJs<string>(`
      (function() {
        var sel = document.querySelector('select[name*="jercicio"], select[name*="ejercicio"], select');
        if (sel) return sel.value;
        return '';
      })()
    `)
    log.info(`[${this.nombre}] Año IRPF seleccionado: ${anioSeleccionado || 'default'}`)

    // Submit "aceptar" para generar certificado
    const submitOk = await this.ejecutarJs<boolean>(`
      (function() {
        var inputs = document.querySelectorAll('input[type="submit"], button[type="submit"]');
        for (var i = 0; i < inputs.length; i++) {
          var t = (inputs[i].value || inputs[i].textContent || '').toLowerCase();
          if (t.includes('aceptar') || t.includes('enviar') || t.includes('generar')) {
            inputs[i].click();
            return true;
          }
        }
        // Intentar submit del form directamente
        var form = document.querySelector('form');
        if (form) { form.submit(); return true; }
        return false;
      })()
    `)

    if (!submitOk) {
      log.warn(`[${this.nombre}] No se encontro boton aceptar en IRPF`)
      return { exito: false, error: 'Boton aceptar no encontrado en pagina IRPF' }
    }

    await this.delay(3000)
    await this.capturarPantalla('03-irpf-descarga')

    // Pagina "DESCARGA DEL CERTIFICADO" — buscar boton "Descarga" (submit)
    const nombreArchivo = this.nombreConFecha('Certificado_SEPE_IRPF')

    try {
      const ruta = await this.descargarConPromesa(
        async () => {
          const clicked = await this.ejecutarJs<boolean>(`
            (function() {
              var inputs = document.querySelectorAll('input[type="submit"], button[type="submit"]');
              for (var i = 0; i < inputs.length; i++) {
                var t = (inputs[i].value || inputs[i].textContent || '').toLowerCase();
                if (t.includes('descarga') || t.includes('descargar') || t.includes('obtener')) {
                  inputs[i].click();
                  return true;
                }
              }
              return false;
            })()
          `)
          if (!clicked) {
            // Fallback: submit del form
            await this.ejecutarJs<void>(`
              var form = document.querySelector('form');
              if (form) form.submit();
            `)
          }
        },
        nombreArchivo,
        30_000,
      )
      log.info(`[${this.nombre}] Certificado IRPF descargado: ${ruta}`)
      return { exito: true, rutaDescarga: ruta, datos: { rutasArchivos: [ruta] } }
    } catch (err) {
      log.warn(`[${this.nombre}] will-download fallo para IRPF: ${(err as Error).message}`)
    }

    // Fallback: printToPdf
    log.warn(`[${this.nombre}] Usando printToPdf para IRPF`)
    await this.capturarPantalla('fallback-printToPdf')
    const rutaPdf = await this.printToPdf(nombreArchivo)
    return { exito: true, rutaDescarga: rutaPdf, datos: { rutasArchivos: [rutaPdf] } }
  }

  /**
   * Descarga certificado via submit button (Situacion, Prestacion Actual, etc.)
   */
  private async descargarPorSubmit(tipo: string): Promise<ResultadoScraping> {
    log.info(`[${this.nombre}] Descargando certificado tipo: ${tipo}`)

    const nombreArchivo = this.nombreConFecha(`Certificado_SEPE_${tipo}`)

    // Buscar y clickear submit del tipo solicitado
    const clicked = await this.ejecutarJs<boolean>(`
      (function() {
        var inputs = document.querySelectorAll('input[type="submit"], button[type="submit"]');
        for (var i = 0; i < inputs.length; i++) {
          var t = (inputs[i].value || inputs[i].textContent || '').toLowerCase();
          if (t.includes('${tipo.toLowerCase()}') || t.includes('solicitar')) {
            inputs[i].click();
            return true;
          }
        }
        // Click primer submit como fallback
        if (inputs.length > 0) { inputs[0].click(); return true; }
        return false;
      })()
    `)

    if (!clicked) {
      return { exito: false, error: `No se encontro boton para tipo ${tipo}` }
    }

    await this.delay(5000)
    await this.capturarPantalla('02-post-submit')

    // Buscar boton de descarga en la pagina resultado
    try {
      const ruta = await this.descargarConPromesa(
        async () => {
          await this.ejecutarJs<void>(`
            (function() {
              var inputs = document.querySelectorAll('input[type="submit"], button[type="submit"], a');
              for (var i = 0; i < inputs.length; i++) {
                var t = (inputs[i].value || inputs[i].textContent || '').toLowerCase();
                if (t.includes('descarga') || t.includes('descargar') || t.includes('imprimir') || t.includes('obtener')) {
                  inputs[i].click(); return;
                }
              }
              // Submit form como fallback
              var form = document.querySelector('form');
              if (form) form.submit();
            })()
          `)
        },
        nombreArchivo,
        30_000,
      )
      return { exito: true, rutaDescarga: ruta, datos: { rutasArchivos: [ruta] } }
    } catch {
      // printToPdf como fallback
      log.warn(`[${this.nombre}] will-download fallo para ${tipo} — usando printToPdf`)
      const rutaPdf = await this.printToPdf(nombreArchivo)
      return { exito: true, rutaDescarga: rutaPdf, datos: { rutasArchivos: [rutaPdf] } }
    }
  }

  /**
   * Intento generico de descarga — busca cualquier boton/enlace de descarga
   */
  private async intentarDescargaGenerica(): Promise<ResultadoScraping> {
    const nombreArchivo = this.nombreConFecha('Certificado_SEPE')

    const encontrado = await this.ejecutarJs<boolean>(`
      (function() {
        var elementos = document.querySelectorAll('a, button, input[type="submit"]');
        for (var i = 0; i < elementos.length; i++) {
          var t = (elementos[i].textContent || elementos[i].value || '').toLowerCase();
          if (t.includes('descargar') || t.includes('obtener') || t.includes('generar') ||
              t.includes('solicitar') || t.includes('certificado')) {
            elementos[i].setAttribute('data-cg-download', 'true');
            return true;
          }
        }
        return false;
      })()
    `)

    if (encontrado) {
      try {
        const ruta = await this.descargarConPromesa(
          () => this.clickElemento('[data-cg-download="true"]'),
          nombreArchivo,
          30_000,
        )
        return { exito: true, rutaDescarga: ruta, datos: { rutasArchivos: [ruta] } }
      } catch {
        log.warn(`[${this.nombre}] Descarga generica fallo`)
      }
    }

    // Ultimo recurso: printToPdf
    log.warn(`[${this.nombre}] Usando printToPdf como ultimo recurso`)
    await this.capturarPantalla('fallback-printToPdf')
    const rutaPdf = await this.printToPdf(nombreArchivo)
    return { exito: true, rutaDescarga: rutaPdf, datos: { rutasArchivos: [rutaPdf] } }
  }

  /** Helper: click en boton/enlace que contenga alguno de los textos dados */
  private async clickBotonPorTexto(textos: string[]): Promise<void> {
    const textosJson = JSON.stringify(textos)
    await this.ejecutarJs<void>(`
      (function() {
        var textos = ${textosJson};
        var elementos = document.querySelectorAll('a, button, input[type="submit"]');
        for (var i = 0; i < elementos.length; i++) {
          var t = (elementos[i].textContent || elementos[i].value || '').toLowerCase();
          for (var j = 0; j < textos.length; j++) {
            if (t.includes(textos[j])) {
              elementos[i].click();
              return;
            }
          }
        }
      })()
    `).catch(() => { /* puede no existir */ })
  }
}
