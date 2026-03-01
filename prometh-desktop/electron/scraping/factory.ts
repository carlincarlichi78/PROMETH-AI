import pLimit from 'p-limit'
import log from 'electron-log'
import { FactoryStatus, type EstadoCola, type ConfigScraping, CONFIG_DEFAULT } from './tipos'
import type { Chain } from './chain'

type CallbackProgreso = (estado: EstadoCola) => void

/**
 * Gestor global de la cola de procesamiento.
 * Orquesta la ejecucion de cadenas de forma secuencial o concurrente.
 */
export class Factory {
  estado: FactoryStatus = FactoryStatus.IDLE
  private cadenas: Chain[] = []
  private cadenaActualIndex = 0
  private cancelado = false
  private config: ConfigScraping = { ...CONFIG_DEFAULT }
  private callbackProgreso: CallbackProgreso | null = null

  /**
   * Configura callback para notificar progreso via IPC.
   */
  onProgreso(callback: CallbackProgreso): void {
    this.callbackProgreso = callback
  }

  /**
   * Actualiza la configuracion de scraping.
   */
  configurar(config: Partial<ConfigScraping>): void {
    this.config = { ...this.config, ...config }
  }

  /**
   * Obtiene la configuracion actual.
   */
  obtenerConfig(): ConfigScraping {
    return { ...this.config }
  }

  /**
   * Agrega una cadena a la cola.
   */
  agregarCadena(cadena: Chain): void {
    this.cadenas.push(cadena)
  }

  /**
   * Limpia todas las cadenas de la cola.
   */
  limpiar(): void {
    this.cadenas = []
    this.cadenaActualIndex = 0
  }

  /**
   * Inicia la ejecucion de todas las cadenas.
   * En modo normal: secuencial.
   * En fast mode: concurrente con p-limit.
   */
  async iniciar(): Promise<void> {
    if (this.estado === FactoryStatus.RUNNING) {
      log.warn('Factory ya en ejecucion')
      return
    }

    this.estado = FactoryStatus.RUNNING
    this.cancelado = false
    this.cadenaActualIndex = 0

    log.info(
      `Factory iniciada — cadenas: ${this.cadenas.length}, fastMode: ${this.config.fastMode}`,
    )
    this.notificarProgreso()

    try {
      if (this.config.fastMode) {
        await this.ejecutarConcurrente()
      } else {
        await this.ejecutarSecuencial()
      }
    } finally {
      this.estado = FactoryStatus.IDLE
      log.info('Factory finalizada')
      this.notificarProgreso()
    }
  }

  /**
   * Cancela la ejecucion en curso.
   */
  detener(): void {
    this.cancelado = true
    log.info('Factory: detencion solicitada')
  }

  /**
   * Ejecucion secuencial: una cadena a la vez.
   */
  private async ejecutarSecuencial(): Promise<void> {
    for (let i = 0; i < this.cadenas.length; i++) {
      if (this.cancelado) break

      this.cadenaActualIndex = i
      this.notificarProgreso()

      await this.cadenas[i].ejecutar()
      this.notificarProgreso()
    }
  }

  /**
   * Ejecucion concurrente: N cadenas en paralelo con p-limit.
   */
  private async ejecutarConcurrente(): Promise<void> {
    const limite = pLimit(this.config.replicas)

    const tareas = this.cadenas.map((cadena, index) =>
      limite(async () => {
        if (this.cancelado) return
        this.cadenaActualIndex = index
        this.notificarProgreso()

        await cadena.ejecutar()
        this.notificarProgreso()
      }),
    )

    await Promise.all(tareas)
  }

  /**
   * Notifica el estado actual al renderer via callback.
   */
  private notificarProgreso(): void {
    if (this.callbackProgreso) {
      this.callbackProgreso(this.obtenerEstado())
    }
  }

  /**
   * Retorna snapshot del estado actual de la cola.
   */
  obtenerEstado(): EstadoCola {
    const cadenaActual = this.cadenas[this.cadenaActualIndex]
    const totalBloques = this.cadenas.reduce(
      (sum, c) => sum + c.bloques.length,
      0,
    )
    const bloquesCompletados = this.cadenas.reduce(
      (sum, c) => sum + c.bloquesCompletados,
      0,
    )
    const progreso = totalBloques > 0
      ? Math.round((bloquesCompletados / totalBloques) * 100)
      : 0

    return {
      status: this.estado,
      totalCadenas: this.cadenas.length,
      cadenaActual: this.cadenaActualIndex,
      bloqueActual: cadenaActual?.bloquesCompletados ?? 0,
      totalBloques,
      progreso,
      cadenas: this.cadenas.map((c) => c.obtenerEstado()),
    }
  }
}
