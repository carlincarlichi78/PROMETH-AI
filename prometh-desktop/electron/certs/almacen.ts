import { execFile } from 'child_process'
import { promisify } from 'util'
import log from 'electron-log'
import type { CertInstaladoWindows, ResultadoOperacion } from './tipos'

const ejecutar = promisify(execFile)
const TIMEOUT_MS = 30_000

/**
 * Instala un certificado P12/PFX en el almacen personal de Windows.
 * Usa certutil -importpfx con almacen de usuario (no requiere admin).
 */
export async function instalarCertificado(
  rutaPfx: string,
  password: string,
): Promise<ResultadoOperacion> {
  try {
    await ejecutar(
      'certutil',
      ['-importpfx', '-user', '-p', password, '-f', rutaPfx],
      { timeout: TIMEOUT_MS },
    )
    log.info(`Certificado instalado: ${rutaPfx}`)
    return { exito: true }
  } catch (error) {
    const mensaje = error instanceof Error ? error.message : 'Error desconocido'
    log.error(`Error instalando certificado: ${mensaje}`)
    return { exito: false, error: mensaje }
  }
}

/**
 * Desinstala un certificado del almacen personal de Windows por thumbprint.
 */
export async function desinstalarCertificado(
  thumbprint: string,
): Promise<ResultadoOperacion> {
  try {
    await ejecutar(
      'certutil',
      ['-delstore', '-user', 'My', thumbprint],
      { timeout: TIMEOUT_MS },
    )
    log.info(`Certificado desinstalado: ${thumbprint}`)
    return { exito: true }
  } catch (error) {
    const mensaje = error instanceof Error ? error.message : 'Error desconocido'
    log.error(`Error desinstalando certificado: ${mensaje}`)
    return { exito: false, error: mensaje }
  }
}

/**
 * Lista los certificados instalados en el almacen personal de Windows.
 * Usa PowerShell para evitar el popup de tarjeta inteligente que provoca certutil.
 * Filtra certificados de Smart Card (DNIe) que no pueden usarse sin dispositivo fisico.
 */
export async function listarCertificadosInstalados(): Promise<CertInstaladoWindows[]> {
  try {
    return await listarConPowerShell()
  } catch (error) {
    log.warn('PowerShell fallo, intentando con certutil:', error)
    try {
      const { stdout } = await ejecutar(
        'certutil',
        ['-store', '-user', 'My'],
        { timeout: TIMEOUT_MS },
      )
      return parsearSalidaCertutil(stdout)
    } catch (err) {
      log.error('Error listando certificados:', err)
      return []
    }
  }
}

/**
 * Lista certificados con PowerShell (no provoca popup de Smart Card).
 * Filtra Smart Card por Issuer (DNIe) sin acceder a PrivateKey (que provoca el popup).
 */
async function listarConPowerShell(): Promise<CertInstaladoWindows[]> {
  const script = `
$certs = Get-ChildItem Cert:\\CurrentUser\\My | Where-Object { $_.HasPrivateKey }
foreach ($c in $certs) {
  $esDNIe = $c.Issuer -match 'DIRECCION GENERAL DE LA POLICIA|DNIE'
  if (-not $esDNIe) {
    Write-Output "CERT_START"
    Write-Output "THUMB:$($c.Thumbprint)"
    Write-Output "SUBJECT:$($c.Subject)"
    Write-Output "ISSUER:$($c.Issuer)"
    Write-Output "NOTAFTER:$($c.NotAfter.ToString('o'))"
    Write-Output "SERIAL:$($c.SerialNumber)"
    Write-Output "CERT_END"
  }
}
`
  const { stdout } = await ejecutar(
    'powershell',
    ['-NoProfile', '-NonInteractive', '-Command', script],
    { timeout: TIMEOUT_MS },
  )
  return parsearSalidaPowerShell(stdout)
}

/**
 * Parsea la salida estructurada de PowerShell.
 */
