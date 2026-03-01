import { readFileSync, writeFileSync, existsSync } from 'fs'
import { join } from 'path'
import { app } from 'electron'
import log from 'electron-log'
import type { ConfigPortalesCertificado, ConfigPortalesLocal } from './tipos-notificaciones'
import { PortalNotificaciones } from './tipos-notificaciones'

const ARCHIVO_CONFIG_PORTALES = 'certigestor-config-portales.json'

/** Portales activos por defecto (solo DEHU) */
export const PORTALES_POR_DEFECTO: readonly PortalNotificaciones[] = [
  PortalNotificaciones.DEHU,
]

function rutaArchivo(): string {
  return join(app.getPath('userData'), ARCHIVO_CONFIG_PORTALES)
}

function leerConfigPortales(): ConfigPortalesLocal {
  const ruta = rutaArchivo()
  if (!existsSync(ruta)) return {}

  try {
    const contenido = readFileSync(ruta, 'utf-8')
    return JSON.parse(contenido) as ConfigPortalesLocal
  } catch (err) {
    log.warn(`[ConfigPortales] Error leyendo config: ${(err as Error).message}`)
    return {}
  }
}

function guardarConfigPortales(config: ConfigPortalesLocal): void {
  const ruta = rutaArchivo()
  writeFileSync(ruta, JSON.stringify(config, null, 2), 'utf-8')
}

/** Obtiene los portales activos para un certificado */
export function obtenerConfigPortales(
  certificadoSerial: string,
): ConfigPortalesCertificado {
  const config = leerConfigPortales()
  return config[certificadoSerial] ?? {
    portalesActivos: [...PORTALES_POR_DEFECTO],
  }
}

/** Guarda los portales activos para un certificado */
export function guardarConfigPortalesCert(
  certificadoSerial: string,
  portalesActivos: PortalNotificaciones[],
  datosPortal?: ConfigPortalesCertificado['datosPortal'],
): void {
  const config = leerConfigPortales()
  const configActualizada: ConfigPortalesLocal = {
    ...config,
    [certificadoSerial]: { portalesActivos, datosPortal },
  }
  guardarConfigPortales(configActualizada)
  log.info(
    `[ConfigPortales] Guardado cert: ${certificadoSerial} — portales: ${portalesActivos.join(', ')}`,
  )
}
