/**
 * Configuración de conexión con PROMETH-AI API.
 * Se persiste en el store de Electron (electron-store / better-sqlite3).
 */

export interface ConfigPromethAI {
  /** URL base de la instancia PROMETH-AI. Ej: "https://api.prometh-ai.es" */
  apiUrl: string
  /** Secreto HMAC compartido con el servidor para autenticar el webhook */
  webhookSecret: string
  /** JWT del gestor autenticado en PROMETH-AI */
  token: string
  /** CIFs de las empresas que gestiona este desktop */
  empresasCif: string[]
}

export const CONFIG_DEFAULTS: ConfigPromethAI = {
  apiUrl: 'https://api.prometh-ai.es',
  webhookSecret: '',
  token: '',
  empresasCif: [],
}

/** Clave usada en el store de configuración de Electron */
export const CONFIG_KEY = 'promethAI' as const
