import { createHash } from 'crypto'
import { statSync, readFileSync, writeFileSync } from 'fs'
import { join } from 'path'
import { app } from 'electron'
import log from 'electron-log'
import { obtenerHistorial, obtenerTodasLasConfigs, guardarConfig } from './historial-descargas'
import { CATALOGO_DOCUMENTOS } from './catalogo'
import type { RegistroHistorialDescarga, TipoDocumento } from './tipos-documentales'

const ARCHIVO_HISTORIAL = 'certigestor-historial-docs.json'

interface ResultadoSincDocs {
  sincronizados: number
  errores: number
}

/**
 * Genera un id externo determinista para un registro de descarga.
 * Formato: hash SHA-256 de "serial_tipo_fecha"
 */
function generarIdExterno(certificadoSerial: string, tipo: string, fechaDescarga: string): string {
  const datos = `${certificadoSerial}_${tipo}_${fechaDescarga}`
  return createHash('sha256').update(datos).digest('hex').substring(0, 64)
}

/**
 * Resuelve el portal de origen dado un tipo de documento.
 */
function resolverPortal(tipo: string): string {
  const doc = CATALOGO_DOCUMENTOS.find(d => d.id === tipo)
  return doc?.portal ?? 'DESCONOCIDO'
}

/**
 * Calcula el tamano total de los archivos descargados.
 */
function calcularTamano(rutasArchivos: string[]): number | undefined {
  try {
    let total = 0
    for (const ruta of rutasArchivos) {
      const info = statSync(ruta)
      total += info.size
    }
    return total > 0 ? total : undefined
  } catch {
    return undefined
  }
}

/**
 * Sincroniza los documentos descargados pendientes con la API cloud.
 * Solo envia metadata (no PDFs).
 */
export async function sincronizarDocsConCloud(
  apiUrl: string,
  token: string,
): Promise<ResultadoSincDocs> {
  const historial = obtenerHistorial()
  const pendientes = historial.filter(r => !r.sincronizadoCloud)

  if (pendientes.length === 0) {
    log.info('[SyncDocs] No hay documentos pendientes de sincronizar')
    return { sincronizados: 0, errores: 0 }
  }

  log.info(`[SyncDocs] Sincronizando ${pendientes.length} documentos con cloud`)

  // Enviar en batches de 50
  const BATCH_SIZE = 50
  let sincronizados = 0
  let errores = 0

  for (let i = 0; i < pendientes.length; i += BATCH_SIZE) {
    const batch = pendientes.slice(i, i + BATCH_SIZE)

    const documentos = batch.map(reg => ({
      idExterno: generarIdExterno(reg.certificadoSerial, reg.tipo, reg.fechaDescarga),
      tipo: reg.tipo,
      nombreArchivo: reg.rutasArchivos[0]
        ? reg.rutasArchivos[0].split(/[/\\]/).pop() ?? `${reg.tipo}.pdf`
        : `${reg.tipo}.pdf`,
      portal: resolverPortal(reg.tipo),
      exito: reg.exito,
      error: reg.error,
      tamanoBytes: calcularTamano(reg.rutasArchivos),
      fechaDescarga: reg.fechaDescarga,
      certificadoSerial: reg.certificadoSerial,
    }))

    try {
      const respuesta = await fetch(`${apiUrl}/api/documentos-descargados/sync-desktop`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ documentos }),
      })

      if (respuesta.ok) {
        // Marcar como sincronizados en el batch (referencia directa al array)
        for (const reg of batch) {
          reg.sincronizadoCloud = true
        }
        sincronizados += batch.length
        log.info(`[SyncDocs] Batch ${Math.floor(i / BATCH_SIZE) + 1} sincronizado: ${batch.length} docs`)
      } else {
        const textoError = await respuesta.text()
        log.warn(`[SyncDocs] Error HTTP ${respuesta.status}: ${textoError}`)
        errores += batch.length
      }
    } catch (error) {
      const mensaje = error instanceof Error ? error.message : 'Error desconocido'
      log.error(`[SyncDocs] Error de red: ${mensaje}`)
      errores += batch.length
    }
  }

  // Guardar historial actualizado con flags sincronizadoCloud
  if (sincronizados > 0) {
    const ruta = join(app.getPath('userData'), ARCHIVO_HISTORIAL)
    // Releer historial completo y actualizar los registros sincronizados
    const historialCompleto: RegistroHistorialDescarga[] = (() => {
      try {
        return JSON.parse(readFileSync(ruta, 'utf-8')) as RegistroHistorialDescarga[]
      } catch {
        return []
      }
    })()

    for (const reg of historialCompleto) {
      const sincronizado = pendientes.find(
        p => p.certificadoSerial === reg.certificadoSerial &&
             p.tipo === reg.tipo &&
             p.fechaDescarga === reg.fechaDescarga &&
             p.sincronizadoCloud,
      )
      if (sincronizado) {
        reg.sincronizadoCloud = true
      }
    }

    const recortado = historialCompleto.length > 500 ? historialCompleto.slice(-500) : historialCompleto
    writeFileSync(ruta, JSON.stringify(recortado, null, 2), 'utf-8')
  }

  log.info(`[SyncDocs] Resultado: ${sincronizados} sincronizados, ${errores} errores`)
  return { sincronizados, errores }
}

