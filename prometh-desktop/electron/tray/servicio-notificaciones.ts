import { randomUUID } from 'crypto'
import log from 'electron-log'
import { listarCertificadosInstalados } from '../certs/almacen'
import {
  agregarNotificacion,
  obtenerConfig,
  obtenerEstadoTray,
  obtenerNotificaciones,
} from './persistencia-tray'
import { GestorTray } from './gestor-tray'
import type {
  NotificacionDesktop,
  TipoNotificacionDesktop,
  PrioridadNotificacion,
} from './tipos-tray'
import type { TareaProgramada, EjecucionScheduler } from '../scheduler/tipos-scheduler'

let gestorTray: GestorTray | null = null

/** Configura la referencia al gestor de tray (llamado desde handlers/tray.ts) */
export function setGestorTray(gestor: GestorTray): void {
  gestorTray = gestor
}

/** Crea y persiste una notificacion, la envia al tray si corresponde */
function crearNotificacion(
  tipo: TipoNotificacionDesktop,
  titulo: string,
  mensaje: string,
  prioridad: PrioridadNotificacion,
  datosExtra?: Record<string, unknown>,
): void {
  const config = obtenerConfig()

  // Verificar si este tipo esta habilitado
  if (tipo.startsWith('scraping') && !config.notificarScraping) return
  if (tipo.startsWith('workflow') && !config.notificarWorkflows) return
  if (tipo === 'sync_completada' && !config.notificarSync) return

  const notif: NotificacionDesktop = {
    id: randomUUID(),
    tipo,
    titulo,
    mensaje,
    prioridad,
    leida: false,
    fechaCreacion: new Date().toISOString(),
    datosExtra,
  }

  agregarNotificacion(notif)

  // Enviar notificacion nativa si esta habilitado
  if (config.nativasActivas && gestorTray) {
    gestorTray.enviarNativa(notif)
    const estado = obtenerEstadoTray()
    gestorTray.actualizarBadge(estado.pendientes)
  }
}

/** Verifica certificados proximos a caducar y genera notificaciones */
export async function verificarCertificadosCaducan(): Promise<number> {
  try {
    const config = obtenerConfig()
    const certs = await listarCertificadosInstalados()
    const ahora = Date.now()
    let nuevas = 0

    // Obtener notificaciones existentes para no duplicar
    const existentes = obtenerNotificaciones(200)
    const hoy = new Date().toISOString().slice(0, 10)

    for (const cert of certs) {
      const vencimiento = new Date(cert.fechaVencimiento).getTime()
      const diasRestantes = Math.floor((vencimiento - ahora) / 86_400_000)

      if (diasRestantes <= 0) {
        // Certificado caducado
        const yaNotifico = existentes.some(
          (n) => n.tipo === 'certificado_caduca' && n.datosExtra?.serial === cert.numeroSerie && n.fechaCreacion.startsWith(hoy)
        )
        if (!yaNotifico) {
          crearNotificacion(
            'certificado_caduca',
            'Certificado caducado',
            `${cert.subject} ha caducado`,
            'alta',
            { serial: cert.numeroSerie },
          )
          nuevas++
        }
      } else if (diasRestantes <= config.diasAvisoCaducidad) {
        const yaNotifico = existentes.some(
          (n) => n.tipo === 'certificado_caduca' && n.datosExtra?.serial === cert.numeroSerie && n.fechaCreacion.startsWith(hoy)
        )
        if (!yaNotifico) {
          crearNotificacion(
            'certificado_caduca',
            'Certificado proximo a caducar',
            `${cert.subject} caduca en ${diasRestantes} dia(s)`,
            diasRestantes <= 7 ? 'alta' : 'media',
            { serial: cert.numeroSerie, diasRestantes },
          )
          nuevas++
        }
      }
    }

    log.info(`[ServicioNotif] Verificacion certs: ${nuevas} nuevas notificaciones`)
    return nuevas
  } catch (error) {
    log.error('[ServicioNotif] Error verificando certs:', error)
    return 0
  }
}

/** Notifica resultado de scraping */
export function notificarResultadoScraping(exito: boolean, detalles?: string): void {
  crearNotificacion(
    exito ? 'scraping_completado' : 'scraping_error',
    exito ? 'Scraping completado' : 'Error en scraping',
    detalles ?? (exito ? 'El scraping se completo correctamente' : 'Hubo un error durante el scraping'),
    exito ? 'baja' : 'alta',
  )
}

/** Notifica resultado de workflow */
export function notificarResultadoWorkflow(nombre: string, exito: boolean, detalles?: string): void {
  crearNotificacion(
    exito ? 'workflow_completado' : 'workflow_error',
    exito ? 'Workflow completado' : 'Error en workflow',
    detalles ?? `Workflow "${nombre}" ${exito ? 'completado' : 'fallo'}`,
    exito ? 'baja' : 'media',
    { workflowNombre: nombre },
  )
}

/** Notifica resultado de sync cloud */
export function notificarSyncCompletada(detalles: string): void {
  crearNotificacion(
    'sync_completada',
    'Sincronizacion completada',
    detalles,
    'baja',
  )
}

/** Notifica resultado de una tarea del scheduler (invocado por motor-scheduler via import dinamico) */
export function notificarResultadoTareaScheduler(tarea: TareaProgramada, ejecucion: EjecucionScheduler): void {
  const exito = ejecucion.resultado === 'exito'
  crearNotificacion(
    'tarea_scheduler',
    `Tarea ${exito ? 'completada' : 'fallida'}: ${tarea.nombre}`,
    ejecucion.mensaje,
    exito ? 'baja' : 'media',
    { tareaId: tarea.id, resultado: ejecucion.resultado },
  )
}

/** Ejecuta todos los chequeos periodicos (invocado por scheduler) */
export async function ejecutarChequeosPeriodicos(): Promise<number> {
  let totalNuevas = 0
  totalNuevas += await verificarCertificadosCaducan()
  return totalNuevas
}
