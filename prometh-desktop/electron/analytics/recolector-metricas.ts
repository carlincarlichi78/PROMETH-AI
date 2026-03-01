import log from 'electron-log'
import { listarCertificadosInstalados } from '../certs/almacen'
import { obtenerHistorialFirmas } from '../firma/historial-firmas'
import { obtenerDatosWorkflows } from '../workflows/historial-workflows'
import { obtenerHistorial as obtenerHistorialDocs } from '../scraping/documentales/historial-descargas'
import { obtenerDatosScheduler } from '../scheduler/persistencia-scheduler'
import { obtenerDatos as obtenerDatosTray } from '../tray/persistencia-tray'
import type {
  MetricasDesktop,
  MetricasCerts,
  MetricasFirmas,
  MetricasWorkflowsLocal,
  MetricasDocumentales,
  MetricasScheduler,
  MetricasNotificacionesDesktop,
  PuntoActividad,
} from './tipos-analytics'

/** Recolecta todas las metricas del desktop */
export async function recolectarMetricas(): Promise<MetricasDesktop> {
  const [certificados, firmas, workflows, documentales, scheduler, notificacionesDesktop] =
    await Promise.all([
      recolectarMetricasCerts(),
      recolectarMetricasFirmas(),
      recolectarMetricasWorkflows(),
      recolectarMetricasDocumentales(),
      recolectarMetricasScheduler(),
      recolectarMetricasNotificaciones(),
    ])

  return {
    certificados,
    firmas,
    workflows,
    documentales,
    scheduler,
    notificacionesDesktop,
  }
}

/** Metricas de certificados instalados */
export async function recolectarMetricasCerts(): Promise<MetricasCerts> {
  try {
    const certs = await listarCertificadosInstalados()
    const ahora = Date.now()

    const conDias = certs.map((cert) => {
      const vencimiento = new Date(cert.fechaVencimiento).getTime()
      const diasRestantes = Math.floor((vencimiento - ahora) / 86_400_000)
      return { subject: cert.subject, fechaVencimiento: cert.fechaVencimiento, diasRestantes }
    })

    return {
      totalInstalados: certs.length,
      proximosACaducar: conDias.filter((c) => c.diasRestantes > 0 && c.diasRestantes <= 30).length,
      caducados: conDias.filter((c) => c.diasRestantes <= 0).length,
      certificados: conDias.sort((a, b) => a.diasRestantes - b.diasRestantes),
    }
  } catch (error) {
    log.error('[Analytics] Error recolectando metricas certs:', error)
    return { totalInstalados: 0, proximosACaducar: 0, caducados: 0, certificados: [] }
  }
}

/** Metricas de firmas locales */
function recolectarMetricasFirmas(): MetricasFirmas {
  try {
    const historial = obtenerHistorialFirmas()
    const docs = historial.documentos

    const local = docs.filter((d) => d.modo === 'local').length
    const autofirma = docs.filter((d) => d.modo === 'autofirma').length
    const pendientesSync = docs.filter((d) => !d.sincronizadoCloud).length

    // Ultimas 30 para grafica
    const ultimas = docs.slice(-30).map((d) => ({
      fecha: d.fechaFirma.slice(0, 10),
      modo: d.modo,
    }))

    return {
      totalFirmados: docs.length,
      pendientesSync,
      porModo: { local, autofirma },
      historial: ultimas,
    }
  } catch (error) {
    log.error('[Analytics] Error recolectando metricas firmas:', error)
    return { totalFirmados: 0, pendientesSync: 0, porModo: { local: 0, autofirma: 0 }, historial: [] }
  }
}

/** Metricas de workflows locales */
function recolectarMetricasWorkflows(): MetricasWorkflowsLocal {
  try {
    const datos = obtenerDatosWorkflows()
    const ejecuciones = datos.ejecuciones

    const exitosas = ejecuciones.filter((e) => e.resultado.exito).length
    const fallidas = ejecuciones.length - exitosas

    const duraciones = ejecuciones
      .filter((e) => e.resultado.tiempoTotalMs > 0)
      .map((e) => e.resultado.tiempoTotalMs)
    const tiempoPromedioMs = duraciones.length > 0
      ? Math.round(duraciones.reduce((a, b) => a + b, 0) / duraciones.length)
      : 0

    // Ultimas 30
    const ultimas = ejecuciones.slice(-30).map((e) => ({
      fecha: e.ejecutadoEn.slice(0, 10),
      resultado: e.resultado.exito ? 'exito' : 'error',
      duracionMs: e.resultado.tiempoTotalMs,
    }))

    return {
      totalEjecuciones: ejecuciones.length,
      exitosas,
      fallidas,
      tiempoPromedioMs,
      historial: ultimas,
    }
  } catch (error) {
    log.error('[Analytics] Error recolectando metricas workflows:', error)
    return { totalEjecuciones: 0, exitosas: 0, fallidas: 0, tiempoPromedioMs: 0, historial: [] }
  }
}

