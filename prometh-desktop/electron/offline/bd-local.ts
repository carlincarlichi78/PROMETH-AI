import Database from 'better-sqlite3'
import { join } from 'path'
import { app } from 'electron'
import log from 'electron-log'

let instancia: Database.Database | null = null

export function obtenerBd(): Database.Database {
  if (!instancia) {
    const ruta = join(app.getPath('userData'), 'certigestor-offline.db')
    instancia = new Database(ruta)
    instancia.pragma('journal_mode = WAL')
    instancia.pragma('foreign_keys = ON')
    log.info('[BdLocal] SQLite inicializada:', ruta)
  }
  return instancia
}

export function cerrarBd(): void {
  if (instancia) {
    instancia.close()
    instancia = null
    log.info('[BdLocal] SQLite cerrada')
  }
}
