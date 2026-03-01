import log from 'electron-log'
import type {
  NotificacionPortal,
  ResultadoSincronizacionPortal,
} from './tipos-notificaciones'
import type { PortalNotificaciones } from './tipos-notificaciones'
import { extraerTextoPdf } from '../../ocr/extraer-texto-pdf'
import { BrowserWindow } from 'electron'
import { notificarResultadoScraping } from '../../tray/servicio-notificaciones'

/**
 * Mapea una NotificacionPortal al formato esperado por el endpoint
 * POST /api/notificaciones/sync-desktop (upsert por idExterno+orgId).
 */
function mapearAFormatoApi(
  notif: NotificacionPortal,
  certificadoId: string,
  portal: PortalNotificaciones,
): Record<string, unknown> {
  return {
    idExterno: notif.idExterno,
    administracion: notif.organismo || portal,
    tipo: notif.tipo,
    contenido: notif.contenidoExtraido ?? notif.titulo,
    fechaDeteccion: notif.fechaDisposicion || new Date().toISOString(),
    fechaPublicacion: notif.fechaDisposicion || undefined,
    certificadoId,
    origen: portal,
    estadoPortal: notif.estado || undefined,
  }
}

/**
 * Sincroniza notificaciones de cualquier portal con la API cloud.
 * Reutiliza el endpoint POST /api/notificaciones/sync-desktop
 * enviando `origen` para distinguir la fuente.
 */
export async function sincronizarPortalConCloud(
  notificaciones: NotificacionPortal[],
  certificadoId: string,
  portal: PortalNotificaciones,
  apiUrl: string,
  token: string,
): Promise<ResultadoSincronizacionPortal> {
  if (notificaciones.length === 0) {
    return { portal, nuevas: 0, actualizadas: 0, errores: 0 }
  }

  log.info(
    `[SyncNotif] Sincronizando ${notificaciones.length} de ${portal} con cloud`,
  )

  // Extraer texto de PDFs descargados (con fallback vision si tesseract falla)
  for (const notif of notificaciones) {
    if (notif.rutaPdfLocal && !notif.contenidoExtraido) {
      try {
        const texto = await extraerTextoPdf(notif.rutaPdfLocal, {
          apiUrl,
          token,
        })
        if (texto) {
          notif.contenidoExtraido = texto
        }
      } catch (err) {
        log.warn(
          `[SyncNotif] Error OCR para ${notif.idExterno}: ${(err as Error).message}`,
        )
      }
    }
  }

  const cuerpo = {
    notificaciones: notificaciones.map((n) =>
      mapearAFormatoApi(n, certificadoId, portal),
    ),
  }

  try {
    const response = await fetch(`${apiUrl}/notificaciones/sync-desktop`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(cuerpo),
    })

    if (!response.ok) {
      const texto = await response.text()
      throw new Error(`HTTP ${response.status}: ${texto}`)
    }

    const resultado = (await response.json()) as {
      data?: { nuevas: number; actualizadas: number; errores: number }
    }
    const data = resultado.data ?? { nuevas: 0, actualizadas: 0, errores: 0 }

    log.info(
      `[SyncNotif] ${portal}: ${data.nuevas} nuevas, ${data.actualizadas} actualizadas`,
    )

    if (data.nuevas > 0) {
      notificarResultadoScraping(
        true,
        `${portal}: ${data.nuevas} notificacion(es) nueva(s)`,
      )
      // Emitir evento al renderer para toast en UI
      const ventana = BrowserWindow.getAllWindows()[0]
      if (ventana && !ventana.isDestroyed()) {
        ventana.webContents.send('notificaciones:nuevas', {
          portal,
          nuevas: data.nuevas,
        })
      }
    }

    return { portal, ...data }
  } catch (error) {
    const msg = error instanceof Error ? error.message : 'Error desconocido'
    log.error(`[SyncNotif] Error en ${portal}: ${msg}`)
    return { portal, nuevas: 0, actualizadas: 0, errores: notificaciones.length }
  }
}
