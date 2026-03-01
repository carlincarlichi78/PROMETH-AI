import { existsSync } from 'fs'
import { shell } from 'electron'
import log from 'electron-log'
import { aislarCertificado, restaurarCertificado } from '../certs/aislamiento'
import { generarRutaSalida } from './firmador-local'
import type { OpcionesFirmaAutoFirma, ResultadoFirma } from './tipos-firma'

/** Rutas comunes donde se instala AutoFirma en Windows */
const RUTAS_AUTOFIRMA = [
  'C:\\Program Files\\AutoFirma\\AutoFirma.exe',
  'C:\\Program Files (x86)\\AutoFirma\\AutoFirma.exe',
]

/** Timeout para esperar resultado de AutoFirma (ms) */
const TIMEOUT_AUTOFIRMA = 120_000

/**
 * Detecta si AutoFirma esta instalado en el sistema.
 * Busca el ejecutable en las rutas comunes de instalacion.
 */
export async function detectarAutoFirma(): Promise<boolean> {
  for (const ruta of RUTAS_AUTOFIRMA) {
    if (existsSync(ruta)) {
      log.info(`[AutoFirma] Detectado en: ${ruta}`)
      return true
    }
  }

  log.info('[AutoFirma] No detectado en el sistema')
  return false
}

/**
 * Obtiene la ruta del ejecutable de AutoFirma si esta instalado.
 */
export function obtenerRutaAutoFirma(): string | null {
  for (const ruta of RUTAS_AUTOFIRMA) {
    if (existsSync(ruta)) return ruta
  }
  return null
}

/**
 * Construye la URL del protocolo afirma:// para firmar un PDF.
 *
 * El protocolo afirma:// permite invocar AutoFirma desde aplicaciones externas.
 * Formato: afirma://sign?op=sign&format=PAdES&...
 *
 * Nota: Este es un formato simplificado. AutoFirma acepta parametros adicionales
 * como algorithm, extraparams, etc. La implementacion completa se refinara en D9.
 */
function construirUrlAutoFirma(rutaPdf: string, rutaSalida: string): string {
  const params = new URLSearchParams({
    op: 'sign',
    format: 'PAdES',
    algorithm: 'SHA256withRSA',
    inputfile: rutaPdf,
    outputfile: rutaSalida,
  })

  return `afirma://sign?${params.toString()}`
}

/**
 * Firma un PDF usando AutoFirma via protocolo afirma://.
 *
 * Flujo:
 * 1. Aisla el certificado (solo el seleccionado visible para AutoFirma)
 * 2. Invoca AutoFirma via shell.openExternal(afirma://...)
 * 3. Espera a que el archivo firmado aparezca en disco
 * 4. Restaura el certificado al estado normal
 *
 * Nota: Semi-placeholder — el protocolo funciona pero la deteccion de resultado
 * depende de convenciones del sistema. La UI real (D9) completara el flujo
 * con feedback visual y dialogo de confirmacion.
 */
export async function firmarConAutoFirma(
  opciones: OpcionesFirmaAutoFirma,
): Promise<ResultadoFirma> {
  const inicio = Date.now()
  const { rutaPdf, thumbprint, rutaSalida: rutaSalidaOpcional } = opciones
  const rutaSalida = generarRutaSalida(rutaPdf, rutaSalidaOpcional)

  try {
    // Verificar que AutoFirma esta instalado
    const instalado = await detectarAutoFirma()
    if (!instalado) {
      return {
        exito: false,
        modo: 'autofirma',
        error: 'AutoFirma no esta instalado en el sistema',
        tiempoMs: Date.now() - inicio,
      }
    }

    // 1. Aislar certificado para que AutoFirma solo vea el seleccionado
    log.info(`[AutoFirma] Aislando certificado ${thumbprint}`)
    const resultadoAislamiento = await aislarCertificado(thumbprint)

    if (!resultadoAislamiento.exito) {
      return {
        exito: false,
        modo: 'autofirma',
        error: `Error al aislar certificado: ${resultadoAislamiento.error ?? 'desconocido'}`,
        tiempoMs: Date.now() - inicio,
      }
    }

    try {
      // 2. Construir URL y abrir AutoFirma
      const url = construirUrlAutoFirma(rutaPdf, rutaSalida)
      log.info(`[AutoFirma] Invocando protocolo: afirma://sign...`)

      await shell.openExternal(url)

      // 3. Esperar a que el archivo firmado aparezca
      const firmado = await esperarArchivoFirmado(rutaSalida, TIMEOUT_AUTOFIRMA)

      if (!firmado) {
        return {
          exito: false,
          modo: 'autofirma',
          error: `Timeout esperando resultado de AutoFirma (${TIMEOUT_AUTOFIRMA / 1000}s)`,
          tiempoMs: Date.now() - inicio,
        }
      }

      const tiempoMs = Date.now() - inicio
      log.info(`[AutoFirma] PDF firmado correctamente en ${tiempoMs}ms`)

      return {
        exito: true,
        modo: 'autofirma',
        rutaPdfFirmado: rutaSalida,
        tiempoMs,
      }
    } finally {
      // 4. SIEMPRE restaurar el certificado, exito o error
      log.info(`[AutoFirma] Restaurando certificado ${thumbprint}`)
      const resultadoRestauracion = await restaurarCertificado(thumbprint)

      if (!resultadoRestauracion.exito) {
        log.error(`[AutoFirma] Error al restaurar certificado: ${resultadoRestauracion.error}`)
      }
    }
  } catch (error) {
    const mensaje = error instanceof Error ? error.message : 'Error desconocido en AutoFirma'
    log.error('[AutoFirma] Error:', mensaje)

    return {
      exito: false,
      modo: 'autofirma',
      error: mensaje,
      tiempoMs: Date.now() - inicio,
    }
  }
}

/**
 * Espera a que un archivo aparezca en disco (polling).
 * AutoFirma escribe el resultado cuando termina.
 */
async function esperarArchivoFirmado(ruta: string, timeoutMs: number): Promise<boolean> {
  const intervalo = 1_000
  const intentosMax = Math.ceil(timeoutMs / intervalo)

  for (let i = 0; i < intentosMax; i++) {
    if (existsSync(ruta)) {
      return true
    }
    await new Promise((resolve) => setTimeout(resolve, intervalo))
  }

  return false
}
