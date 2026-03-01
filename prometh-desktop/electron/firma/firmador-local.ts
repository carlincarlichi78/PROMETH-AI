import { readFileSync, writeFileSync } from 'fs'
import { parse, join, basename } from 'path'
import pdfLib from 'pdf-lib'
const { PDFDocument } = pdfLib
import signpdfPlaceholder from '@signpdf/placeholder-pdf-lib'
const { pdflibAddPlaceholder } = signpdfPlaceholder
import signpdfCore from '@signpdf/signpdf'
const { SignPdf } = signpdfCore
import signerP12 from '@signpdf/signer-p12'
const { P12Signer } = signerP12
import signpdfUtils from '@signpdf/utils'
const { SUBFILTER_ETSI_CADES_DETACHED } = signpdfUtils
import forge from 'node-forge'
import log from 'electron-log'
import type { OpcionesFirmaLocal, ResultadoFirma } from './tipos-firma'
import { dibujarStamp } from './stamp-firma'

const RAZON_DEFAULT = 'Firmado digitalmente con CertiGestor'
const UBICACION_DEFAULT = 'ES'
const LONGITUD_FIRMA = 16_384

/**
 * Genera la ruta de salida para un PDF firmado.
 * Si no se proporciona rutaSalida, añade "-firmado" antes de la extension.
 *
 * Ejemplo: /docs/contrato.pdf → /docs/contrato-firmado.pdf
 */
export function generarRutaSalida(rutaOriginal: string, rutaSalida?: string): string {
  if (rutaSalida) return rutaSalida

  const { dir, name, ext } = parse(rutaOriginal)
  return join(dir, `${name}-firmado${ext || '.pdf'}`)
}

/**
 * Valida que un certificado P12/PFX es legible y no esta caducado.
 * Lanza error descriptivo si hay problemas.
 */
export function validarCertificadoParaFirma(
  ruta: string,
  password: string,
): { valido: boolean; error?: string; serial?: string } {
  try {
    const buffer = readFileSync(ruta)
    const derString = buffer.toString('binary')
    const asn1 = forge.asn1.fromDer(derString)
    const p12 = forge.pkcs12.pkcs12FromAsn1(asn1, password)

    const certBags = p12.getBags({ bagType: forge.pki.oids.certBag })
    const listaBags = certBags[forge.pki.oids.certBag]

    if (!listaBags || listaBags.length === 0) {
      return { valido: false, error: 'No se encontro certificado en el P12/PFX' }
    }

    const cert = listaBags[0]?.cert
    if (!cert) {
      return { valido: false, error: 'No se pudo leer el certificado del P12/PFX' }
    }

    // Verificar caducidad
    const ahora = new Date()
    if (cert.validity.notAfter < ahora) {
      return {
        valido: false,
        error: `Certificado caducado el ${cert.validity.notAfter.toISOString()}`,
      }
    }

    // Verificar que tiene clave privada
    const keyBags = p12.getBags({ bagType: forge.pki.oids.pkcs8ShroudedKeyBag })
    const listaKeys = keyBags[forge.pki.oids.pkcs8ShroudedKeyBag]

    if (!listaKeys || listaKeys.length === 0) {
      return { valido: false, error: 'No se encontro clave privada en el P12/PFX' }
    }

    return {
      valido: true,
      serial: cert.serialNumber ?? undefined,
    }
  } catch (error) {
    const mensaje =
      error instanceof Error ? error.message : 'Error desconocido al leer el certificado'
    return { valido: false, error: mensaje }
  }
}

/**
 * Firma un PDF con PAdES (ETSI.CAdES.detached) usando un certificado P12 local.
 * Replica el patron de apps/api/src/modulos/firmas/firmas.firmador.ts
 * pero ejecutado en el main process de Electron.
 *
 * La clave privada nunca sale del equipo del usuario.
 */
export async function firmarPdfLocal(opciones: OpcionesFirmaLocal): Promise<ResultadoFirma> {
  const inicio = Date.now()
  const {
    rutaPdf,
    rutaCertificado,
    passwordCertificado,
    razon = RAZON_DEFAULT,
    ubicacion = UBICACION_DEFAULT,
    rutaSalida: rutaSalidaOpcional,
  } = opciones

  const rutaSalida = generarRutaSalida(rutaPdf, rutaSalidaOpcional)

  try {
    // 1. Leer archivos
    const p12Buffer = readFileSync(rutaCertificado)
    const pdfBuffer = readFileSync(rutaPdf)

    log.info(`[Firma] Firmando ${basename(rutaPdf)} con certificado local`)

    // 2. Cargar y validar PDF
    let pdfDoc: PDFDocument
    try {
      pdfDoc = await PDFDocument.load(pdfBuffer)
    } catch {
      return {
        exito: false,
        modo: 'local',
        error: 'El archivo PDF no es valido o esta corrupto',
        tiempoMs: Date.now() - inicio,
      }
    }

    // 3. Stamp visual ANTES del placeholder (post-placeholder invalida firma)
    if (opciones.firmaVisible && opciones.opcionesStamp) {
      await dibujarStamp(pdfDoc, opciones.opcionesStamp)
    }

    // 4. Añadir placeholder de firma PAdES
    pdflibAddPlaceholder({
      pdfDoc,
      reason: razon,
      contactInfo: 'CertiGestor Desktop',
      name: 'CertiGestor',
      location: ubicacion,
      subFilter: SUBFILTER_ETSI_CADES_DETACHED,
      signatureLength: LONGITUD_FIRMA,
    })

    // 4. Serializar PDF con placeholder
    const pdfConPlaceholder = Buffer.from(await pdfDoc.save({ useObjectStreams: false }))

    // 5. Crear firmador P12 y firmar
    const firmador = new P12Signer(p12Buffer, { passphrase: passwordCertificado })
    const signPdf = new SignPdf()

    let pdfFirmado: Buffer
    try {
      pdfFirmado = Buffer.from(await signPdf.sign(pdfConPlaceholder, firmador))
    } catch {
      return {
        exito: false,
        modo: 'local',
        error: 'Error al firmar el PDF. Verifica que el certificado es valido.',
        tiempoMs: Date.now() - inicio,
      }
    }

    // 6. Escribir PDF firmado al filesystem
    writeFileSync(rutaSalida, pdfFirmado)

    const tiempoMs = Date.now() - inicio
    log.info(`[Firma] PDF firmado correctamente en ${tiempoMs}ms → ${basename(rutaSalida)}`)

    return {
      exito: true,
      modo: 'local',
      rutaPdfFirmado: rutaSalida,
      tiempoMs,
    }
  } catch (error) {
    const mensaje = error instanceof Error ? error.message : 'Error desconocido al firmar'
    log.error('[Firma] Error:', mensaje)

    return {
      exito: false,
      modo: 'local',
      error: mensaje,
      tiempoMs: Date.now() - inicio,
    }
  }
}
