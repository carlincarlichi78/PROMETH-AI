import log from 'electron-log'
import { BaseScraperDocumental } from '../base-scraper-documental'
import type { ResultadoScraping, ConfigScraping } from '../../tipos'

/** Datos adicionales necesarios para la solicitud CIRBE */
interface DatosExtraCirbe {
  email: string
  fechaNacimiento: string // DD/MM/AAAA
}

/**
 * Scraper para enviar solicitud de informe CIRBE al Banco de Espana.
 * NO descarga ningun archivo — solo envia la solicitud.
 * El informe se recibe por email y estara disponible para descarga en ~15 min.
 *
 * Flujo real mapeado (Chrome MCP 2026-02-21):
 * 1. Navegar a aps.bde.es → "Pasarela de acceso"
 * 2. Click "Acceder usando certificado" → select-client-certificate
 * 3. Portal CIRBE: pagina inicio con menu navegacion SPA
 * 4. Click "Peticion de informe" (link href="#", navegacion SPA)
 * 5. Formulario con 3 secciones:
 *    a) Info titular (auto del certificado)
 *    b) Info a solicitar: tabla periodos con radio + Anadir/Eliminar
 *    c) Otra info: fecha nacimiento DD/MM/AAAA, email, NIE (opcional)
 * 6. Seleccionar radio del periodo (ya viene 2026/01 pre-cargado)
 * 7. Rellenar fecha nacimiento + email
 * 8. Marcar checkbox privacidad
 * 9. Click #BotonAceptar → solicitud enviada
 *
 * IDs reales verificados:
 * - Radio periodo: input[type=radio] en tabla jqGrid
 * - Fecha: #PeticionInformeRiesgo_CajaParaFechaNacimiento
 * - Email: #CajaDeTextoCorreoElectronico
 * - NIE: #CajaDeTextoNIE (opcional)
 * - Checkbox: #CheckBoxSimpleCondicionesPrivacidad
 * - Aceptar: #BotonAceptar
 * - Anadir: #BotonAnadir | Eliminar: #BotonEliminar
 *
 * Auth: Pasarela propia BdE → certificado digital (NO Cl@ve)
 * Requiere datosExtra: { email: string, fechaNacimiento: string }
 */
export class ScraperSolicitudCirbe extends BaseScraperDocumental {
  private readonly url =
    'https://aps.bde.es/cir_www/cir_wwwias/xml/Arranque.html'

  private readonly datosExtra: DatosExtraCirbe

  constructor(
    serialNumber: string,
    datosExtra: DatosExtraCirbe,
    config?: Partial<ConfigScraping>,
  ) {
    super(serialNumber, config)
    this.datosExtra = datosExtra
  }

  get nombre(): string {
    return 'Solicitud CIRBE'
  }

