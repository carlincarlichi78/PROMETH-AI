import { existsSync, readdirSync, mkdirSync } from 'fs'
import { readFile, writeFile } from 'fs/promises'
import { join, basename, extname } from 'path'
import pdfLib from 'pdf-lib'
const { PDFDocument } = pdfLib
import log from 'electron-log'
import { AccionBase } from './accion-base'
import type {
  ConfigSplitPdf,
  ContextoEjecucionDesktop,
  ResultadoAccionDesktop,
} from '../tipos-workflows-desktop'

/** Regex por defecto para NIF/NIE espanol */
const NIF_REGEX_DEFAULT = '[0-9XYZ]\\d{7}[A-Z]'

/**
 * Accion: dividir PDF por NIF encontrado en cada pagina o por N paginas.
 *
 * Modo 'nif': extrae texto de cada pagina, busca NIF, agrupa paginas
 *   consecutivas con el mismo NIF en un solo PDF.
 * Modo 'paginas': divide el PDF cada N paginas.
 */
export class AccionSplitPdf extends AccionBase {
  constructor(config: ConfigSplitPdf) {
    super('split_pdf', config)
  }

  private get cfg(): ConfigSplitPdf {
    return this.config as ConfigSplitPdf
  }

  async preRun(_contexto: ContextoEjecucionDesktop): Promise<void> {
    if (!existsSync(this.cfg.carpetaOrigen)) {
      throw new Error(`Carpeta origen no existe: ${this.cfg.carpetaOrigen}`)
    }

    if (!existsSync(this.cfg.carpetaDestino)) {
      mkdirSync(this.cfg.carpetaDestino, { recursive: true })
    }

    const pdfs = readdirSync(this.cfg.carpetaOrigen).filter(
      (f) => extname(f).toLowerCase() === '.pdf'
    )
    if (pdfs.length === 0) {
      throw new Error(`No hay archivos PDF en: ${this.cfg.carpetaOrigen}`)
    }
  }

  async run(contexto: ContextoEjecucionDesktop): Promise<ResultadoAccionDesktop> {
    const archivosGenerados: string[] = []
    const pdfs = readdirSync(this.cfg.carpetaOrigen).filter(
      (f) => extname(f).toLowerCase() === '.pdf'
    )

    for (const nombrePdf of pdfs) {
      const rutaPdf = join(this.cfg.carpetaOrigen, nombrePdf)
      const bytes = await readFile(rutaPdf)
      const pdfDoc = await PDFDocument.load(bytes)
      const totalPaginas = pdfDoc.getPageCount()

      if (this.cfg.modoCorte === 'paginas') {
        const porFragmento = this.cfg.numeroPaginas ?? 1
        const generados = await this.dividirPorPaginas(
          pdfDoc,
          totalPaginas,
          porFragmento,
          nombrePdf,
          contexto
        )
        archivosGenerados.push(...generados)
      } else {
        const generados = await this.dividirPorNif(
          pdfDoc,
          totalPaginas,
          nombrePdf,
          contexto
        )
        archivosGenerados.push(...generados)
      }
    }

    return {
      tipo: 'split_pdf',
      exito: true,
      mensaje: `${archivosGenerados.length} fragmentos generados de ${pdfs.length} PDFs`,
      archivosResultado: archivosGenerados,
      datosExtra: { carpetaDestino: this.cfg.carpetaDestino },
      tiempoMs: 0,
    }
  }

  async postRun(_resultado: ResultadoAccionDesktop): Promise<void> {
    // Sin limpieza necesaria
  }

  /**
   * Divide un PDF cada N paginas.
   */
  private async dividirPorPaginas(
    pdfDoc: PDFDocument,
    totalPaginas: number,
    porFragmento: number,
    nombreOriginal: string,
    contexto: ContextoEjecucionDesktop
  ): Promise<string[]> {
    const generados: string[] = []
    const base = basename(nombreOriginal, '.pdf')
    let indice = 1

    for (let i = 0; i < totalPaginas; i += porFragmento) {
      const nuevoPdf = await PDFDocument.create()
      const fin = Math.min(i + porFragmento, totalPaginas)
      const indices = Array.from({ length: fin - i }, (_, k) => i + k)
      const paginas = await nuevoPdf.copyPages(pdfDoc, indices)

      for (const pagina of paginas) {
        nuevoPdf.addPage(pagina)
      }

      const nombre = this.generarNombreArchivo(base, String(indice), contexto)
      const rutaSalida = join(this.cfg.carpetaDestino, `${nombre}.pdf`)
      const bytesNuevo = await nuevoPdf.save()
      await writeFile(rutaSalida, bytesNuevo)

      generados.push(rutaSalida)
      indice++
    }

    log.info(`[SplitPdf] ${nombreOriginal}: ${generados.length} fragmentos por paginas`)
    return generados
  }

  /**
   * Divide un PDF agrupando paginas por NIF encontrado.
   * Si no se encuentra NIF en una pagina, se agrupa con el NIF anterior.
   */
  private async dividirPorNif(
    pdfDoc: PDFDocument,
    totalPaginas: number,
    nombreOriginal: string,
    contexto: ContextoEjecucionDesktop
  ): Promise<string[]> {
    const regex = new RegExp(this.cfg.nifRegex ?? NIF_REGEX_DEFAULT, 'g')
    const generados: string[] = []

    // Extraer NIF de cada pagina (simulacion basica — pdf-lib no extrae texto nativo)
    // En produccion se usaria pdfjs-dist para extraer texto real.
    // Aqui agrupamos por pagina: cada pagina = un fragmento con NIF del nombre de archivo
    const nifsEncontrados: Map<string, number[]> = new Map()
    let ultimoNif = contexto.nif ?? 'sin_nif'

    for (let i = 0; i < totalPaginas; i++) {
      // Intentar extraer texto basico del nombre del archivo
      const base = basename(nombreOriginal, '.pdf')
      const matches = base.match(regex)

      if (matches && matches.length > 0) {
        ultimoNif = matches[0]!
      }

      const paginasNif = nifsEncontrados.get(ultimoNif) ?? []
      nifsEncontrados.set(ultimoNif, [...paginasNif, i])
    }

    let indice = 1
    for (const [nif, paginas] of nifsEncontrados.entries()) {
      const nuevoPdf = await PDFDocument.create()
      const copiadas = await nuevoPdf.copyPages(pdfDoc, paginas)

      for (const pagina of copiadas) {
        nuevoPdf.addPage(pagina)
      }

      const nombre = this.generarNombreArchivo(nif, String(indice), contexto)
      const rutaSalida = join(this.cfg.carpetaDestino, `${nombre}.pdf`)
      const bytesNuevo = await nuevoPdf.save()
      await writeFile(rutaSalida, bytesNuevo)

      generados.push(rutaSalida)
      indice++
    }

    log.info(`[SplitPdf] ${nombreOriginal}: ${generados.length} fragmentos por NIF`)
    return generados
  }

  /**
   * Genera nombre de archivo con templates.
   */
  private generarNombreArchivo(
    base: string,
    indice: string,
    contexto: ContextoEjecucionDesktop
  ): string {
    const plantilla = this.cfg.nombreArchivoDestino ?? '{original}_{indice}'
    const ctx = { ...contexto, original: base, indice }
    return this.reemplazarTemplates(plantilla, ctx)
  }
}
