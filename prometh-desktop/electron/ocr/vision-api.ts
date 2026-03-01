import log from 'electron-log'

/**
 * Llama al endpoint POST /api/ocr/vision para extraer texto
 * de imagenes usando GPT-4o-mini vision.
 *
 * Fallback para cuando tesseract.js no produce texto util.
 */
export async function ocrConVisionApi(
  imagenes: Buffer[],
  apiUrl: string,
  token: string,
): Promise<string | null> {
  if (imagenes.length === 0) return null

  const imagenesBase64 = imagenes.map((buf) => buf.toString('base64'))

  try {
    log.info(`[OCR-Vision] Enviando ${imagenes.length} imagenes a API vision`)
    const inicio = Date.now()

    const response = await fetch(`${apiUrl}/ocr/vision`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ imagenes: imagenesBase64 }),
    })

    if (!response.ok) {
      const texto = await response.text()
      log.warn(`[OCR-Vision] API retorno ${response.status}: ${texto}`)
      return null
    }

    const resultado = (await response.json()) as {
      exito: boolean
      datos?: { texto: string; tokens: number }
    }

    const texto = resultado.datos?.texto?.trim() ?? ''
    const tokens = resultado.datos?.tokens ?? 0

    log.info(
      `[OCR-Vision] Texto extraido: ${texto.length} chars, ${tokens} tokens en ${Date.now() - inicio}ms`,
    )

    return texto.length > 0 ? texto : null
  } catch (err) {
    log.warn(`[OCR-Vision] Error: ${(err as Error).message}`)
    return null
  }
}
