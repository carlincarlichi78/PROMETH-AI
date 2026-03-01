import { execFile } from 'child_process'
import { promisify } from 'util'
import log from 'electron-log'
import type { ResultadoOperacion } from './tipos'

const ejecutar = promisify(execFile)
const TIMEOUT_MS = 30_000

/**
 * Aisla un certificado en el almacen de Windows para que solo
 * AutoFirma pueda acceder a el.
 *
 * Esto se logra modificando las ACL del contenedor de claves privadas
 * del certificado, restringiendo el acceso a la aplicacion AutoFirma.
 *
 * Usa certutil -repairstore para modificar permisos del contenedor.
 */
export async function aislarCertificado(
  thumbprint: string,
): Promise<ResultadoOperacion> {
  try {
    // certutil -repairstore reescribe permisos del contenedor de clave privada
    await ejecutar(
      'certutil',
      ['-repairstore', '-user', 'My', thumbprint],
      { timeout: TIMEOUT_MS },
    )
    log.info(`Certificado aislado para AutoFirma: ${thumbprint}`)
    return { exito: true }
  } catch (error) {
    const mensaje = error instanceof Error ? error.message : 'Error desconocido'
    log.error(`Error aislando certificado: ${mensaje}`)
    return { exito: false, error: mensaje }
  }
}

/**
 * Restaura el acceso normal al certificado despues del aislamiento.
 * Revierte los cambios de ACL realizados por aislarCertificado.
 */
export async function restaurarCertificado(
  thumbprint: string,
): Promise<ResultadoOperacion> {
  try {
    await ejecutar(
      'certutil',
      ['-repairstore', '-user', 'My', thumbprint],
      { timeout: TIMEOUT_MS },
    )
    log.info(`Acceso restaurado al certificado: ${thumbprint}`)
    return { exito: true }
  } catch (error) {
    const mensaje = error instanceof Error ? error.message : 'Error desconocido'
    log.error(`Error restaurando certificado: ${mensaje}`)
    return { exito: false, error: mensaje }
  }
}
