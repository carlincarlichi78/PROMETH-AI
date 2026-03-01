import log from 'electron-log'
import type { BaseScraperDocumental } from '../base-scraper-documental'

/**
 * Login compartido en el portal de Seguridad Social (importass).
 *
 * Flujo:
 * 1. Modal "Elige tu metodo de identificacion" → radio ya seleccionado → "Continuar"
 * 2. idp.seg-social.es/PGIS/Login → clic "DNIe o certificado"
 * 3. ipce.seg-social.es → select-client-certificate automatico
 * 4. Redireccion al servicio solicitado
 */
export async function loginSeguridadSocial(
  scraper: BaseScraperDocumental,
): Promise<void> {
  log.info('[Login SS] Iniciando autenticacion con certificado')

  // Verificar URL actual
  const urlInicial = await scraper.ejecutarJs<string>('window.location.href')
  log.info(`[Login SS] URL inicial: ${urlInicial}`)

  // Paso 1: Clic en "Continuar" si aparece el modal de metodo de identificacion
  const clicContinuar = await scraper.ejecutarJs<boolean>(`
    (function() {
      var botones = document.querySelectorAll('button');
      for (var i = 0; i < botones.length; i++) {
        var texto = (botones[i].textContent || '').trim().toLowerCase();
        if (texto === 'continuar' || texto.includes('continuar')) {
          botones[i].click();
          return true;
        }
      }
      return false;
    })()
  `)

  if (clicContinuar) {
    log.info('[Login SS] Clic en "Continuar" del modal de identificacion')
    await scraper.delay(4000)
  }

  // Capturar estado actual
  await scraper.capturarPantalla('login-ss-01-post-continuar')

  // Verificar donde estamos
  const urlPostContinuar = await scraper.ejecutarJs<string>('window.location.href')
  log.info(`[Login SS] URL post-continuar: ${urlPostContinuar}`)

  // Si ya estamos autenticados (no en pasarela de login), salir
  if (!urlPostContinuar.includes('idp.seg-social') &&
      !urlPostContinuar.includes('ipce.seg-social') &&
      !urlPostContinuar.includes('clave.gob.es') &&
      !urlPostContinuar.includes('importass')) {
    log.info('[Login SS] Ya autenticados, no se requiere login')
    return
  }

  // Paso 2: Buscar y hacer clic en "DNIe o certificado"
  // Listar todos los botones para debug
  const botonesDisponibles = await scraper.ejecutarJs<string>(`
    (function() {
      var resultado = [];
      var elementos = document.querySelectorAll('button, a, input[type="submit"]');
      for (var i = 0; i < Math.min(elementos.length, 15); i++) {
        resultado.push({
          tag: elementos[i].tagName,
          texto: (elementos[i].textContent || '').trim().substring(0, 60),
          href: elementos[i].getAttribute('href') || '',
          formaction: elementos[i].getAttribute('formaction') || '',
        });
      }
      return JSON.stringify(resultado);
    })()
  `)
  log.info(`[Login SS] Botones disponibles: ${botonesDisponibles}`)

  const clicDnie = await scraper.ejecutarJs<boolean>(`
    (function() {
      // Interfaz nueva 2026: boton con ID fijo #IPCEIdP
      var btn = document.querySelector('#IPCEIdP');
      if (btn) { btn.click(); return true; }
      // Patron Findiur: boton con formaction IPCE (selector mas fiable)
      btn = document.querySelector("button[formaction*='seleccion=IPCE']");
      if (btn) { btn.click(); return true; }
      // Fallback: formaction generico IPCE
      btn = document.querySelector("button[formaction*='IPCE'], button[formaction*='ipce']");
      if (btn) { btn.click(); return true; }
      // Fallback 2: buscar por texto
      var botones = document.querySelectorAll('button, a');
      for (var i = 0; i < botones.length; i++) {
        var texto = (botones[i].textContent || '').toLowerCase();
        if (texto.includes('dnie') || texto.includes('certificado electr') ||
            texto.includes('certificado digital') || texto.includes('certificado software')) {
          botones[i].click();
          return true;
        }
      }
      // Fallback 3: link con href IPCE
      var links = document.querySelectorAll('a');
      for (var j = 0; j < links.length; j++) {
        var href = links[j].getAttribute('href') || '';
        if (href.includes('IPCE') || href.includes('ipce')) {
          links[j].click();
          return true;
        }
      }
      return false;
    })()
  `)

  if (clicDnie) {
    log.info('[Login SS] Clic en "DNIe o certificado" — esperando select-client-certificate')
    await scraper.delay(5000)
  } else {
    log.warn('[Login SS] Boton DNIe no encontrado — intentando pasarela Cl@ve')
    await scraper.capturarPantalla('login-ss-02-sin-boton-dnie')
    await scraper.manejarPasarelaClave(15_000, 30_000)
    await scraper.delay(3000)
  }

  await scraper.capturarPantalla('login-ss-03-post-dnie-click')

  // Paso 3: Esperar que la autenticacion se complete y nos redirija al servicio
  const urlPostDnie = await scraper.ejecutarJs<string>('window.location.href')
  log.info(`[Login SS] URL post-DNIe: ${urlPostDnie}`)

  if (urlPostDnie.includes('idp.seg-social.es') ||
      urlPostDnie.includes('ipce.seg-social.es') ||
      urlPostDnie.includes('clave.gob.es')) {
    log.info('[Login SS] Aun en pasarela — esperando redireccion...')
    const inicio = Date.now()
    while (Date.now() - inicio < 20_000) {
      await scraper.delay(1000)
      const url = await scraper.ejecutarJs<string>('window.location.href')
      if (!url.includes('idp.seg-social.es') &&
          !url.includes('ipce.seg-social.es') &&
          !url.includes('clave.gob.es')) {
        log.info(`[Login SS] Redireccion completada: ${url}`)
        break
      }
    }
  }

  await scraper.delay(3000)
  await scraper.capturarPantalla('login-ss-04-final')
  const urlFinal = await scraper.ejecutarJs<string>('window.location.href')
  log.info(`[Login SS] URL final: ${urlFinal}`)
  log.info('[Login SS] Autenticacion completada')
}
