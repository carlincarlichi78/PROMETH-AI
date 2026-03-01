import log from 'electron-log'
import { BaseScraperDocumental } from '../base-scraper-documental'
import type { ResultadoScraping } from '../../tipos'

/**
 * Scraper para obtener datos fiscales de los ultimos 3 anios.
 * Genera un PDF via printToPDF por cada ejercicio fiscal.
 * URL dinamica: ultimos 2 digitos del anio en la ruta del servlet.
 */
export class ScraperDatosFiscales extends BaseScraperDocumental {
  /** Base de la URL — se concatenan los 2 ultimos digitos del anio */
  private readonly urlBase =
    'https://www1.agenciatributaria.gob.es/wlpl/DFPA-D182/SvVisDF'

  get nombre(): string {
    return 'Datos Fiscales'
  }

  async ejecutar(): Promise<ResultadoScraping> {
    // El ejercicio fiscal mas reciente cerrado es anioActual - 1
    // (los datos del anio en curso nunca estan disponibles)
    const anioBase = new Date().getFullYear() - 1
    const anios = [anioBase, anioBase - 1, anioBase - 2]
    const rutasGeneradas: string[] = []
    const erroresParciales: string[] = []

    log.info(`[${this.nombre}] Obteniendo datos fiscales para anios: ${anios.join(', ')}`)

    for (let i = 0; i < anios.length; i++) {
      const anio = anios[i]
      const sufijo = String(anio).slice(-2) // Ultimos 2 digitos
      const url = `${this.urlBase}${sufijo}Net`

      log.info(`[${this.nombre}] Navegando a datos fiscales ${anio} — ${url}`)

      try {
        await this.navegar(url)
      } catch (err) {
        log.warn(`[${this.nombre}] Error navegando a ${anio}: ${(err as Error).message}`)
        await this.capturarPantalla(`nav-error-${anio}`)
        erroresParciales.push(`${anio}: error de navegacion`)
        continue
      }

      await this.delay(3000)
      await this.capturarPantalla(`post-nav-${anio}`)

      // Detectar pagina de error AEAT (IP no habilitada, servicio no disponible, etc.)
      const esError = await this.ejecutarJs<boolean>(`
        (function() {
          var texto = (document.body ? document.body.innerText : '').toLowerCase();
          return texto.includes('error interno en el sistema') ||
                 texto.includes('pagina no habilitada') ||
                 texto.includes('página no habilitada') ||
                 texto.includes('servicio no disponible') ||
                 texto.includes('no se puede acceder') ||
                 texto.includes('no identificado');
        })()
      `).catch(() => false)

      if (esError) {
        log.warn(`[${this.nombre}] AEAT devolvio error para ${anio} — saltando`)
        await this.capturarPantalla(`error-aeat-${anio}`)
        erroresParciales.push(`${anio}: AEAT no disponible para este ejercicio`)
        continue
      }

      // En el primer anio puede aparecer un modal informativo
      if (i === 0) {
        await this.cerrarModalSiExiste('#alertsModal .modal-header button.close')
        // Tambien intentar cerrar modal con boton "Aceptar" o "Cerrar"
        await this.ejecutarJs<void>(`
          (function() {
            var btns = document.querySelectorAll('.modal button, .modal .close, button.close');
            for (var j = 0; j < btns.length; j++) {
              var t = (btns[j].textContent || '').toLowerCase();
              if (t.includes('aceptar') || t.includes('cerrar') || btns[j].className.includes('close')) {
                btns[j].click();
                break;
              }
            }
          })()
        `).catch(() => { /* ignorar */ })
        await this.delay(1000)
      }

      // Verificar si estamos autenticados o si necesitamos login
      const urlActual = await this.ejecutarJs<string>('window.location.href')
      log.info(`[${this.nombre}] URL actual tras navegar ${anio}: ${urlActual}`)

      // Si nos redirigieron a login o Cl@ve, manejar autenticacion
      if (urlActual.includes('clave.gob.es') || urlActual.includes('pasarela')) {
        log.info(`[${this.nombre}] Detectada pasarela Cl@ve — manejando login`)
        await this.manejarPasarelaClave(15_000, 30_000)
        await this.delay(3000)
        await this.capturarPantalla(`post-clave-${anio}`)
      }

      // Esperar a que cargue el contenido principal (puede tardar)
      try {
        await this.esperarSelector('#AEAT_contenedor_Aplicacion', 30_000)
        log.info(`[${this.nombre}] Contenedor AEAT cargado para ${anio}`)
      } catch {
        log.warn(`[${this.nombre}] Contenedor AEAT no encontrado para ${anio}`)
        await this.capturarPantalla(`sin-contenedor-${anio}`)

        // Verificar si hay contenido util de todas formas (no errores)
        const textoBody = await this.ejecutarJs<string>(
          'document.body ? document.body.innerText : ""',
        ).catch(() => '')
        const textoLower = textoBody.toLowerCase()

        // No generar PDF si es una pagina de error
        if (
          textoBody.length < 200 ||
          textoLower.includes('error interno') ||
          textoLower.includes('no habilitada') ||
          textoLower.includes('no identificado')
        ) {
          log.warn(`[${this.nombre}] Pagina de error o vacia para ${anio} — saltando`)
          erroresParciales.push(`${anio}: contenido no disponible`)
          continue
        }
        log.info(`[${this.nombre}] Pagina tiene ${textoBody.length} chars — generando PDF igualmente`)
      }

      await this.capturarPantalla(`pre-pdf-${anio}`)

      // Generar PDF de la pagina renderizada
      const nombreArchivo = `Datos_Fiscales_${anio}.pdf`
      const ruta = await this.printToPdf(nombreArchivo, { scale: 0.75 })
      rutasGeneradas.push(ruta)

      log.info(`[${this.nombre}] PDF generado: ${ruta}`)
    }

    if (rutasGeneradas.length === 0) {
      return {
        exito: false,
        error: `No se pudo generar ningun PDF de datos fiscales. ${erroresParciales.join('; ')}`,
      }
    }

    return {
      exito: true,
      datos: {
        tipo: 'datos_fiscales',
        descargados: rutasGeneradas.length,
        total: anios.length,
        anios,
        archivos: rutasGeneradas.map((r) => r.split(/[\\/]/).pop()),
        rutasArchivos: rutasGeneradas,
        errores: erroresParciales.length > 0 ? erroresParciales : undefined,
      },
      rutaDescarga: rutasGeneradas[0],
    }
  }
}
