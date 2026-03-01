import { readFileSync, writeFileSync, existsSync, renameSync } from 'fs'
import { join } from 'path'
import { app } from 'electron'
import log from 'electron-log'
import type { ResultadoMultiCert } from './orquestador-global'

const ARCHIVO_HISTORIAL = 'certigestor-historial-multicert.json'
const MAX_REGISTROS = 100

function rutaArchivo(): string {
  return join(app.getPath('userData'), ARCHIVO_HISTORIAL)
}

function leerHistorial(): ResultadoMultiCert[] {
  const ruta = rutaArchivo()
  if (!existsSync(ruta)) return []

  try {
    const contenido = readFileSync(ruta, 'utf-8')
    return JSON.parse(contenido) as ResultadoMultiCert[]
  } catch (err) {
    log.warn(`[HistorialMC] Error leyendo: ${(err as Error).message}`)
    return []
  }
}

function guardarHistorialLocal(registros: ResultadoMultiCert[]): void {
  const ruta = rutaArchivo()
  // Mantener solo los ultimos N registros
  const recortado = registros.slice(-MAX_REGISTROS)
  // Escritura atomica: escribir a temp + rename para evitar corrupcion
  const rutaTmp = `${ruta}.tmp`
  writeFileSync(rutaTmp, JSON.stringify(recortado, null, 2), 'utf-8')
  renameSync(rutaTmp, ruta)
}

/** Registra una ejecucion multi-cert en el historial */
export function registrarEjecucion(resultado: ResultadoMultiCert): void {
  const historial = leerHistorial()
  historial.push(resultado)
  guardarHistorialLocal(historial)
  log.info(
    `[HistorialMC] Registrado: ${resultado.certificados.length} certs, ${resultado.duracionMs}ms`,
  )
}

/** Obtiene el historial de ejecuciones multi-cert */
export function obtenerHistorialMultiCert(
  limite?: number,
): ResultadoMultiCert[] {
  const historial = leerHistorial()
  // Devolver mas recientes primero
  const invertido = [...historial].reverse()
  return limite ? invertido.slice(0, limite) : invertido
}

/** Limpia el historial de ejecuciones */
export function limpiarHistorialMultiCert(): void {
  guardarHistorialLocal([])
  log.info('[HistorialMC] Historial limpiado')
}
