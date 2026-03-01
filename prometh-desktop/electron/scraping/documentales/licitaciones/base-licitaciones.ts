import log from 'electron-log'
import { BaseScraperDocumental } from '../base-scraper-documental'
import type { ResultadoScraping } from '../../tipos'

/**
 * URL del buscador de licitaciones de la Plataforma de Contratacion del Estado.
 * La URL base redirige al formulario JSF de busqueda.
 */
const URL_BUSCADOR =
  'https://contrataciondelestado.es/wps/portal/plataforma'

/**
 * Clase base para scrapers de licitaciones publicas.
 * Flujo mapeado con Chrome MCP (2026-02-21):
 * 1. Navegar a contrataciondelestado.es/wps/portal/plataforma
 * 2. Click en card "Buscadores" → "Licitaciones"
 * 3. Formulario JSF con: Expediente, Pais, Tipo contrato, Lugar ejecucion,
 *    CPV, Organo contratacion, Estado, Fechas, Procedimiento, etc.
 * 4. Seleccionar Estado = "Publicada", opcionalmente Lugar de ejecucion
 * 5. Click Buscar → tabla de resultados (Expediente, Tipo, Estado, Importe, Fecha, Organo)
 * 6. PrintToPdf de la pagina de resultados
 *
 * Las subclases definen `comunidad` y `lugarEjecucion` para filtrar por CCAA.
 */
export abstract class BaseLicitaciones extends BaseScraperDocumental {
  /** Nombre de la comunidad autonoma para logs y nombre de archivo */
  protected abstract readonly comunidad: string

  /**
   * Texto para el campo "Lugar de ejecucion" del formulario.
   * Vacio = sin filtro (busqueda general a nivel nacional).
   */
  protected abstract readonly lugarEjecucion: string

  async ejecutar(): Promise<ResultadoScraping> {
    log.info(
      `[${this.nombre}] Iniciando consulta de licitaciones — ${this.comunidad}`,
    )

    // Paso 1: Navegar a la plataforma de contratacion
    await this.navegar(URL_BUSCADOR)
    await this.delay(3000)

    // Paso 2: Click en card "Buscadores" y luego "Licitaciones"
    // La URL base redirige al inicio; necesitamos ir al buscador
    const navegoABuscador = await this.ejecutarJs<boolean>(`
      (function() {
        // Buscar enlace "Buscadores" en nav
        var links = document.querySelectorAll('a');
        for (var i = 0; i < links.length; i++) {
          if ((links[i].textContent || '').trim() === 'Buscadores') {
            links[i].click();
            return true;
          }
        }
        return false;
      })()
    `)

    if (navegoABuscador) {
      await this.delay(3000)

      // Click en card "Licitaciones"
      await this.ejecutarJs<boolean>(`
        (function() {
          var links = document.querySelectorAll('a');
          for (var i = 0; i < links.length; i++) {
            var texto = (links[i].textContent || '').trim();
            if (texto === 'Licitaciones' || texto.includes('Licitaciones')) {
              // Evitar link de nav (solo cards del cuerpo)
              var parent = links[i].closest('.portlet-body, main, .buscadores, article');
              if (parent || links[i].className.includes('card') || links[i].querySelector('h2, h3')) {
                links[i].click();
                return true;
              }
            }
          }
          // Fallback: click en el primer "Licitaciones" que no sea nav
          for (var j = 0; j < links.length; j++) {
            if ((links[j].textContent || '').trim() === 'Licitaciones' && links[j].href && links[j].href.includes('#')) {
              continue;
            }
            if ((links[j].textContent || '').includes('Licitaciones')) {
              links[j].click();
              return true;
            }
          }
          return false;
        })()
      `)
      await this.delay(3000)
    }

    // Paso 3: Esperar formulario de busqueda
    try {
      await this.esperarSelector(
        'select, input[type="text"], form',
        15_000,
      )
    } catch {
      log.warn(`[${this.nombre}] Formulario no detectado, intentando con la pagina actual`)
    }

    // Paso 4: Rellenar filtros
    // Estado = "Publicada" (value="PUB")
    const filtrosAplicados = await this.ejecutarJs<boolean>(`
      (function() {
        // Buscar select de Estado (contiene opciones PUB, ADJ, etc.)
        var selects = document.querySelectorAll('select');
        for (var i = 0; i < selects.length; i++) {
          var opciones = selects[i].querySelectorAll('option');
          for (var j = 0; j < opciones.length; j++) {
            if (opciones[j].value === 'PUB') {
              selects[i].value = 'PUB';
              selects[i].dispatchEvent(new Event('change', { bubbles: true }));
              return true;
            }
          }
        }
        return false;
      })()
    `)

    if (filtrosAplicados) {
      log.info(`[${this.nombre}] Estado = Publicada seleccionado`)
    }

    // Lugar de ejecucion (si aplica)
    if (this.lugarEjecucion) {
      await this.ejecutarJs<void>(`
        (function() {
          var inputs = document.querySelectorAll('input[type="text"]');
          for (var i = 0; i < inputs.length; i++) {
            var label = inputs[i].closest('td, div, fieldset');
            if (label && (label.textContent || '').includes('Lugar de ejecuci')) {
              inputs[i].value = '${this.lugarEjecucion}';
              inputs[i].dispatchEvent(new Event('change', { bubbles: true }));
              inputs[i].dispatchEvent(new Event('input', { bubbles: true }));
              break;
            }
          }
        })()
      `)
      log.info(`[${this.nombre}] Lugar de ejecucion = ${this.lugarEjecucion}`)
    }

    // Paso 5: Click Buscar
    const buscado = await this.ejecutarJs<boolean>(`
      (function() {
        var botones = document.querySelectorAll('button[type="submit"], input[type="submit"]');
        for (var i = 0; i < botones.length; i++) {
          var texto = (botones[i].textContent || botones[i].value || '').trim();
          if (texto === 'Buscar') {
            botones[i].click();
            return true;
          }
        }
        return false;
      })()
    `)

    if (!buscado) {
      log.warn(`[${this.nombre}] Boton Buscar no encontrado`)
    }

    // Paso 6: Esperar resultados
    await this.delay(5000)

    // Verificar que hay tabla de resultados
    const tieneResultados = await this.ejecutarJs<boolean>(`
      (function() {
        return !!document.querySelector('table, .tabla-resultados, #myTablaSortable');
      })()
    `)

    if (!tieneResultados) {
      log.warn(`[${this.nombre}] No se detecto tabla de resultados`)
    } else {
      log.info(`[${this.nombre}] Resultados cargados`)
    }

    // Paso 7: Generar PDF de la pagina de resultados
    const nombreArchivo = this.nombreConFecha(
      `Licitaciones_${this.comunidad}`,
    )
    const rutaPdf = await this.printToPdf(nombreArchivo, {
      landscape: true,
      scale: 0.55,
    })

    log.info(`[${this.nombre}] PDF generado: ${rutaPdf}`)

    return {
      exito: true,
      rutaDescarga: rutaPdf,
      datos: {
        comunidad: this.comunidad,
        rutasArchivos: [rutaPdf],
      },
    }
  }
}
