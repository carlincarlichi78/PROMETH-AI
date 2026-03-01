import { existsSync, readFileSync, writeFileSync, mkdirSync, renameSync } from 'fs'
import { join, dirname } from 'path'
import { app } from 'electron'
import log from 'electron-log'
import type {
  DatosNotificacionesDesktop,
  NotificacionDesktop,
  ConfigNotificacionesDesktop,
  EstadoTray,
} from './tipos-tray'

const NOMBRE_ARCHIVO = 'certigestor-notificaciones-desktop.json'

function obtenerRutaArchivo(): string {
  return join(app.getPath('userData'), NOMBRE_ARCHIVO)
}

const CONFIG_DEFAULT: ConfigNotificacionesDesktop = {
  nativasActivas: true,
  diasAvisoCaducidad: 30,
  notificarScraping: true,
  notificarWorkflows: true,
  notificarSync: true,
  sonido: true,
}

function crearDatosVacios(): DatosNotificacionesDesktop {
  return {
    notificaciones: [],
    config: { ...CONFIG_DEFAULT },
  }
}

export function obtenerDatos(): DatosNotificacionesDesktop {
  const ruta = obtenerRutaArchivo()

  if (!existsSync(ruta)) {
    return crearDatosVacios()
  }

  try {
    const contenido = readFileSync(ruta, 'utf-8')
    const datos: DatosNotificacionesDesktop = JSON.parse(contenido)
    return datos
  } catch (error) {
    log.warn('[Tray] Error leyendo datos, creando nuevos:', error)
    return crearDatosVacios()
  }
}

function guardarDatos(datos: DatosNotificacionesDesktop): void {
  const ruta = obtenerRutaArchivo()
  const directorio = dirname(ruta)

  if (!existsSync(directorio)) {
    mkdirSync(directorio, { recursive: true })
  }

  // Escritura atomica: escribir a temp + rename para evitar corrupcion
  const rutaTmp = `${ruta}.tmp`
  writeFileSync(rutaTmp, JSON.stringify(datos, null, 2), 'utf-8')
  renameSync(rutaTmp, ruta)
}

// --- Notificaciones ---

export function agregarNotificacion(notif: NotificacionDesktop): void {
  const datos = obtenerDatos()
  guardarDatos({
    ...datos,
    notificaciones: [...datos.notificaciones, notif],
  })
  log.info(`[Tray] Notificacion agregada: ${notif.titulo} (${notif.tipo})`)
}

export function obtenerNotificaciones(limite: number = 50): NotificacionDesktop[] {
  const datos = obtenerDatos()
  return datos.notificaciones.slice(-limite).reverse()
}

export function marcarLeida(id: string): boolean {
  const datos = obtenerDatos()
  const notif = datos.notificaciones.find((n) => n.id === id)
  if (!notif || notif.leida) return false

  guardarDatos({
    ...datos,
    notificaciones: datos.notificaciones.map((n) =>
      n.id === id ? { ...n, leida: true } : n
    ),
  })
  return true
}

export function marcarTodasLeidas(): number {
  const datos = obtenerDatos()
  const pendientes = datos.notificaciones.filter((n) => !n.leida)
  if (pendientes.length === 0) return 0

  guardarDatos({
    ...datos,
    notificaciones: datos.notificaciones.map((n) => ({ ...n, leida: true })),
  })
  return pendientes.length
}

export function obtenerEstadoTray(): EstadoTray {
  const datos = obtenerDatos()
  const pendientes = datos.notificaciones.filter((n) => !n.leida).length
  const ultima = datos.notificaciones[datos.notificaciones.length - 1]
  return {
    pendientes,
    ultimaNotificacion: ultima?.fechaCreacion,
  }
}

export function limpiarAntiguas(mantener: number = 200): number {
  const datos = obtenerDatos()
  const total = datos.notificaciones.length
  if (total <= mantener) return 0

  const eliminadas = total - mantener
  guardarDatos({
    ...datos,
    notificaciones: datos.notificaciones.slice(-mantener),
  })

  log.info(`[Tray] ${eliminadas} notificaciones antiguas eliminadas`)
  return eliminadas
}

// --- Config ---

export function obtenerConfig(): ConfigNotificacionesDesktop {
  return obtenerDatos().config
}

export function guardarConfig(config: ConfigNotificacionesDesktop): void {
  const datos = obtenerDatos()
  guardarDatos({ ...datos, config })
  log.info('[Tray] Config guardada')
}
