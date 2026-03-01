import log from 'electron-log'
import { BaseScraperDocumental } from '../base-scraper-documental'
import type { ResultadoScraping, ConfigScraping } from '../../tipos'

/**
 * Scraper para obtener certificados de IRPF de la AEAT.
 * Descarga hasta 3 ejercicios fiscales disponibles en el dropdown.
 *
 * Flujo:
 * 1. Formulario → cerrar alertsModal → seleccionar ejercicio → validar
 * 2. Click "Firmar Enviar" → popup firma (Conforme + Firmar)
 * 3. Tras firma: pagina muestra #descarga (boton "Descargar documento")
 * 4. Reiniciar browser completo entre cada anio fiscal (evita estado residual)
 *
 * Auth: SSL/TLS directo a www1.agenciatributaria.gob.es (sin Cl@ve)
 */
export class ScraperCertificadosIrpf extends BaseScraperDocumental {
  private readonly url =
    'https://www1.agenciatributaria.gob.es/wlpl/CERE-EMCE/InternetServlet'

  constructor(serialNumber: string, config?: Partial<ConfigScraping>) {
    super(serialNumber, {
      ...config,
      // 5 minutos: 3 ejercicios × ~80s cada uno + margen
      timeoutGlobal: 300_000,
    })
  }

  get nombre(): string {
    return 'Certificados IRPF'
  }

