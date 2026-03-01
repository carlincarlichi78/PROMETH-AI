import log from 'electron-log'
import { BlockStatus, type ProcessType, type ResultadoScraping, type InfoBloque } from './tipos'
import type { BaseScraper } from './base-scraper'

let contadorBloques = 0

/**
 * Unidad atomica de trabajo en la cola de procesamiento.
 * Cada bloque ejecuta un scraper y registra su resultado.
 */
export class Block {
  readonly id: string
  readonly tipo: ProcessType
  readonly descripcion: string
  readonly scraper: BaseScraper

  estado: BlockStatus = BlockStatus.PENDING
  resultado: ResultadoScraping | null = null

  constructor(tipo: ProcessType, descripcion: string, scraper: BaseScraper) {
    contadorBloques++
    this.id = `block-${contadorBloques}`
    this.tipo = tipo
    this.descripcion = descripcion
    this.scraper = scraper
  }

  /**
   * Ejecuta el scraper del bloque.
   */
  async ejecutar(): Promise<ResultadoScraping> {
    this.estado = BlockStatus.RUNNING
    log.info(`[${this.id}] Ejecutando: ${this.descripcion}`)

    try {
      this.resultado = await this.scraper.run()

      this.estado = this.resultado.exito
        ? BlockStatus.COMPLETED
        : BlockStatus.FAILED

      log.info(
        `[${this.id}] ${this.estado}: ${this.resultado.exito ? 'OK' : this.resultado.error}`,
      )

      return this.resultado
    } catch (error) {
      const mensaje = error instanceof Error ? error.message : 'Error desconocido'
      this.estado = BlockStatus.FAILED
      this.resultado = { exito: false, error: mensaje }
      log.error(`[${this.id}] Error:`, mensaje)
      return this.resultado
    }
  }

  /**
   * Retorna info serializable del bloque para IPC.
   */
  obtenerInfo(): InfoBloque {
    return {
      id: this.id,
      tipo: this.tipo,
      estado: this.estado,
      descripcion: this.descripcion,
    }
  }
}
