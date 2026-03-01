import log from 'electron-log'
import { ChainStatus, BlockStatus, type EstadoCadena } from './tipos'
import type { Block } from './block'

let contadorCadenas = 0

/**
 * Cadena de bloques asociada a un certificado.
 * Ejecuta bloques secuencialmente. Si un bloque falla,
 * la cadena se marca como PARTIALLY_COMPLETED y continua.
 */
export class Chain {
  readonly id: string
  readonly certificadoSerial: string
  readonly nombreCert?: string
  readonly bloques: Block[] = []

  estado: ChainStatus = ChainStatus.IDLE

  constructor(certificadoSerial: string, nombreCert?: string) {
    contadorCadenas++
    this.id = `chain-${contadorCadenas}`
    this.certificadoSerial = certificadoSerial
    this.nombreCert = nombreCert
  }

  /**
   * Agrega un bloque a la cadena.
   */
  agregarBloque(bloque: Block): void {
    this.bloques.push(bloque)
  }

  /**
   * Ejecuta todos los bloques secuencialmente.
   */
  async ejecutar(): Promise<void> {
    this.estado = ChainStatus.RUNNING
    log.info(
      `[${this.id}] Iniciando cadena — cert: ${this.certificadoSerial}, bloques: ${this.bloques.length}`,
    )

    let algunoFallo = false
    let todosCompletados = true

    for (const bloque of this.bloques) {
      const resultado = await bloque.ejecutar()

      if (!resultado.exito) {
        algunoFallo = true
        todosCompletados = false
        log.warn(
          `[${this.id}] Bloque ${bloque.id} fallo, continuando con siguiente`,
        )
      }
    }

    if (todosCompletados) {
      this.estado = ChainStatus.COMPLETED
    } else if (algunoFallo && this.bloquesCompletados > 0) {
      this.estado = ChainStatus.PARTIALLY_COMPLETED
    } else {
      this.estado = ChainStatus.FAILED
    }

    log.info(`[${this.id}] Cadena finalizada: ${this.estado}`)
  }

  /** Cantidad de bloques completados exitosamente */
  get bloquesCompletados(): number {
    return this.bloques.filter((b) => b.estado === BlockStatus.COMPLETED).length
  }

  /**
   * Retorna estado serializable para IPC.
   */
  obtenerEstado(): EstadoCadena {
    return {
      id: this.id,
      estado: this.estado,
      certificadoSerial: this.certificadoSerial,
      nombreCert: this.nombreCert,
      totalBloques: this.bloques.length,
      bloquesCompletados: this.bloquesCompletados,
      bloques: this.bloques.map((b) => b.obtenerInfo()),
    }
  }
}
