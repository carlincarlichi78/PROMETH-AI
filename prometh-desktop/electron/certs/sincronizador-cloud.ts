import { writeFileSync, unlinkSync } from 'fs'
import { join } from 'path'
import { tmpdir } from 'os'
import { randomBytes } from 'crypto'
import log from 'electron-log'
import { listarCertificadosInstalados, instalarCertificado } from './almacen'

export interface ResultadoSyncCloud {
  instalados: string[]
  yaExistentes: number
  errores: Array<{ id: string; error: string }>
}

interface CertCloud {
  id: string
  numeroSerie: string | null
  tieneDatosPfx: boolean
}

interface DatosPfx {
  pfxBase64: string
  password: string
}

/**
 * Sincroniza certificados de la cloud al Windows Certificate Store.
 * Compara por numeroSerie, descarga e instala los faltantes.
 */
export async function sincronizarCertificadosDesdeCloud(
  apiUrl: string,
  token: string,
): Promise<ResultadoSyncCloud> {
  const resultado: ResultadoSyncCloud = { instalados: [], yaExistentes: 0, errores: [] }

  try {
    const certsCloud = await listarCertsCloud(apiUrl, token)
    const conPfx = certsCloud.filter((c) => c.tieneDatosPfx && c.numeroSerie)

    if (conPfx.length === 0) {
      log.info('[sync-cloud] No hay certificados con PFX en la cloud')
      return resultado
    }

    const instalados = await listarCertificadosInstalados()
    const serialesInstalados = new Set(
      instalados.map((c) => c.numeroSerie.toLowerCase()),
    )

    const faltantes = conPfx.filter(
      (c) => !serialesInstalados.has(c.numeroSerie!.toLowerCase()),
    )

    resultado.yaExistentes = conPfx.length - faltantes.length

    if (faltantes.length === 0) {
      log.info('[sync-cloud] Todos los certificados ya estan instalados')
      return resultado
    }

    log.info(`[sync-cloud] ${faltantes.length} certificados por instalar`)

    for (const cert of faltantes) {
      try {
        const datos = await descargarPfx(apiUrl, token, cert.id)
        const rutaTmp = join(tmpdir(), `certigestor-${randomBytes(8).toString('hex')}.pfx`)

        try {
          writeFileSync(rutaTmp, Buffer.from(datos.pfxBase64, 'base64'))

          const res = await instalarCertificado(rutaTmp, datos.password)
          if (res.exito) {
            resultado.instalados.push(cert.numeroSerie!)
            log.info(`[sync-cloud] Instalado: ${cert.numeroSerie}`)
          } else {
            resultado.errores.push({ id: cert.id, error: res.error ?? 'Error desconocido' })
          }
        } finally {
          try { unlinkSync(rutaTmp) } catch { /* ignorar */ }
        }
      } catch (error) {
        const msg = error instanceof Error ? error.message : 'Error desconocido'
        resultado.errores.push({ id: cert.id, error: msg })
        log.error(`[sync-cloud] Error con cert ${cert.id}: ${msg}`)
      }
    }
  } catch (error) {
    const msg = error instanceof Error ? error.message : 'Error desconocido'
    log.error(`[sync-cloud] Error general: ${msg}`)
    resultado.errores.push({ id: 'general', error: msg })
  }

  log.info(
    `[sync-cloud] Resultado: ${resultado.instalados.length} instalados, ` +
    `${resultado.yaExistentes} ya existian, ${resultado.errores.length} errores`,
  )
  return resultado
}

async function listarCertsCloud(apiUrl: string, token: string): Promise<CertCloud[]> {
  const resp = await fetch(`${apiUrl}/certificados?limite=100`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!resp.ok) throw new Error(`Error listando certs: ${resp.status}`)
  const json = await resp.json()
  return json.datos ?? []
}

async function descargarPfx(apiUrl: string, token: string, certId: string): Promise<DatosPfx> {
  const resp = await fetch(`${apiUrl}/certificados/${certId}/descargar-pfx`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!resp.ok) throw new Error(`Error descargando PFX: ${resp.status}`)
  const json = await resp.json()
  return json.datos
}
