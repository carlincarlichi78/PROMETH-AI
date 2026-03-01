import { existsSync, readFileSync, writeFileSync, mkdirSync, renameSync } from 'fs'
import { join, dirname } from 'path'
import { app } from 'electron'
import log from 'electron-log'
import type { DocumentoFirmadoLocal, HistorialFirmasLocal } from './tipos-firma'

const NOMBRE_ARCHIVO = 'certigestor-historial-firmas.json'

/** Obtiene la ruta completa del archivo de historial */
function obtenerRutaArchivo(): string {
  return join(app.getPath('userData'), NOMBRE_ARCHIVO)
}

/** Historial vacio por defecto */
function crearHistorialVacio(): HistorialFirmasLocal {
  return { documentos: [] }
}

/**
 * Lee el historial de firmas locales desde el archivo JSON.
 * Si no existe, retorna historial vacio.
 */
export function obtenerHistorialFirmas(): HistorialFirmasLocal {
  const ruta = obtenerRutaArchivo()

  if (!existsSync(ruta)) {
    return crearHistorialVacio()
  }

  try {
    const contenido = readFileSync(ruta, 'utf-8')
    const datos: HistorialFirmasLocal = JSON.parse(contenido)
    return datos
  } catch (error) {
    log.warn('[HistorialFirmas] Error leyendo historial, creando nuevo:', error)
    return crearHistorialVacio()
  }
}

/**
 * Guarda el historial completo en el archivo JSON.
 */
function guardarHistorial(historial: HistorialFirmasLocal): void {
  const ruta = obtenerRutaArchivo()
  const directorio = dirname(ruta)

  if (!existsSync(directorio)) {
    mkdirSync(directorio, { recursive: true })
  }

  // Escritura atomica: escribir a temp + rename para evitar corrupcion
  const rutaTmp = `${ruta}.tmp`
  writeFileSync(rutaTmp, JSON.stringify(historial, null, 2), 'utf-8')
  renameSync(rutaTmp, ruta)
}

/**
 * Registra un documento firmado en el historial local.
 * Inmutable: crea nuevo array con el documento añadido.
 */
export function registrarFirma(documento: DocumentoFirmadoLocal): void {
  const historial = obtenerHistorialFirmas()

  const nuevoHistorial: HistorialFirmasLocal = {
    documentos: [...historial.documentos, documento],
  }

  guardarHistorial(nuevoHistorial)
  log.info(`[HistorialFirmas] Firma registrada: ${documento.id}`)
}

/**
 * Obtiene firmas pendientes de sincronizar con cloud.
 * Filtra documentos donde sincronizadoCloud === false.
 */
export function obtenerFirmasPendienteSync(): DocumentoFirmadoLocal[] {
  const historial = obtenerHistorialFirmas()
  return historial.documentos.filter((doc) => !doc.sincronizadoCloud)
}

/**
 * Marca una firma como sincronizada con cloud.
 * Inmutable: crea nuevo array con el documento actualizado.
 */
export function marcarSincronizado(id: string): void {
  const historial = obtenerHistorialFirmas()

  const nuevoHistorial: HistorialFirmasLocal = {
    documentos: historial.documentos.map((doc) =>
      doc.id === id ? { ...doc, sincronizadoCloud: true } : doc,
    ),
  }

  guardarHistorial(nuevoHistorial)
  log.info(`[HistorialFirmas] Firma marcada como sincronizada: ${id}`)
}

/**
 * Obtiene el numero total de firmas en el historial.
 */
export function contarFirmas(): number {
  const historial = obtenerHistorialFirmas()
  return historial.documentos.length
}
