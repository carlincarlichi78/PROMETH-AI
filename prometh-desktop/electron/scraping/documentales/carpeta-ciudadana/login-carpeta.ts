import log from 'electron-log'
import type { BaseScraperDocumental } from '../base-scraper-documental'

/**
 * Login compartido en Carpeta Ciudadana via Cl@ve con certificado electronico.
 * Selecciona identificacion con certificado (AFIRMA/AutoFirma) y espera
 * la redireccion de vuelta al portal autenticado.
 */
export async function loginCarpetaCiudadana(
  scraper: BaseScraperDocumental,
): Promise<void> {
  log.info('[Login Carpeta] Iniciando autenticacion con certificado')

  // Paso 1: Cerrar banner de cookies si aparece
  await scraper.cerrarModalSiExiste('button.cc-boton-aceptar')

  // Paso 2: Buscar boton de identificacion con Cl@ve
  const botonExiste = await scraper.ejecutarJs(`
    !!document.querySelector('button.botonIdentificateClave, #botonIdentificateClave, a[href*="clave"], .boton-acceso')
  `)

  if (!botonExiste) {
    // Si no hay boton, puede que ya estemos autenticados (redirect automatico)
    const url = await scraper.obtenerURL()
    if (url.includes('/carpeta/')) {
      log.info('[Login Carpeta] Ya autenticado — sesion activa')
      return
    }
    // Intentar con manejarPasarelaClave como fallback
    log.info('[Login Carpeta] Sin boton de login — intentando pasarela Cl@ve')
    await scraper.manejarPasarelaClave()
    await esperarSesionActiva(scraper)
    return
  }

  // Paso 3: Click en boton de identificacion
  try {
    await scraper.clickElemento(
      "button.botonIdentificateClave[onclick='redirect();']",
    )
  } catch {
    try {
      await scraper.clickElemento('button.botonIdentificateClave')
    } catch {
      await scraper.clickElemento('#botonIdentificateClave, .boton-acceso')
    }
  }

  // Paso 4: Esperar segunda pantalla o redireccion a Cl@ve
  await scraper.delay(2000)
  const urlActual = await scraper.obtenerURL()

  if (urlActual.includes('clave.gob.es') || urlActual.includes('pasarela')) {
    // Ya estamos en la pasarela Cl@ve
    await scraper.manejarPasarelaClave()
  } else if (urlActual.includes('carpetaciudadana.gob.es')) {
    // Puede haber un segundo boton de acceso
    try {
      await scraper.esperarSelector('#botonIdentificateClave.boton-acceso', 5_000)
      await scraper.clickElemento('#botonIdentificateClave.boton-acceso')
      await scraper.delay(2000)

      // Ahora deberiamos estar en Cl@ve
      await scraper.manejarPasarelaClave()
    } catch {
      // Si no hay segundo boton, intentar pasarela directamente
      await scraper.manejarPasarelaClave()
    }
  }

  // Paso 5: Esperar redireccion post-autenticacion al portal autenticado
  await esperarSesionActiva(scraper)

  // Paso 6: Aceptar terminos y condiciones si aparecen
  await scraper.cerrarModalSiExiste(
    '#botonesCondiciones button, .aceptar-condiciones',
  )

  log.info('[Login Carpeta] Autenticacion completada')
}

/** Espera hasta que la URL contenga /carpeta/ (sesion autenticada) con timeout */
async function esperarSesionActiva(
  scraper: BaseScraperDocumental,
  timeout = 30_000,
): Promise<void> {
  const inicio = Date.now()
  while (Date.now() - inicio < timeout) {
    const url = await scraper.obtenerURL()
    if (url.includes('/carpeta/') && !url.includes('clave.gob.es')) {
      return
    }
    await scraper.delay(1000)
  }
  // Si no llega, continuamos de todas formas (puede funcionar si la sesion esta en cookies)
  log.warn('[Login Carpeta] Timeout esperando sesion activa — continuando')
}
