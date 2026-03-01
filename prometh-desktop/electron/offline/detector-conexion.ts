import { net } from 'electron'
import log from 'electron-log'

type CallbackConexion = (conectado: boolean) => void

let conectado = true
let intervalo: ReturnType<typeof setInterval> | null = null
const listeners: Set<CallbackConexion> = new Set()

const INTERVALO_MS = 30_000
const TIMEOUT_MS = 5_000

async function verificarConexion(urlPing: string): Promise<boolean> {
  try {
    if (!net.isOnline()) return false
    const ctrl = new AbortController()
    const timeout = setTimeout(() => ctrl.abort(), TIMEOUT_MS)
    const resp = await fetch(urlPing, { signal: ctrl.signal, method: 'HEAD' })
    clearTimeout(timeout)
    return resp.ok
  } catch {
    return false
  }
}

export function iniciarDetectorConexion(urlPing: string, callback?: CallbackConexion): void {
  if (callback) listeners.add(callback)
  if (intervalo) return

  intervalo = setInterval(async () => {
    const conectadoAhora = await verificarConexion(urlPing)
    if (conectadoAhora !== conectado) {
      conectado = conectadoAhora
      log.info(`[Conexion] ${conectadoAhora ? 'ONLINE' : 'OFFLINE'}`)
      listeners.forEach(cb => cb(conectadoAhora))
    }
  }, INTERVALO_MS)

  // Verificación inicial inmediata
  verificarConexion(urlPing).then(online => {
    conectado = online
    listeners.forEach(cb => cb(online))
  })
}

export function detenerDetectorConexion(): void {
  if (intervalo) {
    clearInterval(intervalo)
    intervalo = null
  }
  listeners.clear()
}

export function estaOnline(): boolean {
  return conectado
}

export function agregarListenerConexion(callback: CallbackConexion): void {
  listeners.add(callback)
}

export function removerListenerConexion(callback: CallbackConexion): void {
  listeners.delete(callback)
}
