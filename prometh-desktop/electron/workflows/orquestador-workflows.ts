import { randomUUID } from 'crypto'
import { mkdirSync, existsSync } from 'fs'
import { join } from 'path'
import { app, BrowserWindow } from 'electron'
import log from 'electron-log'
import { evaluarCondicionesDesktop, ejecutarAccionesDesktop } from './motor-desktop'
import {
  registrarEjecucion,
  obtenerEjecuciones,
  obtenerWorkflowsPersonalizados,
  guardarWorkflowPersonalizado,
  eliminarWorkflowPersonalizado,
  duplicarWorkflow,
  limpiarEjecucionesAntiguas,
  obtenerConfigSmtp,
  guardarConfigSmtp,
} from './historial-workflows'
import { obtenerWorkflowsPredefinidos } from './workflows-predefinidos'
import type {
  WorkflowDesktop,
  ContextoEjecucionDesktop,
  ResultadoWorkflowDesktop,
  ProgresoWorkflowDesktop,
  EjecucionWorkflowLocal,
  ConfigSmtpGlobal,
} from './tipos-workflows-desktop'

/**
 * Orquestador de workflows desktop.
 * Coordina ejecucion, historial, y workflows predefinidos/personalizados.
 */
export class OrquestadorWorkflows {
  private readonly ventana: BrowserWindow | null
  private ejecutando: boolean = false

  constructor(ventana?: BrowserWindow | null) {
    this.ventana = ventana ?? null
  }

  /**
   * Lista todos los workflows (predefinidos + personalizados).
   * Los predefinidos se marcan como no editables.
   */
  listarWorkflows(): WorkflowDesktop[] {
    const predefinidos = obtenerWorkflowsPredefinidos()
    const personalizados = obtenerWorkflowsPersonalizados()
    return [...predefinidos, ...personalizados]
  }

  /**
   * Obtiene un workflow por id (busca en predefinidos y personalizados).
   */
  obtenerWorkflow(id: string): WorkflowDesktop | null {
    const todos = this.listarWorkflows()
    return todos.find((w) => w.id === id) ?? null
  }

  /**
   * Guarda un workflow personalizado (crear o actualizar).
   */
  guardarWorkflow(workflow: WorkflowDesktop): void {
    if (workflow.predefinido) {
      throw new Error('No se pueden modificar workflows predefinidos')
    }
    guardarWorkflowPersonalizado(workflow)
  }

  /**
   * Elimina un workflow personalizado.
   */
  eliminarWorkflow(id: string): boolean {
    return eliminarWorkflowPersonalizado(id)
  }

  /**
   * Duplica un workflow (predefinido o personalizado) como personalizado.
   */
  duplicarWorkflow(id: string): WorkflowDesktop | null {
    const original = this.obtenerWorkflow(id)
    if (!original) return null

    const nuevoId = randomUUID()

    if (original.predefinido) {
      // Copiar predefinido como personalizado
      const copia: WorkflowDesktop = {
        ...original,
        id: nuevoId,
        nombre: `${original.nombre} (copia)`,
        predefinido: false,
        creadoEn: new Date().toISOString(),
        actualizadoEn: new Date().toISOString(),
      }
      guardarWorkflowPersonalizado(copia)
      return copia
    }

    return duplicarWorkflow(id, nuevoId)
  }

