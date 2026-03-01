import log from 'electron-log'
import { listarCertificadosInstalados } from './almacen'

/**
 * Extrae nombre legible del subject de un certificado y lo sanitiza para usar como carpeta.
 * Subject tipico: "CN=CANETE GOMEZ, CARLOS ALBERTO - NIF:44584182Q, OU=..."
 * Resultado: "CANETE_GOMEZ_CARLOS_ALBERTO_44584182Q"
 */
export function extraerNombreCarpeta(subject: string): string | undefined {
  const cn = subject.match(/CN=([^,]+)/i)
  if (!cn) return undefined

  let nombre = cn[1].trim()

  // Extraer NIF/NIE si existe (puede estar en el CN o en SERIALNUMBER)
  const nifMatch = subject.match(/(?:NIF|NIE|SERIALNUMBER)[=:]?\s*([A-Z0-9]+)/i)
  const nif = nifMatch ? nifMatch[1].trim() : ''

  // Limpiar: quitar "- NIF:..." del nombre si esta incluido
  nombre = nombre.replace(/\s*-\s*(?:NIF|NIE):?\s*[A-Z0-9]+/i, '').trim()

  // Sanitizar: normalizar unicode, uppercase, reemplazar caracteres no alfanumericos
  nombre = nombre
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toUpperCase()
    .replace(/[^A-Z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')

  if (nif && !nombre.includes(nif.toUpperCase())) {
    nombre = `${nombre}_${nif}`
  }

  return nombre || undefined
}

/**
 * Resuelve el nombre de carpeta para un certificado por su serial.
 * Busca en los certificados instalados y extrae nombre legible del subject.
 */
export async function resolverNombreCarpeta(serialNumber: string): Promise<string | undefined> {
  try {
    const certs = await listarCertificadosInstalados()
    const cert = certs.find(
      (c) => c.numeroSerie.toLowerCase() === serialNumber.toLowerCase(),
    )
    if (!cert) return undefined
    return extraerNombreCarpeta(cert.subject)
  } catch (err) {
    log.warn(`Error resolviendo nombre carpeta para ${serialNumber}: ${(err as Error).message}`)
    return undefined
  }
}
