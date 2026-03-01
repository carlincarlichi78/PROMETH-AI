import { readFileSync } from 'fs'
import { basename } from 'path'
import log from 'electron-log'
import { obtenerFirmasPendienteSync, marcarSincronizado } from './historial-firmas'
import type { ResultadoSincFirma } from './tipos-firma'

/**
 * Sincroniza las firmas locales pendientes con la API cloud.
 *
 * Para cada firma no sincronizada:
 * 1. Lee el PDF firmado del filesystem
 * 2. Envia POST multipart a /api/firmas (mismo endpoint que la firma web)
 * 3. Marca como sincronizada en historial local
 *
 * Nota: El endpoint POST /api/firmas espera multipart con:
 * - archivo: File (PDF firmado)
 * - certificadoId: string (UUID del cert en BD cloud)
 *
 * Para sincronizar necesitamos el certificadoId de la BD cloud,
 * que se mapea desde el serial del certificado local.
 * Si no se puede resolver el certificadoId, se omite la sincronizacion.
 */
export async function sincronizarFirmasConCloud(
  apiUrl: string,
  token: string,
  mapaCertificados?: Record<string, string>,
): Promise<ResultadoSincFirma> {
  const pendientes = obtenerFirmasPendienteSync()

  if (pendientes.length === 0) {
    log.info('[SyncFirmas] No hay firmas pendientes de sincronizar')
    return { sincronizados: 0, errores: 0 }
  }

  log.info(`[SyncFirmas] Sincronizando ${pendientes.length} firmas con cloud`)

  let sincronizados = 0
  let errores = 0

  for (const firma of pendientes) {
    try {
      // Resolver certificadoId de cloud desde serial local
      const certificadoIdCloud = mapaCertificados?.[firma.certificadoSerial]

      if (!certificadoIdCloud) {
        log.warn(
          `[SyncFirmas] No se encontro certificadoId cloud para serial ${firma.certificadoSerial}`,
        )
        errores++
        continue
      }

      // Leer PDF firmado
      const pdfBuffer = readFileSync(firma.rutaPdfFirmado)
      const nombreArchivo = basename(firma.rutaPdfFirmado)

      // Construir FormData para multipart
      const formData = new FormData()
      const blob = new Blob([pdfBuffer], { type: 'application/pdf' })
      formData.append('archivo', blob, nombreArchivo)
      formData.append('certificadoId', certificadoIdCloud)

      // Enviar a API cloud
      const respuesta = await fetch(`${apiUrl}/api/firmas`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      })

      if (respuesta.ok) {
        marcarSincronizado(firma.id)
        sincronizados++
        log.info(`[SyncFirmas] Firma ${firma.id} sincronizada`)
      } else {
        const textoError = await respuesta.text()
        log.warn(`[SyncFirmas] Error HTTP ${respuesta.status} para firma ${firma.id}: ${textoError}`)
        errores++
      }
    } catch (error) {
      const mensaje = error instanceof Error ? error.message : 'Error desconocido'
      log.error(`[SyncFirmas] Error sincronizando firma ${firma.id}:`, mensaje)
      errores++
    }
  }

  log.info(`[SyncFirmas] Resultado: ${sincronizados} sincronizados, ${errores} errores`)
  return { sincronizados, errores }
}