/** Metricas de descargas documentales */
function recolectarMetricasDocumentales(): MetricasDocumentales {
  try {
    const historial = obtenerHistorialDocs()

    const exitosas = historial.filter((r) => r.exito).length
    const fallidas = historial.length - exitosas

    // Agrupar por tipo
    const porTipo: Record<string, number> = {}
    for (const r of historial) {
      porTipo[r.tipo] = (porTipo[r.tipo] ?? 0) + 1
    }

    // Ultimas 30
    const ultimas = historial.slice(-30).map((r) => ({
      fecha: r.fechaDescarga.slice(0, 10),
      tipo: r.tipo,
      exito: r.exito,
    }))

    return {
      totalDescargas: historial.length,
      exitosas,
      fallidas,
      porTipo,
      historial: ultimas,
    }
  } catch (error) {
    log.error('[Analytics] Error recolectando metricas documentales:', error)
    return { totalDescargas: 0, exitosas: 0, fallidas: 0, porTipo: {}, historial: [] }
  }
}

/** Metricas del scheduler */
function recolectarMetricasScheduler(): MetricasScheduler {
  try {
    const datos = obtenerDatosScheduler()
    const tareasActivas = datos.tareas.filter((t) => t.activa).length
    const hoy = new Date().toISOString().slice(0, 10)
    const ejecucionesHoy = datos.ejecuciones.filter((e) => e.ejecutadoEn.startsWith(hoy))

    return {
      tareasActivas,
      ejecucionesHoy: ejecucionesHoy.length,
      exitosasHoy: ejecucionesHoy.filter((e) => e.resultado === 'exito').length,
      fallidasHoy: ejecucionesHoy.filter((e) => e.resultado === 'error').length,
    }
  } catch (error) {
    log.error('[Analytics] Error recolectando metricas scheduler:', error)
    return { tareasActivas: 0, ejecucionesHoy: 0, exitosasHoy: 0, fallidasHoy: 0 }
  }
}

/** Metricas de notificaciones desktop */
function recolectarMetricasNotificaciones(): MetricasNotificacionesDesktop {
  try {
    const datos = obtenerDatosTray()
    const pendientes = datos.notificaciones.filter((n) => !n.leida).length
    const hoy = new Date().toISOString().slice(0, 10)
    const notifHoy = datos.notificaciones.filter((n) => n.fechaCreacion.startsWith(hoy))

    const porTipo: Record<string, number> = {}
    for (const n of datos.notificaciones) {
      porTipo[n.tipo] = (porTipo[n.tipo] ?? 0) + 1
    }

    return { pendientes, totalHoy: notifHoy.length, porTipo }
  } catch (error) {
    log.error('[Analytics] Error recolectando metricas notificaciones:', error)
    return { pendientes: 0, totalHoy: 0, porTipo: {} }
  }
}

/** Serie temporal de actividad combinada (ultimos N dias) */
export function recolectarActividadTemporal(dias: number = 30): PuntoActividad[] {
  try {
    const firmasHist = obtenerHistorialFirmas().documentos
    const workflowsHist = obtenerDatosWorkflows().ejecuciones
    const docsHist = obtenerHistorialDocs()

    const hoy = new Date()
    const puntos: PuntoActividad[] = []

    for (let i = dias - 1; i >= 0; i--) {
      const fecha = new Date(hoy)
      fecha.setDate(fecha.getDate() - i)
      const fechaStr = fecha.toISOString().slice(0, 10)

      puntos.push({
        fecha: fechaStr,
        firmas: firmasHist.filter((d) => d.fechaFirma.startsWith(fechaStr)).length,
        workflows: workflowsHist.filter((e) => e.ejecutadoEn.startsWith(fechaStr)).length,
        descargas: docsHist.filter((r) => r.fechaDescarga.startsWith(fechaStr)).length,
      })
    }

    return puntos
  } catch (error) {
    log.error('[Analytics] Error recolectando actividad temporal:', error)
    return []
  }
}
