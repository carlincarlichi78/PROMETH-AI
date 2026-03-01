import { readFileSync, writeFileSync, existsSync, renameSync } from 'fs'
import { join } from 'path'
import { app } from 'electron'
import log from 'electron-log'
import type { RegistroHistorialDescarga, ConfigDocumentosLocal, TipoDocumento } from './tipos-documentales'
import { documentosPorDefecto } from './catalogo'

const ARCHIVO_HISTORIAL = 'certigestor-historial-docs.json'
const ARCHIVO_CONFIG = 'certigestor-config-docs.json'

function rutaArchivo(nombre: string): string {
  return join(app.getPath('userData'), nombre)
}

// ── Historial de descargas ─────────────────────────────────

function leerHistorial(): RegistroHistorialDescarga[] {
  const ruta = rutaArchivo(ARCHIVO_HISTORIAL)
  if (!existsSync(ruta)) return []

  try {
    const contenido = readFileSync(ruta, 'utf-8')
    return JSON.parse(contenido) as RegistroHistorialDescarga[]
  } catch (err) {
    log.warn(`[Historial] Error leyendo historial: ${(err as Error).message}`)
    return []
  }
}

function guardarHistorial(registros: RegistroHistorialDescarga[]): void {
  const ruta = rutaArchivo(ARCHIVO_HISTORIAL)
  // Limitar a ultimos 500 registros para evitar crecimiento ilimitado
  const recortado = registros.length > 500 ? registros.slice(-500) : registros
  // Escritura atomica: escribir a temp + rename para evitar corrupcion
  const rutaTmp = `${ruta}.tmp`
  writeFileSync(rutaTmp, JSON.stringify(recortado, null, 2), 'utf-8')
  renameSync(rutaTmp, ruta)
}

/** Registra una descarga en el historial local */
export function registrarDescarga(registro: RegistroHistorialDescarga): void {
  const historial = leerHistorial()
  historial.push(registro)
  guardarHistorial(historial)
  log.info(`[Historial] Registrado: ${registro.tipo} — ${registro.exito ? 'OK' : 'ERROR'}`)
}

/** Obtiene historial filtrado por certificado (o todo) */
export function obtenerHistorial(
  certificadoSerial?: string,
): RegistroHistorialDescarga[] {
  const historial = leerHistorial()
  if (!certificadoSerial) return historial
  return historial.filter((r) => r.certificadoSerial === certificadoSerial)
}

/** Obtiene el ultimo resultado de cada tipo de documento (para indicadores dinamicos) */
export function obtenerUltimosResultados(
  certificadoSerial?: string,
): Record<string, { exito: boolean; fecha: string; error?: string }> {
  const historial = leerHistorial()
  const filtrado = certificadoSerial
    ? historial.filter((r) => r.certificadoSerial === certificadoSerial)
    : historial

  const ultimos: Record<string, { exito: boolean; fecha: string; error?: string }> = {}
  // Recorrer de mas antiguo a mas reciente → el ultimo sobreescribe
  for (const reg of filtrado) {
    ultimos[reg.tipo] = {
      exito: reg.exito,
      fecha: reg.fechaDescarga,
      error: reg.error,
    }
  }
  return ultimos
}

/** Limpia todo el historial */
export function limpiarHistorial(): void {
  guardarHistorial([])
  log.info('[Historial] Historial limpiado')
}

// ── Config de documentos por certificado ───────────────────

function leerConfigLocal(): ConfigDocumentosLocal {
  const ruta = rutaArchivo(ARCHIVO_CONFIG)
  if (!existsSync(ruta)) return {}

  try {
    const contenido = readFileSync(ruta, 'utf-8')
    return JSON.parse(contenido) as ConfigDocumentosLocal
  } catch (err) {
    log.warn(`[Config] Error leyendo config: ${(err as Error).message}`)
    return {}
  }
}

function guardarConfigLocal(config: ConfigDocumentosLocal): void {
  const ruta = rutaArchivo(ARCHIVO_CONFIG)
  writeFileSync(ruta, JSON.stringify(config, null, 2), 'utf-8')
}

/** Obtiene la config de documentos activos para un certificado */
export function obtenerConfig(
  certificadoSerial: string,
): { documentosActivos: TipoDocumento[]; datosExtra?: Record<string, unknown> } {
  const config = leerConfigLocal()
  return config[certificadoSerial] ?? {
    documentosActivos: documentosPorDefecto(),
  }
}

/** Obtiene todas las configs de documentos (para sync cloud) */
export function obtenerTodasLasConfigs(): ConfigDocumentosLocal {
  return leerConfigLocal()
}

/** Guarda la config de documentos activos para un certificado */
export function guardarConfig(
  certificadoSerial: string,
  documentosActivos: TipoDocumento[],
  datosExtra?: Record<string, unknown>,
): void {
  const config = leerConfigLocal()
  config[certificadoSerial] = { documentosActivos, datosExtra }
  guardarConfigLocal(config)
  log.info(`[Config] Guardada config para cert: ${certificadoSerial} — ${documentosActivos.length} docs activos`)
}
