/**
 * Handlers IPC para la configuración de PROMETH-AI.
 * Persiste la config en un archivo JSON junto a los datos de la app.
 */
import { ipcMain, app } from 'electron'
import { join } from 'path'
import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'fs'
import log from 'electron-log'
import {
  CONFIG_DEFAULTS,
  type ConfigPromethAI,
} from '../config/prometh-ai.config'
import { probarConexionPromethAI } from '../api/cliente-prometh-ai'

const CONFIG_PATH = join(app.getPath('userData'), 'prometh-ai-config.json')

function leerConfig(): ConfigPromethAI {
  try {
    if (!existsSync(CONFIG_PATH)) return { ...CONFIG_DEFAULTS }
    const raw = readFileSync(CONFIG_PATH, 'utf-8')
    return { ...CONFIG_DEFAULTS, ...JSON.parse(raw) }
  } catch {
    return { ...CONFIG_DEFAULTS }
  }
}

function guardarConfig(config: ConfigPromethAI): void {
  const dir = app.getPath('userData')
  if (!existsSync(dir)) mkdirSync(dir, { recursive: true })
  writeFileSync(CONFIG_PATH, JSON.stringify(config, null, 2), 'utf-8')
}

export function registrarHandlersConfigPromethAI(): void {
  /** Leer config actual */
  ipcMain.handle('prometh-ai:config:leer', () => {
    return leerConfig()
  })

  /** Guardar config (desde pantalla de configuración) */
  ipcMain.handle('prometh-ai:config:guardar', (_, config: Partial<ConfigPromethAI>) => {
    const actual = leerConfig()
    const nueva = { ...actual, ...config }
    guardarConfig(nueva)
    log.info('[PromethAI] Configuración guardada: apiUrl=%s', nueva.apiUrl)
    return { ok: true }
  })

  /** Probar conexión con la instancia PROMETH-AI */
  ipcMain.handle('prometh-ai:config:probar-conexion', async (_, apiUrl: string) => {
    const ok = await probarConexionPromethAI(apiUrl)
    return { ok }
  })

  /** Obtener config para uso interno del main process */
  ipcMain.handle('prometh-ai:config:obtener-para-sync', () => {
    const config = leerConfig()
    // No exponer el secreto HMAC a la UI por seguridad
    return {
      apiUrl: config.apiUrl,
      token: config.token,
      empresasCif: config.empresasCif,
    }
  })
}

/** Obtiene la config directamente en el main process (sin IPC). */
export function obtenerConfigPromethAI(): ConfigPromethAI {
  return leerConfig()
}