  /**
   * Ejecuta un workflow por id con el contexto dado.
   * Evalua condiciones, ejecuta acciones secuencialmente, registra resultado.
   */
  async ejecutarWorkflow(
    id: string,
    contexto: Partial<ContextoEjecucionDesktop>
  ): Promise<ResultadoWorkflowDesktop> {
    if (this.ejecutando) {
      return {
        workflowId: id,
        exito: false,
        acciones: [],
        tiempoTotalMs: 0,
        error: 'Ya hay un workflow en ejecucion',
      }
    }

    const workflow = this.obtenerWorkflow(id)
    if (!workflow) {
      return {
        workflowId: id,
        exito: false,
        acciones: [],
        tiempoTotalMs: 0,
        error: `Workflow no encontrado: ${id}`,
      }
    }

    if (!workflow.activo) {
      return {
        workflowId: id,
        exito: false,
        acciones: [],
        tiempoTotalMs: 0,
        error: `Workflow desactivado: ${workflow.nombre}`,
      }
    }

    this.ejecutando = true

    try {
      // Crear carpeta temporal de trabajo
      const carpetaTrabajo = join(
        app.getPath('temp'),
        'certigestor-workflows',
        randomUUID()
      )
      if (!existsSync(carpetaTrabajo)) {
        mkdirSync(carpetaTrabajo, { recursive: true })
      }

      const contextoCompleto: ContextoEjecucionDesktop = {
        carpetaTrabajo,
        ...contexto,
      }

      // Evaluar condiciones
      if (!evaluarCondicionesDesktop(workflow.condiciones, contextoCompleto)) {
        log.info(`[OrqWorkflows] Condiciones no cumplen: ${workflow.nombre}`)
        return {
          workflowId: id,
          exito: false,
          acciones: [],
          tiempoTotalMs: 0,
          error: 'Las condiciones del workflow no se cumplen',
        }
      }

      // Emitir progreso inicial
      this.emitirProgreso({
        workflowId: id,
        workflowNombre: workflow.nombre,
        totalAcciones: workflow.acciones.length,
        accionActual: 0,
        accionNombre: 'Iniciando...',
        estado: 'ejecutando',
        porcentaje: 0,
      })

      // Ejecutar acciones
      const resultado = await ejecutarAccionesDesktop(
        id,
        workflow.nombre,
        workflow.acciones,
        contextoCompleto,
        (porcentaje, accionNombre) => {
          this.emitirProgreso({
            workflowId: id,
            workflowNombre: workflow.nombre,
            totalAcciones: workflow.acciones.length,
            accionActual: Math.round((porcentaje / 100) * workflow.acciones.length),
            accionNombre,
            estado: 'ejecutando',
            porcentaje,
          })
        }
      )

      // Registrar en historial
      const ejecucion: EjecucionWorkflowLocal = {
        id: randomUUID(),
        workflowId: id,
        workflowNombre: workflow.nombre,
        resultado: resultado.exito ? 'exito' : 'error',
        detalles: resultado,
        ejecutadoEn: new Date().toISOString(),
      }
      registrarEjecucion(ejecucion)

      // Progreso final
      this.emitirProgreso({
        workflowId: id,
        workflowNombre: workflow.nombre,
        totalAcciones: workflow.acciones.length,
        accionActual: workflow.acciones.length,
        accionNombre: resultado.exito ? 'Completado' : 'Error',
        estado: resultado.exito ? 'completado' : 'error',
        porcentaje: 100,
      })

      log.info(
        `[OrqWorkflows] Workflow ejecutado: ${workflow.nombre} — ${resultado.exito ? 'exito' : 'error'} (${resultado.tiempoTotalMs}ms)`
      )

      return resultado
    } finally {
      this.ejecutando = false
    }
  }

  /**
   * Procesa workflows que coincidan con un disparador.
   * Fire-and-forget: no lanza errores, solo loguea.
   */
  async procesarDisparador(
    disparador: string,
    contexto: Partial<ContextoEjecucionDesktop>
  ): Promise<void> {
    try {
      const todos = this.listarWorkflows()
      const coinciden = todos.filter(
        (w) => w.activo && w.disparador === disparador
      )

      if (coinciden.length === 0) return

      log.info(`[OrqWorkflows] Disparador "${disparador}": ${coinciden.length} workflow(s)`)

      for (const workflow of coinciden) {
        try {
          await this.ejecutarWorkflow(workflow.id, contexto)
        } catch (error) {
          log.error(`[OrqWorkflows] Error ejecutando workflow ${workflow.nombre}:`, error)
        }
      }
    } catch (error) {
      log.error(`[OrqWorkflows] Error procesando disparador ${disparador}:`, error)
    }
  }

  /**
   * Obtiene el historial de ejecuciones.
   */
  obtenerHistorial(limite: number = 50): EjecucionWorkflowLocal[] {
    return obtenerEjecuciones(limite)
  }

  /**
   * Limpia ejecuciones antiguas del historial.
   */
  limpiarHistorial(mantener: number = 100): number {
    return limpiarEjecucionesAntiguas(mantener)
  }

  /**
   * Obtiene la config SMTP global.
   */
  obtenerConfigSmtp(): ConfigSmtpGlobal | undefined {
    return obtenerConfigSmtp()
  }

  /**
   * Guarda la config SMTP global.
   */
  guardarConfigSmtp(config: ConfigSmtpGlobal): void {
    guardarConfigSmtp(config)
  }

  /**
   * Emite evento de progreso via IPC al renderer.
   */
  private emitirProgreso(progreso: ProgresoWorkflowDesktop): void {
    if (this.ventana && !this.ventana.isDestroyed()) {
      this.ventana.webContents.send('workflows:progreso', progreso)
    }
  }
}
