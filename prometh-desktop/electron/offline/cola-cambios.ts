import { obtenerBd } from './bd-local'
import log from 'electron-log'
import type { CambioPendiente } from './tipos-offline'

export function encolarCambio(
  recurso: string,
  recursoId: string,
  operacion: string,
  payload: unknown
): void {
  const db = obtenerBd()
  db.prepare(`
    INSERT INTO cola_cambios (recurso, recurso_id, operacion, payload_json, creado_en)
    VALUES (?, ?, ?, ?, ?)
  `).run(recurso, recursoId, operacion, JSON.stringify(payload), new Date().toISOString())
  log.info(`[Cola] Encolado: ${recurso}/${recursoId} op=${operacion}`)
}

export function obtenerCambiosPendientes(): CambioPendiente[] {
  const db = obtenerBd()
  const filas = db.prepare('SELECT * FROM cola_cambios ORDER BY creado_en ASC').all()
  return filas.map((f: Record<string, unknown>) => ({
    id: f.id as number,
    recurso: f.recurso as string,
    recursoId: f.recurso_id as string,
    operacion: f.operacion as string,
    payloadJson: f.payload_json as string,
    intentos: f.intentos as number,
    ultimoIntento: f.ultimo_intento as string | null,
    creadoEn: f.creado_en as string,
    errorUltimo: f.error_ultimo as string | null,
  }))
}

export function eliminarCambio(id: number): void {
  const db = obtenerBd()
  db.prepare('DELETE FROM cola_cambios WHERE id = ?').run(id)
}

export function registrarErrorCambio(id: number, error: string): void {
  const db = obtenerBd()
  db.prepare(`
    UPDATE cola_cambios SET intentos = intentos + 1, ultimo_intento = ?, error_ultimo = ? WHERE id = ?
  `).run(new Date().toISOString(), error, id)
}

export function contarPendientes(): number {
  const db = obtenerBd()
  const fila = db.prepare('SELECT COUNT(*) as total FROM cola_cambios').get() as { total: number }
  return fila.total
}

export function limpiarCola(): void {
  const db = obtenerBd()
  db.prepare('DELETE FROM cola_cambios').run()
  log.info('[Cola] Cola vaciada')
}

/** Mueve un cambio a dead-letter en vez de eliminarlo silenciosamente */
export function moverADeadLetter(cambio: CambioPendiente): void {
  const db = obtenerBd()
  db.prepare(`
    INSERT OR IGNORE INTO dead_letter_cambios (id, recurso, recurso_id, operacion, payload_json, intentos, error_ultimo, creado_en, descartado_en)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
  `).run(
    cambio.id,
    cambio.recurso,
    cambio.recursoId,
    cambio.operacion,
    cambio.payloadJson,
    cambio.intentos,
    cambio.errorUltimo,
    cambio.creadoEn,
    new Date().toISOString(),
  )
  eliminarCambio(cambio.id)
  log.warn(`[Cola] Cambio ${cambio.id} movido a dead-letter tras ${cambio.intentos} intentos`)
}

/** Obtiene cambios descartados en dead-letter */
export function obtenerDeadLetter(): CambioPendiente[] {
  const db = obtenerBd()
  const filas = db.prepare('SELECT * FROM dead_letter_cambios ORDER BY descartado_en DESC').all()
  return filas.map((f: Record<string, unknown>) => ({
    id: f.id as number,
    recurso: f.recurso as string,
    recursoId: f.recurso_id as string,
    operacion: f.operacion as string,
    payloadJson: f.payload_json as string,
    intentos: f.intentos as number,
    ultimoIntento: null,
    creadoEn: f.creado_en as string,
    errorUltimo: f.error_ultimo as string | null,
  }))
}

/** Cuenta cambios en dead-letter */
export function contarDeadLetter(): number {
  const db = obtenerBd()
  const fila = db.prepare('SELECT COUNT(*) as total FROM dead_letter_cambios').get() as { total: number }
  return fila.total
}