  async ejecutar(): Promise<ResultadoScraping> {
    log.info(`[${this.nombre}] Iniciando obtencion de certificados IRPF`)

    // Paso 1: Navegar y obtener ejercicios disponibles
    await this.navegar(this.url)
    await this.cerrarModalSiExiste('#alertsModal .close')
    await this.esperarSelector('#fEjercicio')

    const opciones = await this.ejecutarJs<string[]>(`
      Array.from(document.querySelector('#fEjercicio').options)
        .filter(o => o.value && o.value !== '')
        .slice(0, 3)
        .map(o => o.value)
    `)

    if (opciones.length === 0) {
      return { exito: false, error: 'No hay ejercicios fiscales disponibles' }
    }

    log.info(`[${this.nombre}] Ejercicios disponibles: ${opciones.join(', ')}`)

    const rutasDescargadas: string[] = []
    const erroresParciales: string[] = []

    for (let i = 0; i < opciones.length; i++) {
      const anio = opciones[i]

      try {
        // Reiniciar browser entre iteraciones (patron Findiur — sesion limpia)
        if (i > 0) {
          log.info(`[${this.nombre}] Reiniciando browser para ejercicio ${anio}...`)
          await this.cerrarNavegador()
          await this.delay(2000) // Margen para liberar recursos
          await this.inicializarNavegador()
          await this.delay(1000)

          try {
            await this.navegar(this.url)
          } catch (navErr) {
            log.warn(`[${this.nombre}] Error navegando tras reinicio para ${anio}: ${(navErr as Error).message}`)
            await this.capturarPantalla(`reinicio-error-${anio}`)
            erroresParciales.push(`${anio}: error de navegacion tras reinicio`)
            continue
          }

          await this.delay(2000)
          await this.cerrarModalSiExiste('#alertsModal .close')

          // Verificar que cargó el formulario correctamente
          try {
            await this.esperarSelector('#fEjercicio', 20_000)
          } catch {
            log.warn(`[${this.nombre}] Formulario no cargo tras reinicio para ${anio}`)
            await this.capturarPantalla(`form-no-cargo-${anio}`)

            // Detectar pagina de error AEAT
            const esError = await this.ejecutarJs<boolean>(`
              (function() {
                var t = (document.body ? document.body.innerText : '').toLowerCase();
                return t.includes('error interno') || t.includes('no habilitada') || t.includes('no identificado');
              })()
            `).catch(() => false)

            if (esError) {
              erroresParciales.push(`${anio}: AEAT devolvio error`)
              continue
            }

            // Intentar re-navegar una vez mas
            log.info(`[${this.nombre}] Reintentando navegacion para ${anio}...`)
            await this.navegar(this.url)
            await this.delay(3000)
            await this.cerrarModalSiExiste('#alertsModal .close')
            await this.esperarSelector('#fEjercicio', 15_000)
          }
        }

        log.info(`[${this.nombre}] Procesando ejercicio ${anio} (${i + 1}/${opciones.length})`)

        // Seleccionar ejercicio fiscal
        await this.seleccionarOpcion('#fEjercicio', anio)
        await this.delay(1000)

        // Validar solicitud
        await this.clickElemento('#validarSolicitud')

        // Esperar boton de firma con mas margen
        await this.esperarSelector("input[value='Firmar Enviar']", 20_000)
        await this.delay(500)

        // Preparar popup de firma
        const waitPopupFirma = this.prepararEsperaVentana(30_000)
        await this.clickElemento("input[value='Firmar Enviar']")

        const popupFirma = await waitPopupFirma
        log.info(`[${this.nombre}] Popup de firma abierto para ${anio}`)

        await this.esperarSelectorEnVentana(popupFirma, '#Conforme', 15_000)
        await this.clickElementoEnVentana(popupFirma, '#Conforme')
        await this.delay(1500)

        const nombreArchivo = `Certificado_IRPF_${anio}.pdf`

        // Configurar interceptor como respaldo (captura popups/downloadURL)
        const esperaDescarga = this.configurarInterceptorDescarga(nombreArchivo, 30_000)

        await this.clickElementoEnVentana(popupFirma, '#Firmar')
        log.info(`[${this.nombre}] Firma enviada para ${anio} — esperando resultado...`)

        // Esperar a que AEAT procese la firma
        await this.delay(3000)

        // Estrategia 1: boton #descarga (funciona en la mayoria de casos)
        try {
          await this.esperarSelector('#descarga', 20_000)
          const ruta = await this.descargarConPromesa(
            () => this.clickElemento('#descarga'),
            nombreArchivo,
            30_000,
          )
          rutasDescargadas.push(ruta)
          log.info(`[${this.nombre}] IRPF ${anio} via #descarga: ${ruta}`)
          continue
        } catch {
          log.warn(`[${this.nombre}] #descarga no encontrado para ${anio}`)
        }

        // Estrategia 2: interceptor will-download (popup PDF)
        try {
          const ruta = await esperaDescarga
          log.info(`[${this.nombre}] IRPF ${anio} via interceptor: ${ruta}`)
          rutasDescargadas.push(ruta)
          continue
        } catch {
          log.warn(`[${this.nombre}] Interceptor no capturo para ${anio}`)
        }

        // Estrategia 3: printToPdf (ultimo recurso)
        log.warn(`[${this.nombre}] printToPdf fallback para ${anio}`)
        await this.capturarPantalla(`fallback-printToPdf-${anio}`)
        const rutaPdf = await this.printToPdf(nombreArchivo)
        rutasDescargadas.push(rutaPdf)
      } catch (error) {
        const mensaje = error instanceof Error ? error.message : 'Error desconocido'
        log.error(`[${this.nombre}] Error en ejercicio ${anio}: ${mensaje}`)
        await this.capturarPantalla(`error-${anio}`).catch(() => {})
        erroresParciales.push(`${anio}: ${mensaje}`)
      }
    }

    if (rutasDescargadas.length === 0) {
      return {
        exito: false,
        error: `No se pudo descargar ningun certificado. Errores: ${erroresParciales.join('; ')}`,
      }
    }

    return {
      exito: true,
      datos: {
        tipo: 'certificados_irpf',
        descargados: rutasDescargadas.length,
        total: opciones.length,
        archivos: rutasDescargadas.map((r) => r.split(/[\\/]/).pop()),
        errores: erroresParciales.length > 0 ? erroresParciales : undefined,
      },
      rutaDescarga: rutasDescargadas[0],
    }
  }
}
