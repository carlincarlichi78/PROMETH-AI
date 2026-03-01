import { existsSync, readdirSync, mkdirSync, copyFileSync } from 'fs'
import { join, basename, extname } from 'path'
import log from 'electron-log'
import { AccionBase } from './accion-base'
import type {
  ConfigSendToRepository,
  ContextoEjecucionDesktop,
  ResultadoAccionDesktop,
} from '../tipos-workflows-desktop'

/**
 * Accion: organizar archivos en estructura de carpetas del repositorio.
 *
 * Copia archivos desde carpetaOrigen a repositorioRaiz/estructuraCarpetas.
 * La estructura soporta templates: {nif}, {fecha}, {modelo}, {tipo}, {anio}.
 *
 * Ejemplo: repositorioRaiz = "C:/Clientes"
 *          estructuraCarpetas = "{nif}/{anio}/{modelo}"
 *          → "C:/Clientes/12345678A/2025/130/"
 */
export class AccionSendToRepository extends AccionBase {
  constructor(config: ConfigSendToRepository) {
    super('send_to_repository', config)
  }

  private get cfg(): ConfigSendToRepository {
    return this.config as ConfigSendToRepository
  }

  async preRun(_contexto: ContextoEjecucionDesktop): Promise<void> {
    if (!existsSync(this.cfg.carpetaOrigen)) {
      throw new Error(`Carpeta origen no existe: ${this.cfg.carpetaOrigen}`)
    }

    if (!existsSync(this.cfg.repositorioRaiz)) {
      mkdirSync(this.cfg.repositorioRaiz, { recursive: true })
    }

    const archivos = readdirSync(this.cfg.carpetaOrigen).filter(
      (f) => !f.startsWith('.')
    )
    if (archivos.length === 0) {
      throw new Error(`No hay archivos en: ${this.cfg.carpetaOrigen}`)
    }
  }

  async run(contexto: ContextoEjecucionDesktop): Promise<ResultadoAccionDesktop> {
    const archivosCopiados: string[] = []
    const archivos = readdirSync(this.cfg.carpetaOrigen).filter(
      (f) => !f.startsWith('.') && extname(f) !== ''
    )

    // Resolver estructura de carpetas con templates
    const estructura = this.reemplazarTemplates(
      this.cfg.estructuraCarpetas,
      contexto
    )
    const carpetaDestino = join(this.cfg.repositorioRaiz, estructura)

    if (!existsSync(carpetaDestino)) {
      mkdirSync(carpetaDestino, { recursive: true })
    }

    for (const archivo of archivos) {
      const rutaOrigen = join(this.cfg.carpetaOrigen, archivo)
      const rutaDestino = join(carpetaDestino, archivo)

      // Verificar si ya existe
      if (existsSync(rutaDestino) && !this.cfg.sobreescribir) {
        // Generar nombre alternativo: archivo_1.pdf, archivo_2.pdf, etc.
        const rutaAlternativa = this.generarNombreAlternativo(carpetaDestino, archivo)
        copyFileSync(rutaOrigen, rutaAlternativa)
        archivosCopiados.push(rutaAlternativa)
        log.info(`[SendToRepo] Copiado (renombrado): ${archivo} → ${basename(rutaAlternativa)}`)
      } else {
        copyFileSync(rutaOrigen, rutaDestino)
        archivosCopiados.push(rutaDestino)
        log.info(`[SendToRepo] Copiado: ${archivo} → ${estructura}/`)
      }
    }

    return {
      tipo: 'send_to_repository',
      exito: true,
      mensaje: `${archivosCopiados.length} archivos organizados en ${estructura}`,
      archivosResultado: archivosCopiados,
      datosExtra: { carpetaDestino },
      tiempoMs: 0,
    }
  }

  async postRun(_resultado: ResultadoAccionDesktop): Promise<void> {
    // Sin limpieza necesaria
  }

  /**
   * Genera un nombre de archivo alternativo si ya existe.
   * archivo.pdf → archivo_1.pdf → archivo_2.pdf
   */
  private generarNombreAlternativo(carpeta: string, nombre: string): string {
    const ext = extname(nombre)
    const base = basename(nombre, ext)
    let contador = 1
    let rutaCandidata = join(carpeta, `${base}_${contador}${ext}`)

    while (existsSync(rutaCandidata)) {
      contador++
      rutaCandidata = join(carpeta, `${base}_${contador}${ext}`)
    }

    return rutaCandidata
  }
}
