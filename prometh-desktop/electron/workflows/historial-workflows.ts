import { existsSync, readFileSync, writeFileSync, mkdirSync } from 'fs'
import { join, dirname } from 'path'
import { app } from 'electron'
import log from 'electron-log'
import type {
  WorkflowDesktop,
  EjecucionWorkflowLocal,
  HistorialWorkflowsLocal,
  ConfigSmtpGlobal,
} from './tipos-workflows-desktop'

const NOMBRE_ARCHIVO = 'certigestor-workflows-desktop.json'

/** Obtiene la ruta completa del archivo de datos */
function obtenerRutaArchivo(): string {
  return join(app.getPath('userData'), NOMBRE_ARCHIVO)
}

/** Historial vacio por defecto */
function crearDatosVacios(): HistorialWorkflowsLocal {
  return {
    ejecuciones: [],
    workflowsPersonalizados: [],
  }
}

/**
 * Lee los datos de workflows desktop desde el archivo JSON.
 * Si no existe, retorna datos vacios.
 */
export function obtenerDatosWorkflows(): HistorialWorkflowsLocal {
  const ruta = obtenerRutaArchivo()

  if (!existsSync(ruta)) {
    return crearDatosVacios()
  }

  try {
    const contenido = readFileSync(ruta, 'utf-8')
    const datos: HistorialWorkflowsLocal = JSON.parse(contenido)
    return datos
  } catch (error) {
    log.warn('[HistorialWorkflows] Error leyendo datos, creando nuevos:', error)
    return crearDatosVacios()
  }
}

/**
 * Guarda los datos completos en el archivo JSON.
 */
function guardarDatos(datos: HistorialWorkflowsLocal): void {
  const ruta = obtenerRutaArchivo()
  const directorio = dirname(ruta)

  if (!existsSync(directorio)) {
    mkdirSync(directorio, { recursive: true })
  }

  writeFileSync(ruta, JSON.stringify(datos, null, 2), 'utf-8')
}

// --- Ejecuciones ---

/**
 * Registra una ejecucion de workflow en el historial.
 * Inmutable: crea nuevo array con la ejecucion anadida.
 */
export function registrarEjecucion(ejecucion: EjecucionWorkflowLocal): void {
  const datos = obtenerDatosWorkflows()

  const nuevosDatos: HistorialWorkflowsLocal = {
    ...datos,
    ejecuciones: [...datos.ejecuciones, ejecucion],
  }

  guardarDatos(nuevosDatos)
  log.info(`[HistorialWorkflows] Ejecucion registrada: ${ejecucion.id}`)
}

/**
 * Obtiene las ultimas N ejecuciones del historial.
 */
export function obtenerEjecuciones(limite: number = 50): EjecucionWorkflowLocal[] {
  const datos = obtenerDatosWorkflows()
  return datos.ejecuciones
    .slice(-limite)
    .reverse()
}

/**
 * Limpia ejecuciones antiguas (mantiene las ultimas N).
 */
export function limpiarEjecucionesAntiguas(mantener: number = 100): number {
  const datos = obtenerDatosWorkflows()
  const total = datos.ejecuciones.length

  if (total <= mantener) return 0

  const eliminadas = total - mantener
  const nuevosDatos: HistorialWorkflowsLocal = {
    ...datos,
    ejecuciones: datos.ejecuciones.slice(-mantener),
  }

  guardarDatos(nuevosDatos)
  log.info(`[HistorialWorkflows] ${eliminadas} ejecuciones antiguas eliminadas`)
  return eliminadas
}

// --- Workflows personalizados ---

/**
 * Obtiene todos los workflows personalizados del usuario.
 */
export function obtenerWorkflowsPersonalizados(): WorkflowDesktop[] {
  const datos = obtenerDatosWorkflows()
  return datos.workflowsPersonalizados
}

/**
 * Guarda un workflow personalizado (crear o actualizar).
 */
export function guardarWorkflowPersonalizado(workflow: WorkflowDesktop): void {
  const datos = obtenerDatosWorkflows()
  const indice = datos.workflowsPersonalizados.findIndex((w) => w.id === workflow.id)

  let nuevosWorkflows: WorkflowDesktop[]
  if (indice >= 0) {
    nuevosWorkflows = datos.workflowsPersonalizados.map((w) =>
      w.id === workflow.id ? workflow : w
    )
  } else {
    nuevosWorkflows = [...datos.workflowsPersonalizados, workflow]
  }

  guardarDatos({ ...datos, workflowsPersonalizados: nuevosWorkflows })
  log.info(`[HistorialWorkflows] Workflow guardado: ${workflow.nombre} (${workflow.id})`)
}

/**
 * Elimina un workflow personalizado por id.
 */
export function eliminarWorkflowPersonalizado(id: string): boolean {
  const datos = obtenerDatosWorkflows()
  const nuevosWorkflows = datos.workflowsPersonalizados.filter((w) => w.id !== id)

  if (nuevosWorkflows.length === datos.workflowsPersonalizados.length) {
    return false
  }

  guardarDatos({ ...datos, workflowsPersonalizados: nuevosWorkflows })
  log.info(`[HistorialWorkflows] Workflow eliminado: ${id}`)
  return true
}

/**
 * Duplica un workflow existente con nuevo id y nombre.
 */
export function duplicarWorkflow(id: string, nuevoId: string): WorkflowDesktop | null {
  const datos = obtenerDatosWorkflows()
  const original = datos.workflowsPersonalizados.find((w) => w.id === id)

  if (!original) return null

  const duplicado: WorkflowDesktop = {
    ...original,
    id: nuevoId,
    nombre: `${original.nombre} (copia)`,
    predefinido: false,
    creadoEn: new Date().toISOString(),
    actualizadoEn: new Date().toISOString(),
  }

  guardarWorkflowPersonalizado(duplicado)
  return duplicado
}

// --- Config SMTP global ---

/**
 * Obtiene la configuracion SMTP global.
 */
export function obtenerConfigSmtp(): ConfigSmtpGlobal | undefined {
  const datos = obtenerDatosWorkflows()
  return datos.configSmtp
}

/**
 * Guarda la configuracion SMTP global.
 */
export function guardarConfigSmtp(config: ConfigSmtpGlobal): void {
  const datos = obtenerDatosWorkflows()
  guardarDatos({ ...datos, configSmtp: config })
  log.info('[HistorialWorkflows] Config SMTP guardada')
}