  async ejecutar(): Promise<ResultadoScraping> {
    log.info(`[${this.nombre}] Iniciando solicitud CIRBE`)

    if (!this.datosExtra.email) {
      return { exito: false, error: 'Email requerido para solicitud CIRBE' }
    }
    if (!this.datosExtra.fechaNacimiento) {
      return { exito: false, error: 'Fecha de nacimiento requerida (DD/MM/AAAA) para solicitud CIRBE' }
    }

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

    // ── Paso 3: Verificar que estamos en el portal CIRBE ──
    await this.delay(2000)
    const textoPortal = await this.ejecutarJs<string>(`
      (document.body.innerText || '').substring(0, 500)
    `)
    if (!textoPortal?.toLowerCase().includes('central de informaci')) {
      log.error(`[${this.nombre}] No parece ser el portal CIRBE`)
      return { exito: false, error: 'No se accedio al portal CIRBE correctamente' }
    }

    // ── Paso 4: Click en "Peticion de informe" (link SPA href="#") ──
    const clicPeticion = await this.ejecutarJs<boolean>(`
      (function() {
        var enlaces = document.querySelectorAll('a');
        for (var i = 0; i < enlaces.length; i++) {
          var t = (enlaces[i].textContent || '').trim().toLowerCase();
          if (t === 'petición de informe' || (t.includes('petici') && t.includes('informe'))) {
            enlaces[i].click();
            return true;
          }
        }
        return false;
      })()
    `)

    if (!clicPeticion) {
      log.error(`[${this.nombre}] Link "Peticion de informe" no encontrado`)
      return { exito: false, error: 'No se encontro enlace "Peticion de informe" en portal CIRBE' }
    }

    log.info(`[${this.nombre}] Click en "Peticion de informe"`)
    await this.delay(4000)
    await this.capturarPantalla('02-formulario')

    // ── Paso 5: Esperar formulario — verificar que aparecen los campos ──
    try {
      await this.esperarSelector('#PeticionInformeRiesgo_CajaParaFechaNacimiento', 15_000)
    } catch {
      log.warn(`[${this.nombre}] Campo fecha nacimiento no aparecio — reintentando`)
      await this.delay(3000)
    }

    // ── Paso 6: Seleccionar radio del periodo (tabla jqGrid) ──
    // El periodo mas reciente ya viene pre-cargado, solo hay que seleccionar el radio
    const radioSeleccionado = await this.ejecutarJs<boolean>(`
      (function() {
        var radios = document.querySelectorAll('input[type="radio"]');
        for (var i = 0; i < radios.length; i++) {
          // Buscar el radio de la tabla de periodos (no otros radios)
          if (radios[i].id && radios[i].id.includes('Rejilla')) {
            radios[i].click();
            return true;
          }
        }
        // Fallback: primer radio de cualquier tabla
        var radio = document.querySelector('table input[type="radio"]');
        if (radio) { radio.click(); return true; }
        return false;
      })()
    `)

    if (radioSeleccionado) {
      log.info(`[${this.nombre}] Radio de periodo seleccionado`)
    } else {
      log.warn(`[${this.nombre}] No se encontro radio de periodo — puede fallar al enviar`)
    }
    await this.delay(500)

    // ── Paso 7: Rellenar fecha de nacimiento ──
    const fechaOk = await this.ejecutarJs<boolean>(`
      (function() {
        var campo = document.querySelector('#PeticionInformeRiesgo_CajaParaFechaNacimiento');
        if (!campo) return false;
        campo.focus();
        campo.value = '${this.datosExtra.fechaNacimiento.replace(/'/g, "\\'")}';
        campo.dispatchEvent(new Event('input', { bubbles: true }));
        campo.dispatchEvent(new Event('change', { bubbles: true }));
        campo.blur();
        return true;
      })()
    `)
    if (fechaOk) {
      log.info(`[${this.nombre}] Fecha de nacimiento rellenada: ${this.datosExtra.fechaNacimiento}`)
    } else {
      log.error(`[${this.nombre}] Campo fecha nacimiento no encontrado`)
      return { exito: false, error: 'No se encontro campo de fecha de nacimiento en formulario CIRBE' }
    }

    // ── Paso 8: Rellenar email ──
    const emailOk = await this.ejecutarJs<boolean>(`
      (function() {
        var campo = document.querySelector('#CajaDeTextoCorreoElectronico');
        if (!campo) return false;
        campo.focus();
        campo.value = '${this.datosExtra.email.replace(/'/g, "\\'")}';
        campo.dispatchEvent(new Event('input', { bubbles: true }));
        campo.dispatchEvent(new Event('change', { bubbles: true }));
        campo.blur();
        return true;
      })()
    `)
    if (emailOk) {
      log.info(`[${this.nombre}] Email configurado: ${this.datosExtra.email}`)
    } else {
      log.error(`[${this.nombre}] Campo email no encontrado`)
      return { exito: false, error: 'No se encontro campo de email en formulario CIRBE' }
    }

    // ── Paso 9: Checkbox condiciones de privacidad ──
    await this.ejecutarJs(`
      var cb = document.querySelector('#CheckBoxSimpleCondicionesPrivacidad');
      if (cb && !cb.checked) cb.click();
    `)
    log.info(`[${this.nombre}] Condiciones de privacidad aceptadas`)

    await this.capturarPantalla('03-pre-envio')

    // ── Paso 10: Enviar solicitud ──
    await this.clickElemento('#BotonAceptar')
    await this.delay(4000)

    await this.capturarPantalla('04-post-envio')

    // ── Paso 11: Verificar resultado ──
    const textoResultado = await this.ejecutarJs<string>(`
      (document.body.innerText || '').substring(0, 1000).toLowerCase()
    `)

    const solicitudOk = textoResultado?.includes('solicitud') ||
      textoResultado?.includes('tramitada') ||
      textoResultado?.includes('disponible') ||
      textoResultado?.includes('informaci')

    if (textoResultado?.includes('error') && !solicitudOk) {
      log.error(`[${this.nombre}] Posible error en solicitud`)
      return { exito: false, error: 'Error al enviar solicitud CIRBE. Revisa las capturas de pantalla.' }
    }

    log.info(`[${this.nombre}] Solicitud CIRBE enviada correctamente`)

    return {
      exito: true,
      datos: {
        tipo: 'solicitud',
        mensaje:
          'Solicitud CIRBE enviada. El informe estara disponible en ~15 minutos para descarga.',
        emailDestino: this.datosExtra.email,
      },
    }
  }
}
