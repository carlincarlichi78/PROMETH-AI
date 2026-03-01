import { app } from 'electron'
import { createHash } from 'crypto'
import nodeMachineId from 'node-machine-id'
const { machineIdSync } = nodeMachineId
import log from 'electron-log'
import type { EventoLocal, ConfigTelemetria, EstadoTelemetria } from './tipos-telemetria'

const INTERVALO_DEFAULT = 5 * 60 * 1000 // 5 minutos
const MAX_COLA = 500

/** Hash anonimo estable por maquina */
function generarHashInstalacion(): string {
  try {
    const id = machineIdSync(true)
    return createHash('sha256').update(id).digest('hex').slice(0, 32)
  } catch {
    // Fallback si machineId falla (ej: permisos)
    return createHash('sha256')
      .update(`${process.platform}-${app.getPath('userData')}`)
      .digest('hex')
      .slice(0, 32)
  }
}

class ClienteTelemetria {
  private cola: Array<{
    evento: string
    version: string
    plataforma: string
    propiedades?: Record<string, unknown>
    hashInstalacion: string
    timestamp: string
  }> = []

  private config: ConfigTelemetria = {
    apiUrl: 'https://carloscanetegomez.dev/certigestor/api/telemetria',
    intervaloFlush: INTERVALO_DEFAULT,
    optOut: false,
  }

  private hashInstalacion: string = ''
  private timer: ReturnType<typeof setInterval> | null = null
  private ultimoEnvio: string | null = null

  /** Inicializar cliente — llamar una vez desde main */
  iniciar(opciones?: Partial<ConfigTelemetria>): void {
    if (opciones) {
      this.config = { ...this.config, ...opciones }
    }

    this.hashInstalacion = generarHashInstalacion()

    // Programar flush periodico
    this.timer = setInterval(() => {
      this.flush().catch((err) => log.warn('[telemetria] Error flush:', err))
    }, this.config.intervaloFlush)

    log.info(`[telemetria] Cliente iniciado (hash: ${this.hashInstalacion.slice(0, 8)}..., optOut: ${this.config.optOut})`)

    // Evento de inicio de app
    this.registrar('app:inicio')
  }

  /** Detener cliente y hacer flush final */
  async detener(): Promise<void> {
    if (this.timer) {
      clearInterval(this.timer)
      this.timer = null
    }
    await this.flush()
    log.info('[telemetria] Cliente detenido')
  }

  /** Registrar un evento en la cola */
  registrar(evento: string, propiedades?: Record<string, unknown>): void {
    if (this.config.optOut) return
    if (this.cola.length >= MAX_COLA) {
      // Descartar eventos mas antiguos si la cola esta llena
      this.cola.shift()
    }

    this.cola.push({
      evento,
      version: app.getVersion(),
      plataforma: process.platform,
      propiedades,
      hashInstalacion: this.hashInstalacion,
      timestamp: new Date().toISOString(),
    })
  }

  /** Enviar eventos pendientes al servidor */
  async flush(): Promise<void> {
    if (this.config.optOut || this.cola.length === 0) return

    const batch = [...this.cola]
    this.cola = []

    try {
      const respuesta = await fetch(this.config.apiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ eventos: batch }),
        signal: AbortSignal.timeout(10000),
      })

      if (!respuesta.ok) {
        // Re-encolar si fallo (hasta el limite)
        const espacio = MAX_COLA - this.cola.length
        this.cola.push(...batch.slice(0, espacio))
        log.warn(`[telemetria] Flush fallido: ${respuesta.status}`)
        return
      }

      this.ultimoEnvio = new Date().toISOString()
      log.info(`[telemetria] ${batch.length} eventos enviados`)
    } catch (error) {
      // Re-encolar si hubo error de red
      const espacio = MAX_COLA - this.cola.length
      this.cola.push(...batch.slice(0, espacio))
      log.warn('[telemetria] Error de red al enviar eventos')
    }
  }

  /** Activar opt-out (desactivar telemetria) */
  optOut(): void {
    this.config.optOut = true
    this.cola = []
    log.info('[telemetria] Opt-out activado')
  }

  /** Desactivar opt-out (reactivar telemetria) */
  optIn(): void {
    this.config.optOut = false
    log.info('[telemetria] Opt-in activado')
  }

  /** Consultar si esta activa */
  estaActiva(): boolean {
    return !this.config.optOut
  }

  /** Obtener estado actual */
  obtenerEstado(): EstadoTelemetria {
    return {
      activa: !this.config.optOut,
      eventosEnCola: this.cola.length,
      ultimoEnvio: this.ultimoEnvio,
    }
  }
}

/** Singleton exportado */
export const clienteTelemetria = new ClienteTelemetria()
