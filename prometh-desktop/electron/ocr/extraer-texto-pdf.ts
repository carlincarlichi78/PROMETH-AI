import { readFileSync } from 'fs'
import { existsSync } from 'fs'
import log from 'electron-log'
import { PDFParse } from 'pdf-parse'
import { ocrDesdeImagen } from './ocr-imagen'
import { pdfAImagenes } from './pdf-a-imagen'
import { ocrConVisionApi } from './vision-api'

/** Umbral minimo de caracteres para considerar que se extrajo texto util */
const UMBRAL_TEXTO_NATIVO = 50

/** Maximo de caracteres a retornar (GPT-4o-mini soporta 128k tokens input) */
const MAX_CARACTERES = 25000

/** Opciones para habilitar fallback con GPT-4o-mini vision */
export interface OpcionesVision {
  apiUrl: string
  token: string
}

/**
 * Extrae texto de un PDF usando tres capas:
 * 1. pdf-parse para texto nativo (rapido, ~100ms)
 * 2. tesseract.js OCR como fallback para PDFs escaneados (~5-15s)
 * 3. GPT-4o-mini vision como ultimo recurso si tesseract falla (~2-5s, requiere red)
 *
 * Layer 3 solo se activa si se pasan opcionesVision (apiUrl + token).
 * Retorna null si no se puede extraer texto.
 */
export async function extraerTextoPdf(
  rutaPdf: string,
  opcionesVision?: OpcionesVision,
): Promise<string | null> {
  if (!existsSync(rutaPdf)) {
    log.warn(`[OCR] Archivo no existe: ${rutaPdf}`)
    return null
  }

  const inicio = Date.now()

  try {
    // Capa 1: texto nativo con pdf-parse v2
    const buffer = readFileSync(rutaPdf)
    const parser = new PDFParse({ data: new Uint8Array(buffer) })
    await parser.load()
    const resultado = await parser.getText()
    // pdf-parse v2 getText() retorna objeto { text, pages, total }, no string
    const textoNativo = (typeof resultado === 'string' ? resultado : resultado?.text ?? '').trim()

    if (textoNativo.length >= UMBRAL_TEXTO_NATIVO) {
      const texto = textoNativo.slice(0, MAX_CARACTERES)
      log.info(
        `[OCR] Texto nativo extraido: ${texto.length} chars en ${Date.now() - inicio}ms`,
      )
      return texto
    }

    // Capa 2: OCR con tesseract.js
    log.info('[OCR] Texto nativo insuficiente, iniciando OCR...')
    const imagenes = await pdfAImagenes(rutaPdf, 10)

    if (imagenes.length === 0) {
      log.warn('[OCR] No se pudieron generar imagenes del PDF')
      return null
    }

    const textosOcr: string[] = []
    for (const imagen of imagenes) {
      const texto = await ocrDesdeImagen(imagen)
      if (texto.length > 10) {
        textosOcr.push(texto)
      }
    }

    const textoTesseract = textosOcr.join('\n\n').trim()

    if (textoTesseract.length >= UMBRAL_TEXTO_NATIVO) {
      const textoFinal = textoTesseract.slice(0, MAX_CARACTERES)
      log.info(
        `[OCR] Texto tesseract extraido: ${textoFinal.length} chars en ${Date.now() - inicio}ms`,
      )
      return textoFinal
    }

    // Capa 3: GPT-4o-mini vision (si hay conexion y credenciales)
    if (opcionesVision) {
      log.info('[OCR] Tesseract insuficiente, intentando vision API...')
      const textoVision = await ocrConVisionApi(
        imagenes,
        opcionesVision.apiUrl,
        opcionesVision.token,
      )

      if (textoVision && textoVision.length >= UMBRAL_TEXTO_NATIVO) {
        const textoFinal = textoVision.slice(0, MAX_CARACTERES)
        log.info(
          `[OCR] Texto vision extraido: ${textoFinal.length} chars en ${Date.now() - inicio}ms`,
        )
        return textoFinal
      }
    }

    // Si tesseract produjo algo (aunque poco), devolverlo
    if (textoTesseract.length > 0) {
      return textoTesseract.slice(0, MAX_CARACTERES)
    }

    log.warn('[OCR] Ninguna capa produjo texto util')
    return null
  } catch (err) {
    log.error(`[OCR] Error extrayendo texto: ${(err as Error).message}`)
    return null
  }
}
