import log from 'electron-log'
import tesseractJs from 'tesseract.js'
const { createWorker } = tesseractJs
import type { Worker } from 'tesseract.js'

/** Worker singleton reutilizable */
let worker: Worker | null = null
let inicializando: Promise<Worker> | null = null

/**
 * Obtiene (o crea) el worker OCR singleton.
 * Usa idioma espanol por defecto (notificaciones de administracion).
 */
async function obtenerWorker(): Promise<Worker> {
  if (worker) return worker

  // Evitar race condition si se llama multiples veces
  if (inicializando) return inicializando

  inicializando = (async () => {
    log.info('[OCR] Inicializando worker tesseract.js (spa)')
    const w = await createWorker('spa')
    worker = w
    inicializando = null
    log.info('[OCR] Worker listo')
    return w
  })()

  return inicializando
}

/**
 * Ejecuta OCR sobre un buffer de imagen.
 * Retorna el texto extraido.
 */
export async function ocrDesdeImagen(buffer: Buffer): Promise<string> {
  const w = await obtenerWorker()
  const { data } = await w.recognize(buffer)
  return data.text.trim()
}

/**
 * Indica si el worker esta activo.
 */
export function workerActivo(): boolean {
  return worker !== null
}

/**
 * Termina el worker OCR (llamar al cerrar la app).
 */
export async function terminarWorkerOcr(): Promise<void> {
  if (worker) {
    try {
      await worker.terminate()
      log.info('[OCR] Worker terminado')
    } catch (err) {
      log.warn(`[OCR] Error terminando worker: ${(err as Error).message}`)
    }
    worker = null
  }
}
