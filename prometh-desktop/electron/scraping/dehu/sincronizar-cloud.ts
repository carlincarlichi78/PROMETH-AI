import log from 'electron-log'
import type { NotificacionDEHU, ResultadoSincronizacion } from './tipos-dehu'
import { BrowserWindow } from 'electron'
import { notificarResultadoScraping } from '../../tray/servicio-notificaciones'

/**
 * Sincroniza notificaciones DEHU con la API cloud de CertiGestor.
 *
 * Flujo:
 * 1. Mapear notificaciones al formato API
 * 2. Enviar batch a POST /api/notificaciones/sync-desktop
 * 3. Procesar respuesta con detalle de nuevas/actualizadas/errores
 */
export async function sincronizarConCloud(
  notificaciones: NotificacionDEHU[],
  certificadoId: string,
  apiUrl: string,
  token: string,
): Promise<ResultadoSincronizacion> {
  if (notificaciones.length === 0) {
    return { nuevas: 0, actualizadas: 0, errores: 0, detalle: [] }
  }

  log.info(
    `[SyncCloud] Sincronizando ${notificaciones.length} notificaciones con ${apiUrl}`,
  )

  const cuerpo = {
    notificaciones: notificaciones.map((n) =>
      mapearAFormatoApi(n, certificadoId),
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
      data?: {
        nuevas: number
        actualizadas: number
        errores: number
        detalle: Array<{
          idExterno: string
          accion: 'creada' | 'actualizada' | 'error'
          error?: string
        }>
      }
    }

    const data = resultado.data ?? {
      nuevas: 0,
      actualizadas: 0,
      errores: 0,
      detalle: [],
    }

    log.info(
      `[SyncCloud] Resultado: ${data.nuevas} nuevas, ${data.actualizadas} actualizadas, ${data.errores} errores`,
    )

    if (data.nuevas > 0) {
      notificarResultadoScraping(
        true,
        `DEHU: ${data.nuevas} notificacion(es) nueva(s)`,
      )
      const ventana = BrowserWindow.getAllWindows()[0]
      if (ventana && !ventana.isDestroyed()) {
        ventana.webContents.send('notificaciones:nuevas', {
          portal: 'DEHU',
          nuevas: data.nuevas,
        })
      }
    }

    return {
      nuevas: data.nuevas,
      actualizadas: data.actualizadas,
      errores: data.errores,
      detalle: data.detalle.map((d) => ({
        idDehu: d.idExterno,
        accion: d.accion,
        error: d.error,
      })),
    }
  } catch (error) {
    const msg = error instanceof Error ? error.message : 'Error desconocido'
    log.error(`[SyncCloud] Error sincronizando: ${msg}`)

    // Retornar todas como error
    return {
      nuevas: 0,
      actualizadas: 0,
      errores: notificaciones.length,
      detalle: notificaciones.map((n) => ({
        idDehu: n.idDehu,
        accion: 'error' as const,
        error: msg,
      })),
    }
  }
}

/**
 * Mapea una NotificacionDEHU al formato esperado por POST /api/notificaciones/sync-desktop.
 */
function mapearAFormatoApi(
  notif: NotificacionDEHU,
  certificadoId: string,
): Record<string, unknown> {
  return {
    idExterno: notif.idDehu,
    administracion: notif.organismo || 'DEHU',
    tipo: notif.tipo,
    contenido: [notif.titulo, notif.ambito, notif.organismo]
      .filter(Boolean)
      .join(' — '),
    fechaDeteccion: notif.fechaDisposicion || new Date().toISOString(),
    fechaPublicacion: notif.fechaDisposicion || undefined,
    certificadoId,
    estadoPortal: notif.estado || undefined,
  }
}