function parsearSalidaPowerShell(stdout: string): CertInstaladoWindows[] {
  const certificados: CertInstaladoWindows[] = []
  const bloques = stdout.split('CERT_START').filter(b => b.includes('CERT_END'))

  for (const bloque of bloques) {
    const thumbprint = extraerCampoPS(bloque, 'THUMB')
    const subject = extraerCampoPS(bloque, 'SUBJECT')
    const emisor = extraerCampoPS(bloque, 'ISSUER')
    const notAfter = extraerCampoPS(bloque, 'NOTAFTER')
    const serial = extraerCampoPS(bloque, 'SERIAL')

    if (thumbprint && subject) {
      certificados.push({
        thumbprint: thumbprint.replace(/\s/g, '').toLowerCase(),
        subject: subject.trim(),
        emisor: emisor?.trim() ?? '',
        fechaVencimiento: notAfter ? new Date(notAfter).toISOString() : new Date(0).toISOString(),
        numeroSerie: serial?.trim() ?? '',
      })
    }
  }

  return certificados
}

function extraerCampoPS(bloque: string, campo: string): string | null {
  const regex = new RegExp(`${campo}:(.+)`, 'i')
  const match = bloque.match(regex)
  return match?.[1]?.trim() ?? null
}

/**
 * Exporta un certificado del almacen a archivo PFX.
 */
export async function exportarCertificadoPfx(
  thumbprint: string,
  rutaDestino: string,
  password: string,
): Promise<ResultadoOperacion> {
  try {
    await ejecutar(
      'certutil',
      ['-exportpfx', '-user', '-p', password, 'My', thumbprint, rutaDestino],
      { timeout: TIMEOUT_MS },
    )
    log.info(`Certificado exportado a: ${rutaDestino}`)
    return { exito: true }
  } catch (error) {
    const mensaje = error instanceof Error ? error.message : 'Error desconocido'
    log.error(`Error exportando certificado: ${mensaje}`)
    return { exito: false, error: mensaje }
  }
}

/**
 * Parsea la salida de texto de certutil -store -user My.
 * Formato tipico:
 *   ================ Certificado 0 ================
 *   Número de serie: xxxx
 *   Emisor: CN=...
 *   NotAfter: dd/mm/yyyy HH:MM
 *   Sujeto: CN=...
 *   Hash cert.(sha1): xxxx xxxx xxxx
 */
function parsearSalidaCertutil(stdout: string): CertInstaladoWindows[] {
  const certificados: CertInstaladoWindows[] = []
  // Dividir por bloques de certificado
  const bloques = stdout.split(/={10,}\s*Certificad[eo]\s+\d+\s*={10,}/i)

  for (const bloque of bloques) {
    if (!bloque.trim()) continue

    const thumbprint = extraerCampo(bloque, /Hash\s+cert\.\(sha1\):\s*(.+)/i)
    const subject = extraerCampo(bloque, /Sujeto?:\s*(.+)/i) ??
                    extraerCampo(bloque, /Subject:\s*(.+)/i)
    const emisor = extraerCampo(bloque, /Emisor:\s*(.+)/i) ??
                   extraerCampo(bloque, /Issuer:\s*(.+)/i)
    const notAfter = extraerCampo(bloque, /NotAfter:\s*(.+)/i)
    const serial = extraerCampo(bloque, /N[úu]mero de serie:\s*(.+)/i) ??
                   extraerCampo(bloque, /Serial Number:\s*(.+)/i)

    if (thumbprint && subject) {
      certificados.push({
        thumbprint: thumbprint.replace(/\s/g, '').toLowerCase(),
        subject: subject.trim(),
        emisor: emisor?.trim() ?? '',
        fechaVencimiento: parsearFechaCertutil(notAfter),
        numeroSerie: serial?.trim() ?? '',
      })
    }
  }

  return certificados
}

function extraerCampo(texto: string, regex: RegExp): string | null {
  const match = texto.match(regex)
  return match?.[1]?.trim() ?? null
}

/**
 * Parsea fecha de certutil (formato variable segun locale de Windows).
 * Intenta varios formatos comunes.
 */
function parsearFechaCertutil(valor: string | null): string {
  if (!valor) return new Date(0).toISOString()

  // certutil puede devolver: "dd/mm/yyyy HH:MM" o "mm/dd/yyyy HH:MM" segun locale
  const fecha = new Date(valor)
  if (!isNaN(fecha.getTime())) return fecha.toISOString()

  // Intentar formato europeo dd/mm/yyyy
  const partes = valor.match(/(\d{1,2})\/(\d{1,2})\/(\d{4})/)
  if (partes) {
    const [, dia, mes, anio] = partes
    const intentoEuropeo = new Date(`${anio}-${mes}-${dia}`)
    if (!isNaN(intentoEuropeo.getTime())) return intentoEuropeo.toISOString()
  }

  return new Date(0).toISOString()
}