/**
 * Sincroniza la config de documentos activos (por certificado) con la API cloud.
 * Sube todas las configs locales en un solo POST batch.
 */
export async function sincronizarConfigConCloud(
  apiUrl: string,
  token: string,
): Promise<{ sincronizados: number; errores: number }> {
  const configLocal = obtenerTodasLasConfigs()
  const seriales = Object.keys(configLocal)

  if (seriales.length === 0) {
    log.info('[SyncConfig] No hay configs de documentos para sincronizar')
    return { sincronizados: 0, errores: 0 }
  }

  log.info(`[SyncConfig] Sincronizando config de ${seriales.length} certificados con cloud`)

  const configs = seriales.map(serial => ({
    certificadoSerial: serial,
    documentosActivos: configLocal[serial].documentosActivos,
    datosExtra: configLocal[serial].datosExtra,
  }))

  try {
    const respuesta = await fetch(`${apiUrl}/api/documentos-descargados/sync-config-desktop`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ configs }),
    })

    if (respuesta.ok) {
      log.info(`[SyncConfig] ${configs.length} configs sincronizadas con cloud`)
      return { sincronizados: configs.length, errores: 0 }
    }

    const textoError = await respuesta.text()
    log.warn(`[SyncConfig] Error HTTP ${respuesta.status}: ${textoError}`)
    return { sincronizados: 0, errores: configs.length }
  } catch (error) {
    const mensaje = error instanceof Error ? error.message : 'Error desconocido'
    log.error(`[SyncConfig] Error de red: ${mensaje}`)
    return { sincronizados: 0, errores: configs.length }
  }
}

/**
 * Recupera la config de documentos activos desde la API cloud y la guarda localmente.
 * Sobreescribe la config local de cada certificado recibido.
 */
export async function recuperarConfigDesdeCloud(
  apiUrl: string,
  token: string,
): Promise<{ recuperados: number }> {
  log.info('[SyncConfig] Recuperando config de documentos desde cloud')

  try {
    const respuesta = await fetch(`${apiUrl}/api/documentos-descargados/config`, {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })

    if (!respuesta.ok) {
      const textoError = await respuesta.text()
      log.warn(`[SyncConfig] Error HTTP ${respuesta.status}: ${textoError}`)
      return { recuperados: 0 }
    }

    const datos = (await respuesta.json()) as {
      configs: Array<{
        certificadoSerial: string
        documentosActivos: TipoDocumento[]
        datosExtra?: Record<string, unknown>
      }>
    }

    if (!datos.configs || datos.configs.length === 0) {
      log.info('[SyncConfig] No hay configs en cloud para recuperar')
      return { recuperados: 0 }
    }

    for (const cfg of datos.configs) {
      guardarConfig(cfg.certificadoSerial, cfg.documentosActivos, cfg.datosExtra)
    }

    log.info(`[SyncConfig] ${datos.configs.length} configs recuperadas desde cloud`)
    return { recuperados: datos.configs.length }
  } catch (error) {
    const mensaje = error instanceof Error ? error.message : 'Error desconocido'
    log.error(`[SyncConfig] Error de red: ${mensaje}`)
    return { recuperados: 0 }
  }
}
