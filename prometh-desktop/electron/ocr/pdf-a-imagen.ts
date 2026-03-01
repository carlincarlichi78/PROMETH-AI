import { readFileSync } from 'fs'
import { BrowserWindow } from 'electron'
import log from 'electron-log'

/**
 * Convierte las primeras paginas de un PDF a imagenes PNG usando
 * un BrowserWindow oculto + printToPDF renderizado.
 *
 * Alternativa ligera: renderiza el PDF en un iframe oculto y
 * captura cada pagina como imagen via NativeImage.
 *
 * Para simplificar, usamos un approach mas directo:
 * renderizamos el PDF en un BrowserWindow headless y capturamos
 * la pagina como imagen.
 */
export async function pdfAImagenes(
  rutaPdf: string,
  maxPaginas = 3,
): Promise<Buffer[]> {
  const pdfBuffer = readFileSync(rutaPdf)
  const base64 = pdfBuffer.toString('base64')
  const imagenes: Buffer[] = []

  // Crear ventana oculta para renderizar el PDF
  const ventana = new BrowserWindow({
    show: false,
    width: 1240,
    height: 1754, // A4 aprox a 150 DPI
    webPreferences: {
      offscreen: true,
      contextIsolation: true,
      sandbox: true,
    },
  })

  try {
    // Cargar PDF como data URL (pdf.js integrado en Chromium)
    await ventana.loadURL(
      `data:application/pdf;base64,${base64}`,
    )

    // Esperar a que el PDF se renderice
    await new Promise((resolve) => setTimeout(resolve, 2000))

    // Capturar paginas (Chromium renderiza el PDF en scroll continuo)
    const paginas = maxPaginas
    for (let i = 0; i < paginas; i++) {
      const imagen = await ventana.webContents.capturePage()
      const pngBuffer = imagen.toPNG()

      // Si la imagen tiene contenido (no esta vacia)
      if (pngBuffer.length > 1000) {
        imagenes.push(pngBuffer)
      }

      // Scroll a la siguiente pagina
      if (i < paginas - 1) {
        await ventana.webContents.executeJavaScript(
          `window.scrollBy(0, ${1754})`,
        )
        await new Promise((resolve) => setTimeout(resolve, 500))
      }
    }

    log.info(`[OCR] PDF renderizado: ${imagenes.length} paginas capturadas`)
  } catch (err) {
    log.warn(`[OCR] Error renderizando PDF: ${(err as Error).message}`)
  } finally {
    ventana.destroy()
  }

  return imagenes
}
