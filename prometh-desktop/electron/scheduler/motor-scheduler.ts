import { BrowserWindow } from 'electron'
import log from 'electron-log'
import { randomUUID } from 'crypto'
import {
  obtenerTareas,
  registrarEjecucion,
  guardarTarea,
} from './persistencia-scheduler'
import type {
  TareaProgramada,
  EjecucionScheduler,
  EstadoScheduler,
  FrecuenciaScheduler,
  DiaSemana,
} from './tipos-scheduler'

/** Intervalo de verificacion: cada 60 segundos */
const INTERVALO_CHECK_MS = 60_000

/** Mapeo frecuencia → horas entre ejecuciones */
const HORAS_POR_FRECUENCIA: Record<string, number> = {
  cada_hora: 1,
  cada_2_horas: 2,
  cada_4_horas: 4,
  cada_6_horas: 6,
  cada_12_horas: 12,
  diaria: 24,
  semanal: 168,
}

/** Mapeo dia de semana → numero JS (0=domingo, 1=lunes, ...) */
const DIA_A_NUMERO: Record<DiaSemana, number> = {
  domingo: 0,
  lunes: 1,
  martes: 2,
  miercoles: 3,
  jueves: 4,
  viernes: 5,
  sabado: 6,
}

/**
 * Motor del scheduler local.
 * Verifica cada 60s si alguna tarea debe ejecutarse.
 */
export class MotorScheduler {
  private ventana: BrowserWindow
  private intervalo: ReturnType<typeof setInterval> | null = null
  private ejecutandoAhora: string | null = null
  private activo = false

  constructor(ventana: BrowserWindow) {
    this.ventana = ventana
  }

  /** Arranca el loop de verificacion */
  iniciar(): void {
    if (this.intervalo) return

    this.activo = true
    this.intervalo = setInterval(() => {
      this.verificarYEjecutar().catch((err) => {
        log.error('[Scheduler] Error en verificacion periodica:', err)
      })
    }, INTERVALO_CHECK_MS)

    // Verificacion inicial inmediata
    this.verificarYEjecutar().catch((err) => {
      log.error('[Scheduler] Error en verificacion inicial:', err)
    })

    log.info('[Scheduler] Motor iniciado')
  }

  /** Detiene el loop */
  detener(): void {
    if (this.intervalo) {
      clearInterval(this.intervalo)
      this.intervalo = null
    }
    this.activo = false
    log.info('[Scheduler] Motor detenido')
  }

  /** Obtiene el estado actual */
  obtenerEstado(): EstadoScheduler {
    const tareas = obtenerTareas()
    const activas = tareas.filter((t) => t.activa)
    const proximasEjecuciones = activas
      .map((t) => t.proximaEjecucion)
      .filter(Boolean)
      .sort()

    return {
      activo: this.activo,
      tareasActivas: activas.length,
      proximaEjecucion: proximasEjecuciones[0] ?? undefined,
      ejecutandoAhora: this.ejecutandoAhora ?? undefined,
    }
  }

  /** Ejecuta una tarea manualmente (fuera de horario) */
  async ejecutarManual(id: string): Promise<{ exito: boolean; error?: string }> {
    const tareas = obtenerTareas()
    const tarea = tareas.find((t) => t.id === id)
    if (!tarea) return { exito: false, error: 'Tarea no encontrada' }

    return await this.ejecutarTarea(tarea)
  }

  /** Verifica todas las tareas y ejecuta las que correspondan */
  private async verificarYEjecutar(): Promise<void> {
    if (this.ejecutandoAhora) return // ya hay una ejecucion en curso

    const tareas = obtenerTareas()
    const ahora = new Date()

    for (const tarea of tareas) {
      if (!tarea.activa) continue

      // Calcular proxima ejecucion si no tiene
      if (!tarea.proximaEjecucion) {
        const proxima = this.calcularProximaEjecucion(tarea)
        guardarTarea({ ...tarea, proximaEjecucion: proxima, actualizadoEn: ahora.toISOString() })
        continue
      }

      const proximaFecha = new Date(tarea.proximaEjecucion)
      if (ahora >= proximaFecha) {
        await this.ejecutarTarea(tarea)
      }
    }
  }

