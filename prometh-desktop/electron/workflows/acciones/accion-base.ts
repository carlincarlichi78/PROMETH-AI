import log from 'electron-log'
import type {
  TipoAccionDesktop,
  ConfigAccionDesktop,
  ContextoEjecucionDesktop,
  ResultadoAccionDesktop,
} from '../tipos-workflows-desktop'

/**
 * Clase base abstracta para acciones de workflow desktop.
 * Patron lifecycle: preRun → run → postRun (envuelto en execute).
 */
export abstract class AccionBase {
  readonly tipo: TipoAccionDesktop
  protected readonly config: ConfigAccionDesktop

  constructor(tipo: TipoAccionDesktop, config: ConfigAccionDesktop) {
    this.tipo = tipo
    this.config = config
  }

  /**
   * Validacion previa a la ejecucion.
   * Verificar que carpetas existen, config es valida, etc.
   * Lanza error si algo no es correcto.
   */
  abstract preRun(contexto: ContextoEjecucionDesktop): Promise<void>

  /**
   * Logica principal de la accion.
   * Retorna resultado parcial (archivos generados, datos extra).
   */
  abstract run(contexto: ContextoEjecucionDesktop): Promise<ResultadoAccionDesktop>

  /**
   * Limpieza post-ejecucion (borrar temporales, etc.).
   * No lanza errores — solo loguea warnings.
   */
  abstract postRun(resultado: ResultadoAccionDesktop): Promise<void>

  /**
   * Ejecuta el ciclo completo: preRun → run → postRun.
   * Mide tiempo y captura errores en cada fase.
   */
  async execute(contexto: ContextoEjecucionDesktop): Promise<ResultadoAccionDesktop> {
    const inicio = Date.now()

    try {
      log.info(`[Accion:${this.tipo}] Iniciando preRun`)
      await this.preRun(contexto)

      log.info(`[Accion:${this.tipo}] Ejecutando run`)
      const resultado = await this.run(contexto)

      log.info(`[Accion:${this.tipo}] Ejecutando postRun`)
      await this.postRun(resultado).catch((err) =>
        log.warn(`[Accion:${this.tipo}] Error en postRun:`, err)
      )

      return { ...resultado, tiempoMs: Date.now() - inicio }
    } catch (error) {
      const mensaje = error instanceof Error ? error.message : 'Error desconocido'
      log.error(`[Accion:${this.tipo}] Error:`, error)
      return {
        tipo: this.tipo,
        exito: false,
        mensaje,
        tiempoMs: Date.now() - inicio,
      }
    }
  }

  /**
   * Reemplaza templates {variable} en strings de configuracion.
   * Soporta: {nif}, {fecha}, {original}, {indice}, {modelo}, {anio}
   */
  protected reemplazarTemplates(
    texto: string,
    contexto: ContextoEjecucionDesktop
  ): string {
    return texto.replace(/\{(\w+)\}/g, (_match, variable: string) => {
      if (variable === 'fecha') {
        return new Date().toISOString().split('T')[0]!
      }
      if (variable in contexto) {
        return String(contexto[variable])
      }
      return `{${variable}}`
    })
  }
}
