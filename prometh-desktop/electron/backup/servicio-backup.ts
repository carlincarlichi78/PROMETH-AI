import { readFileSync, writeFileSync, existsSync } from 'fs'
import { join } from 'path'
import { app } from 'electron'
import log from 'electron-log'
import { obtenerDatosScheduler } from '../scheduler/persistencia-scheduler'
import { obtenerConfig as obtenerConfigTray } from '../tray/persistencia-tray'
import { obtenerDatosWorkflows } from '../workflows/historial-workflows'
import { obtenerHistorial as obtenerHistorialDocs } from '../scraping/documentales/historial-descargas'
import type {
  SeccionBackup,
  OpcionesExportar,
  DatosBackup,
  ResultadoImportar,
} from './tipos-backup'

/** Nombres de archivos JSON en userData */
const ARCHIVOS_JSON: Partial<Record<SeccionBackup, string>> = {
  config_portales: 'certigestor-config-portales.json',
  config_docs: 'certigestor-config-docs.json',
}

function rutaUserData(nombre: string): string {
  return join(app.getPath('userData'), nombre)
}

function leerJsonLocal(nombre: string): unknown {
  const ruta = rutaUserData(nombre)
  if (!existsSync(ruta)) return null
  try {
    return JSON.parse(readFileSync(ruta, 'utf-8'))
  } catch {
    return null
  }
}

function escribirJsonLocal(nombre: string, datos: unknown): void {
  const ruta = rutaUserData(nombre)
  writeFileSync(ruta, JSON.stringify(datos, null, 2), 'utf-8')
}

/** Recolecta datos de las secciones seleccionadas */
export function exportarConfiguracion(opciones: OpcionesExportar): DatosBackup {
  const secciones: Partial<Record<SeccionBackup, unknown>> = {}

  for (const seccion of opciones.secciones) {
    try {
      switch (seccion) {
        case 'scheduler': {
          const datos = obtenerDatosScheduler()
          // Exportar solo tareas (no historial de ejecuciones)
          secciones.scheduler = { tareas: datos.tareas }
          break
        }
        case 'tray_config': {
          secciones.tray_config = obtenerConfigTray()
          break
        }
        case 'workflows': {
          const datos = obtenerDatosWorkflows()
          // Exportar workflows personalizados y config SMTP (no historial ejecuciones)
          secciones.workflows = {
            workflowsPersonalizados: datos.workflowsPersonalizados,
            configSmtp: datos.configSmtp,
          }
          break
        }
        case 'config_portales': {
          const nombre = ARCHIVOS_JSON.config_portales!
          secciones.config_portales = leerJsonLocal(nombre) ?? {}
          break
        }
        case 'config_docs': {
          const nombre = ARCHIVOS_JSON.config_docs!
          secciones.config_docs = leerJsonLocal(nombre) ?? {}
          break
        }
        case 'historial_docs': {
          secciones.historial_docs = obtenerHistorialDocs()
          break
        }
      }
      log.info(`[Backup] Exportada seccion: ${seccion}`)
    } catch (error) {
      log.error(`[Backup] Error exportando seccion ${seccion}:`, error)
    }
  }

  return {
    version: 1,
    fecha: new Date().toISOString(),
    secciones,
  }
}

/** Importa datos de un backup a los archivos locales */
export function importarConfiguracion(datos: DatosBackup): ResultadoImportar {
  const seccionesImportadas: SeccionBackup[] = []

  for (const [seccion, contenido] of Object.entries(datos.secciones)) {
    if (!contenido) continue

    try {
      switch (seccion as SeccionBackup) {
        case 'scheduler': {
          // Merge: reemplazar tareas del scheduler, mantener ejecuciones existentes
          const datosActuales = obtenerDatosScheduler()
          const backup = contenido as { tareas: unknown[] }
          const datosNuevos = {
            ...datosActuales,
            tareas: backup.tareas ?? datosActuales.tareas,
          }
          escribirJsonLocal('certigestor-scheduler.json', datosNuevos)
          break
        }
        case 'tray_config': {
          // Sobreescribir solo la config, mantener notificaciones existentes
          const datosActuales = leerJsonLocal('certigestor-notificaciones-desktop.json') as Record<string, unknown> | null
          const datosNuevos = {
            ...(datosActuales ?? { notificaciones: [] }),
            config: contenido,
          }
          escribirJsonLocal('certigestor-notificaciones-desktop.json', datosNuevos)
          break
        }
        case 'workflows': {
          // Merge: reemplazar workflows y SMTP, mantener historial ejecuciones
          const datosActuales = obtenerDatosWorkflows()
          const backup = contenido as { workflowsPersonalizados?: unknown[]; configSmtp?: unknown }
          const datosNuevos = {
            ...datosActuales,
            workflowsPersonalizados: backup.workflowsPersonalizados ?? datosActuales.workflowsPersonalizados,
            configSmtp: backup.configSmtp ?? datosActuales.configSmtp,
          }
          escribirJsonLocal('certigestor-workflows-desktop.json', datosNuevos)
          break
        }
        case 'config_portales': {
          escribirJsonLocal(ARCHIVOS_JSON.config_portales!, contenido)
          break
        }
        case 'config_docs': {
          escribirJsonLocal(ARCHIVOS_JSON.config_docs!, contenido)
          break
        }
        case 'historial_docs': {
          escribirJsonLocal('certigestor-historial-docs.json', contenido)
          break
        }
      }
      seccionesImportadas.push(seccion as SeccionBackup)
      log.info(`[Backup] Importada seccion: ${seccion}`)
    } catch (error) {
      log.error(`[Backup] Error importando seccion ${seccion}:`, error)
    }
  }

  return {
    exito: seccionesImportadas.length > 0,
    seccionesImportadas,
  }
}
