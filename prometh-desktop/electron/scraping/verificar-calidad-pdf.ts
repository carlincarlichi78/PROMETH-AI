import fs from 'node:fs'

export interface ResultadoVerificacion {
  esDocumentoReal: boolean
  confianza: number
  motivo: string
}

/**
 * Verifica si un PDF es un documento real o una captura de pantalla.
 * Heuristicas:
 * - Producer "Chromium" o "Chrome" = captura printToPDF
 * - Tamano > 400KB para 1 pagina DEHU = sospechoso (reales ~175KB, capturas ~490KB)
 */
export function verificarCalidadPdf(rutaPdf: string): ResultadoVerificacion {
  try {
    const stats = fs.statSync(rutaPdf)
    // Leer los primeros 4KB para buscar metadatos PDF
    const fd = fs.openSync(rutaPdf, 'r')
    const buffer = Buffer.alloc(4096)
    fs.readSync(fd, buffer, 0, 4096, 0)
    fs.closeSync(fd)
    const header = buffer.toString('latin1')

    // Heuristica 1: Producer contiene "Chromium" o "HeadlessChrome" = captura
    if (header.includes('/Producer') && (header.includes('Chromium') || header.includes('HeadlessChrome'))) {
      return { esDocumentoReal: false, confianza: 95, motivo: 'Producer Chromium/HeadlessChrome' }
    }

    // Heuristica 2: Creator contiene "Chromium"
    if (header.includes('/Creator') && header.includes('Chromium')) {
      return { esDocumentoReal: false, confianza: 90, motivo: 'Creator Chromium' }
    }

    // Heuristica 3: Tamano > 400KB sospechoso para documentos DEHU de 1 pagina
    // Los documentos reales de DEHU son ~175KB, las capturas ~490KB
    if (stats.size > 400000) {
      return { esDocumentoReal: false, confianza: 70, motivo: 'Tamano sospechoso (>400KB)' }
    }

    return { esDocumentoReal: true, confianza: 90, motivo: 'Documento nativo' }
  } catch {
    // Si no se puede leer, asumir que es real
    return { esDocumentoReal: true, confianza: 50, motivo: 'No se pudo verificar' }
  }
}
