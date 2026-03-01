import { createCipheriv, createDecipheriv, randomBytes, scryptSync } from 'crypto'
import type { DatosBackup } from './tipos-backup'

const ALGORITMO = 'aes-256-gcm'
const IV_BYTES = 16
const SAL_BYTES = 16
const CLAVE_BYTES = 32
const AUTH_TAG_BYTES = 16

/** Cabecera magica para identificar archivos de backup */
const MAGIC = Buffer.from('CGBK', 'ascii') // CertiGestor BackUp

function derivarClave(password: string, sal: Buffer): Buffer {
  return scryptSync(password, sal, CLAVE_BYTES)
}

/**
 * Cifra datos de backup con AES-256-GCM usando password del usuario.
 * Formato: MAGIC(4) + sal(16) + iv(16) + authTag(16) + cifrado(N)
 */
export function cifrarBackup(datos: DatosBackup, password: string): Buffer {
  const json = JSON.stringify(datos)
  const sal = randomBytes(SAL_BYTES)
  const clave = derivarClave(password, sal)
  const iv = randomBytes(IV_BYTES)

  const cifrador = createCipheriv(ALGORITMO, clave, iv)
  const cifrado = Buffer.concat([cifrador.update(json, 'utf8'), cifrador.final()])
  const authTag = cifrador.getAuthTag()

  return Buffer.concat([MAGIC, sal, iv, authTag, cifrado])
}

/**
 * Descifra un buffer de backup con AES-256-GCM.
 * Lanza error si el password es incorrecto o el formato invalido.
 */
export function descifrarBackup(buffer: Buffer, password: string): DatosBackup {
  const offsetMin = MAGIC.length + SAL_BYTES + IV_BYTES + AUTH_TAG_BYTES
  if (buffer.length < offsetMin) {
    throw new Error('Archivo de backup inválido: demasiado pequeño')
  }

  const magic = buffer.subarray(0, MAGIC.length)
  if (!magic.equals(MAGIC)) {
    throw new Error('Archivo de backup inválido: cabecera incorrecta')
  }

  let offset = MAGIC.length
  const sal = buffer.subarray(offset, offset + SAL_BYTES)
  offset += SAL_BYTES
  const iv = buffer.subarray(offset, offset + IV_BYTES)
  offset += IV_BYTES
  const authTag = buffer.subarray(offset, offset + AUTH_TAG_BYTES)
  offset += AUTH_TAG_BYTES
  const cifrado = buffer.subarray(offset)

  const clave = derivarClave(password, sal)

  try {
    const descifrador = createDecipheriv(ALGORITMO, clave, iv)
    descifrador.setAuthTag(authTag)
    const descifrado = Buffer.concat([descifrador.update(cifrado), descifrador.final()])
    return JSON.parse(descifrado.toString('utf8')) as DatosBackup
  } catch {
    throw new Error('Contraseña incorrecta o archivo corrupto')
  }
}
