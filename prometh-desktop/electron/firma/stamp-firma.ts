import pdfLib from 'pdf-lib'
const { PDFDocument, StandardFonts, rgb } = pdfLib

export interface OpcionesStampFirma {
  nombreFirmante: string
  razon?: string
  logoBase64?: string
  colorHex?: string
  posicion?: 'inferior-derecha' | 'inferior-izquierda' | 'superior-derecha' | 'superior-izquierda'
}

function hexARgb(hex: string): { r: number; g: number; b: number } {
  const limpio = hex.replace('#', '')
  return {
    r: parseInt(limpio.substring(0, 2), 16) / 255,
    g: parseInt(limpio.substring(2, 4), 16) / 255,
    b: parseInt(limpio.substring(4, 6), 16) / 255,
  }
}

function formatearFechaStamp(): string {
  const ahora = new Date()
  const dia = String(ahora.getDate()).padStart(2, '0')
  const mes = String(ahora.getMonth() + 1).padStart(2, '0')
  const anio = ahora.getFullYear()
  const hora = String(ahora.getHours()).padStart(2, '0')
  const min = String(ahora.getMinutes()).padStart(2, '0')
  return `${dia}/${mes}/${anio} ${hora}:${min}`
}

/**
 * Dibuja un stamp visual de firma en la primera pagina del PDF.
 * DEBE llamarse ANTES de pdflibAddPlaceholder().
 * Modifica pdfDoc in-place.
 */
export async function dibujarStamp(
  pdfDoc: PDFDocument,
  opciones: OpcionesStampFirma,
): Promise<void> {
  const pagina = pdfDoc.getPages()[0]
  if (!pagina) return

  const { width: anchoPagina, height: altoPagina } = pagina.getSize()
  const colorBase = opciones.colorHex ? hexARgb(opciones.colorHex) : { r: 0.102, g: 0.212, b: 0.365 }

  const fuenteNormal = await pdfDoc.embedFont(StandardFonts.Helvetica)
  const fuenteNegrita = await pdfDoc.embedFont(StandardFonts.HelveticaBold)

  // Dimensiones del stamp
  const anchoStamp = 220
  const altoStamp = 72
  const margen = 40
  const padding = 8

  // Posicion segun configuracion
  const posicion = opciones.posicion ?? 'inferior-derecha'
  let x: number
  let y: number

  switch (posicion) {
    case 'inferior-izquierda':
      x = margen
      y = margen
      break
    case 'superior-derecha':
      x = anchoPagina - anchoStamp - margen
      y = altoPagina - altoStamp - margen
      break
    case 'superior-izquierda':
      x = margen
      y = altoPagina - altoStamp - margen
      break
    default: // inferior-derecha
      x = anchoPagina - anchoStamp - margen
      y = margen
      break
  }

  // Fondo semitransparente
  pagina.drawRectangle({
    x,
    y,
    width: anchoStamp,
    height: altoStamp,
    color: rgb(colorBase.r, colorBase.g, colorBase.b),
    opacity: 0.08,
    borderColor: rgb(colorBase.r, colorBase.g, colorBase.b),
    borderWidth: 0.75,
    borderOpacity: 0.4,
  })

  // Logo opcional
  let offsetTextoX = x + padding
  if (opciones.logoBase64) {
    try {
      const datosLogo = Buffer.from(opciones.logoBase64, 'base64')
      const imagenLogo = await pdfDoc.embedPng(datosLogo)
      const tamLogo = 32
      pagina.drawImage(imagenLogo, {
        x: x + padding,
        y: y + altoStamp - tamLogo - padding,
        width: tamLogo,
        height: tamLogo,
      })
      offsetTextoX = x + padding + tamLogo + 6
    } catch {
      // Logo invalido, continuar sin el
    }
  }

  const colorTexto = rgb(colorBase.r, colorBase.g, colorBase.b)
  const tamFuente = 7.5
  const tamFuenteTitulo = 8.5
  let cursorY = y + altoStamp - padding - tamFuenteTitulo

  // Titulo
  pagina.drawText('Firmado digitalmente', {
    x: offsetTextoX,
    y: cursorY,
    size: tamFuenteTitulo,
    font: fuenteNegrita,
    color: colorTexto,
  })

  cursorY -= tamFuente + 4

  // Nombre firmante
  pagina.drawText(`por: ${opciones.nombreFirmante}`, {
    x: offsetTextoX,
    y: cursorY,
    size: tamFuente,
    font: fuenteNormal,
    color: colorTexto,
  })

  cursorY -= tamFuente + 3

  // Razon
  const razon = opciones.razon ?? 'Conforme'
  pagina.drawText(`Razón: ${razon}`, {
    x: offsetTextoX,
    y: cursorY,
    size: tamFuente,
    font: fuenteNormal,
    color: colorTexto,
  })

  cursorY -= tamFuente + 3

  // Fecha
  pagina.drawText(`Fecha: ${formatearFechaStamp()}`, {
    x: offsetTextoX,
    y: cursorY,
    size: tamFuente,
    font: fuenteNormal,
    color: colorTexto,
  })
}