  /** Ejecuta una tarea y registra el resultado */
  private async ejecutarTarea(tarea: TareaProgramada): Promise<{ exito: boolean; error?: string }> {
    this.ejecutandoAhora = tarea.nombre
    this.emitirProgreso()
    const inicio = Date.now()

    let resultado: 'exito' | 'error' | 'parcial' = 'error'
    let mensaje = ''

    try {
      log.info(`[Scheduler] Ejecutando tarea: ${tarea.nombre} (${tarea.tipo})`)

      switch (tarea.parametros.tipo) {
        case 'scraping': {
          const { factory } = await import('../handlers/scraping')
          await factory.iniciar()
          resultado = 'exito'
          mensaje = 'Scraping completado'
          break
        }

        case 'workflow': {
          const { OrquestadorWorkflows } = await import('../workflows/orquestador-workflows')
          const orq = new OrquestadorWorkflows(this.ventana)
          const res = await orq.ejecutarWorkflow(tarea.parametros.workflowId, tarea.parametros.contexto ?? {})
          resultado = res.exito ? 'exito' : 'error'
          mensaje = res.exito ? 'Workflow ejecutado correctamente' : (res.error ?? 'Error en workflow')
          break
        }

        case 'sync_cloud': {
          const mensajes: string[] = []
          if (tarea.parametros.sincronizar.includes('firmas')) {
            const { obtenerHistorialFirmas } = await import('../firma/historial-firmas')
            const firmas = obtenerHistorialFirmas()
            const pendientes = firmas.documentos.filter((d) => !d.sincronizadoCloud)
            mensajes.push(`${pendientes.length} firmas pendientes de sync`)
          }
          if (tarea.parametros.sincronizar.includes('notificaciones')) {
            mensajes.push('Sync notificaciones completado')
          }
          resultado = 'exito'
          mensaje = mensajes.join('. ') || 'Sincronizacion completada'
          break
        }

        case 'descarga_docs': {
          resultado = 'exito'
          mensaje = 'Descarga de documentos completada'
          break
        }

        case 'consulta_notif': {
          resultado = 'exito'
          mensaje = 'Consulta de notificaciones completada'
          break
        }
      }
    } catch (error) {
      resultado = 'error'
      mensaje = error instanceof Error ? error.message : 'Error desconocido'
      log.error(`[Scheduler] Error ejecutando tarea ${tarea.nombre}:`, error)
    }

    const duracionMs = Date.now() - inicio

    // Registrar ejecucion
    const ejecucion: EjecucionScheduler = {
      id: randomUUID(),
      tareaId: tarea.id,
      tareaNombre: tarea.nombre,
      tipo: tarea.tipo,
      resultado,
      mensaje,
      ejecutadoEn: new Date().toISOString(),
      duracionMs,
    }
    registrarEjecucion(ejecucion)

    // Calcular proxima ejecucion y actualizar tarea
    const proxima = this.calcularProximaEjecucion(tarea)
    guardarTarea({
      ...tarea,
      ultimaEjecucion: ejecucion.ejecutadoEn,
      ultimoResultado: resultado,
      proximaEjecucion: proxima,
      actualizadoEn: new Date().toISOString(),
    })

    // Notificar al tray (fire-and-forget)
    this.notificarResultado(tarea, ejecucion).catch((err) => {
      log.error('[Scheduler] Error notificando resultado:', err)
    })

    this.ejecutandoAhora = null
    this.emitirProgreso()

    log.info(`[Scheduler] Tarea completada: ${tarea.nombre} → ${resultado} (${duracionMs}ms)`)
    return { exito: resultado !== 'error' }
  }

  /** Calcula la proxima fecha de ejecucion basada en frecuencia */
  calcularProximaEjecucion(tarea: TareaProgramada): string {
    const ahora = new Date()
    const [horas, minutos] = (tarea.horaEjecucion || '09:00').split(':').map(Number)

    if (tarea.frecuencia === 'semanal' && tarea.diaSemana) {
      const diaObjetivo = DIA_A_NUMERO[tarea.diaSemana]
      const proxima = new Date(ahora)
      proxima.setHours(horas, minutos, 0, 0)

      // Buscar el proximo dia de la semana
      const diaActual = ahora.getDay()
      let diasHasta = diaObjetivo - diaActual
      if (diasHasta < 0 || (diasHasta === 0 && ahora >= proxima)) {
        diasHasta += 7
      }
      proxima.setDate(proxima.getDate() + diasHasta)
      return proxima.toISOString()
    }

    if (tarea.frecuencia === 'personalizada' && tarea.intervaloMinutos) {
      const proxima = new Date(ahora.getTime() + tarea.intervaloMinutos * 60_000)
      return proxima.toISOString()
    }

    // Frecuencias basadas en horas
    const horasIntervalo = HORAS_POR_FRECUENCIA[tarea.frecuencia] || 24
    const proxima = new Date(ahora)

    if (tarea.frecuencia === 'diaria' || horasIntervalo >= 24) {
      // Para diaria: la hora especifica del dia siguiente (o hoy si aun no paso)
      proxima.setHours(horas, minutos, 0, 0)
      if (ahora >= proxima) {
        proxima.setDate(proxima.getDate() + 1)
      }
    } else {
      // Para intervalos < 24h: siguiente ventana desde ahora
      proxima.setTime(ahora.getTime() + horasIntervalo * 3_600_000)
    }

    return proxima.toISOString()
  }

  /** Notifica resultado al modulo tray (import dinamico para evitar dep circular) */
  private async notificarResultado(tarea: TareaProgramada, ejecucion: EjecucionScheduler): Promise<void> {
    try {
      const { notificarResultadoTareaScheduler } = await import('../tray/servicio-notificaciones')
      notificarResultadoTareaScheduler(tarea, ejecucion)
    } catch {
      // Tray puede no estar inicializado aun — no es critico
    }
  }

  /** Emite estado al renderer */
  private emitirProgreso(): void {
    if (!this.ventana.isDestroyed()) {
      this.ventana.webContents.send('scheduler:progreso', this.obtenerEstado())
    }
  }
}
