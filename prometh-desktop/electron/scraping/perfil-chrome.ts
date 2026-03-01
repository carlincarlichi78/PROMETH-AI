import { existsSync, mkdirSync, readdirSync } from 'fs'
import { join } from 'path'
import { app } from 'electron'
import log from 'electron-log'

// Rutas estandar de Chrome en Windows
const RUTAS_CHROME_WINDOWS = [
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
  `${process.env.LOCALAPPDATA}\\Google\\Chrome\\Application\\chrome.exe`,
]

// Control de perfiles ocupados
const perfilesOcupados = new Set<string>()

/**
 * Detecta la ruta del ejecutable de Chrome instalado en Windows.
 * Busca en las rutas estandar del sistema.
 */
export function detectarChrome(): string | null {
  for (const ruta of RUTAS_CHROME_WINDOWS) {
    if (existsSync(ruta)) {
      log.info(`Chrome encontrado en: ${ruta}`)
      return ruta
    }
  }
  log.warn('Chrome no encontrado en rutas estandar')
  return null
}

/**
 * Directorio base donde se guardan los perfiles de Chrome para scraping.
 */
function directorioPerfiles(): string {
  const dir = join(app.getPath('userData'), 'chrome-profiles')
  if (!existsSync(dir)) {
    mkdirSync(dir, { recursive: true })
  }
  return dir
}

/**
 * Crea un perfil de Chrome para scraping.
 * Cada perfil es un directorio independiente que mantiene cookies y sesion.
 */
export function crearPerfil(nombre: string): string {
  const ruta = join(directorioPerfiles(), nombre)
  if (!existsSync(ruta)) {
    mkdirSync(ruta, { recursive: true })
    log.info(`Perfil Chrome creado: ${nombre}`)
  }
  return ruta
}

/**
 * Lista todos los perfiles disponibles.
 */
export function listarPerfiles(): string[] {
  const dir = directorioPerfiles()
  try {
    return readdirSync(dir, { withFileTypes: true })
      .filter((e) => e.isDirectory())
      .map((e) => e.name)
  } catch {
    return []
  }
}

/**
 * Obtiene un perfil disponible (no ocupado) para scraping concurrente.
 * Si no hay perfiles disponibles, crea uno nuevo.
 */
export function obtenerPerfilDisponible(): string {
  const perfiles = listarPerfiles()
  const disponible = perfiles.find((p) => !perfilesOcupados.has(p))

  if (disponible) {
    return crearPerfil(disponible)
  }

  // Crear nuevo perfil con nombre incremental
  const nuevoNombre = `perfil-${perfiles.length + 1}`
  return crearPerfil(nuevoNombre)
}

/**
 * Marca un perfil como ocupado (en uso por un scraper).
 */
export function marcarPerfilOcupado(nombre: string): void {
  perfilesOcupados.add(nombre)
}

/**
 * Libera un perfil para que pueda ser reutilizado.
 */
export function liberarPerfil(nombre: string): void {
  perfilesOcupados.delete(nombre)
}

/**
 * Obtiene el nombre del perfil a partir de su ruta completa.
 */
export function nombreDesdePerfil(rutaPerfil: string): string {
  return rutaPerfil.split(/[/\\]/).pop() ?? 'default'
}
