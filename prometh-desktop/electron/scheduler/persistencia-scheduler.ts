import { existsSync, readFileSync, writeFileSync, mkdirSync, renameSync } from 'fs'
import { join, dirname } from 'path'
import { app } from 'electron'
import log from 'electron-log'
import type {
  DatosScheduler,
  TareaProgramada,
  EjecucionScheduler,
} from './tipos-scheduler'

const NOMBRE_ARCHIVO = 'certigestor-scheduler.json'

function obtenerRutaArchivo(): string {
  return join(app.getPath('userData'), NOMBRE_ARCHIVO)
}

function crearDatosVacios(): DatosScheduler {
  return {
    tareas: [],
    ejecuciones: [],
  }
}

export function obtenerDatosScheduler(): DatosScheduler {
  const ruta = obtenerRutaArchivo()

  if (!existsSync(ruta)) {
    return crearDatosVacios()
  }

  try {
    const contenido = readFileSync(ruta, 'utf-8')
    const datos: DatosScheduler = JSON.parse(contenido)
    return datos
  } catch (error) {
    log.warn('[Scheduler] Error leyendo datos, creando nuevos:', error)
    return crearDatosVacios()
  }
}

function guardarDatos(datos: DatosScheduler): void {
  const ruta = obtenerRutaArchivo()
  const directorio = dirname(ruta)

  if (!existsSync(directorio)) {
    mkdirSync(directorio, { recursive: true })
  }

  // Escritura atomica: escribir a temp + rename para evitar corrupcion
  const rutaTmp = `${ruta}.tmp`
  writeFileSync(rutaTmp, JSON.stringify(datos, null, 2), 'utf-8')
  renameSync(rutaTmp, ruta)
}

// --- Tareas ---

export function obtenerTareas(): TareaProgramada[] {
  return obtenerDatosScheduler().tareas
}

export function obtenerTarea(id: string): TareaProgramada | null {
  const datos = obtenerDatosScheduler()
  return datos.tareas.find((t) => t.id === id) ?? null
}

export function guardarTarea(tarea: TareaProgramada): void {
  const datos = obtenerDatosScheduler()
  const indice = datos.tareas.findIndex((t) => t.id === tarea.id)

  let nuevasTareas: TareaProgramada[]
  if (indice >= 0) {
    nuevasTareas = datos.tareas.map((t) =>
      t.id === tarea.id ? tarea : t
    )
  } else {
    nuevasTareas = [...datos.tareas, tarea]
  }

  guardarDatos({ ...datos, tareas: nuevasTareas })
  log.info(`[Scheduler] Tarea guardada: ${tarea.nombre} (${tarea.id})`)
}

export function eliminarTarea(id: string): boolean {
  const datos = obtenerDatosScheduler()
  const nuevasTareas = datos.tareas.filter((t) => t.id !== id)

  if (nuevasTareas.length === datos.tareas.length) {
    return false
  }

  guardarDatos({ ...datos, tareas: nuevasTareas })
  log.info(`[Scheduler] Tarea eliminada: ${id}`)
  return true
}

export function toggleTarea(id: string): { activa: boolean } | null {
  const datos = obtenerDatosScheduler()
  const tarea = datos.tareas.find((t) => t.id === id)

  if (!tarea) return null

  const nuevasTareas = datos.tareas.map((t) =>
    t.id === id ? { ...t, activa: !t.activa, actualizadoEn: new Date().toISOString() } : t
  )

  guardarDatos({ ...datos, tareas: nuevasTareas })
  log.info(`[Scheduler] Tarea ${!tarea.activa ? 'activada' : 'desactivada'}: ${id}`)
  return { activa: !tarea.activa }
}

// --- Ejecuciones ---

export function registrarEjecucion(ejecucion: EjecucionScheduler): void {
  const datos = obtenerDatosScheduler()

  // Actualizar ultima ejecucion y resultado en la tarea
  const nuevasTareas = datos.tareas.map((t) =>
    t.id === ejecucion.tareaId
      ? { ...t, ultimaEjecucion: ejecucion.ejecutadoEn, ultimoResultado: ejecucion.resultado }
      : t
  )

  guardarDatos({
    ...datos,
    tareas: nuevasTareas,
    ejecuciones: [...datos.ejecuciones, ejecucion],
  })
  log.info(`[Scheduler] Ejecucion registrada: ${ejecucion.id} (${ejecucion.resultado})`)
}

export function obtenerEjecuciones(limite: number = 50): EjecucionScheduler[] {
  const datos = obtenerDatosScheduler()
  return datos.ejecuciones.slice(-limite).reverse()
}

export function limpiarEjecucionesAntiguas(mantener: number = 100): number {
  const datos = obtenerDatosScheduler()
  const total = datos.ejecuciones.length

  if (total <= mantener) return 0

  const eliminadas = total - mantener
  guardarDatos({
    ...datos,
    ejecuciones: datos.ejecuciones.slice(-mantener),
  })

  log.info(`[Scheduler] ${eliminadas} ejecuciones antiguas eliminadas`)
  return eliminadas
}
