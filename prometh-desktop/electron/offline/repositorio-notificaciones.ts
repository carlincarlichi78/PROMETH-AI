import { obtenerBd } from './bd-local'
import type { NotificacionCache, FiltrosNotificacionesCache } from './tipos-offline'

export function upsertNotificacion(notif: NotificacionCache): void {
  const db = obtenerBd()
  db.prepare(`
    INSERT INTO notificaciones_cache (
      id, organizacion_id, certificado_id, administracion, tipo, estado,
      contenido, fecha_deteccion, asignado_a, notas, urgencia, categoria,
      id_externo, creado_en, sincronizado_en, pendiente_push
    ) VALUES (
      @id, @organizacionId, @certificadoId, @administracion, @tipo, @estado,
      @contenido, @fechaDeteccion, @asignadoA, @notas, @urgencia, @categoria,
      @idExterno, @creadoEn, @sincronizadoEn, @pendientePush
    ) ON CONFLICT(id) DO UPDATE SET
      estado = excluded.estado,
      contenido = excluded.contenido,
      asignado_a = excluded.asignado_a,
      notas = excluded.notas,
      urgencia = excluded.urgencia,
      categoria = excluded.categoria,
      sincronizado_en = excluded.sincronizado_en,
      pendiente_push = CASE
        WHEN notificaciones_cache.pendiente_push = 1 THEN 1
        ELSE excluded.pendiente_push
      END
  `).run({
    id: notif.id,
    organizacionId: notif.organizacionId,
    certificadoId: notif.certificadoId,
    administracion: notif.administracion,
    tipo: notif.tipo,
    estado: notif.estado,
    contenido: notif.contenido,
    fechaDeteccion: notif.fechaDeteccion,
    asignadoA: notif.asignadoA,
    notas: notif.notas,
    urgencia: notif.urgencia,
    categoria: notif.categoria,
    idExterno: notif.idExterno,
    creadoEn: notif.creadoEn,
    sincronizadoEn: notif.sincronizadoEn,
    pendientePush: notif.pendientePush,
  })
}

export function upsertNotificaciones(notifs: NotificacionCache[]): void {
  const db = obtenerBd()
  const tx = db.transaction(() => {
    for (const notif of notifs) {
      upsertNotificacion(notif)
    }
  })
  tx()
}

export function listarNotificacionesCache(
  organizacionId: string,
  filtros: FiltrosNotificacionesCache = {}
): { datos: NotificacionCache[]; total: number } {
  const db = obtenerBd()
  const { busqueda, estado, urgencia, categoria, pagina = 1, limite = 50 } = filtros
  const offset = (pagina - 1) * limite

  let whereClause = 'WHERE organizacion_id = ?'
  const params: unknown[] = [organizacionId]

  if (estado) {
    whereClause += ' AND estado = ?'
    params.push(estado)
  }
  if (urgencia) {
    whereClause += ' AND urgencia = ?'
    params.push(urgencia)
  }
  if (categoria) {
    whereClause += ' AND categoria = ?'
    params.push(categoria)
  }
  if (busqueda) {
    whereClause += ' AND (administracion LIKE ? OR contenido LIKE ?)'
    const patron = `%${busqueda}%`
    params.push(patron, patron)
  }

  const totalRow = db.prepare(`SELECT COUNT(*) as total FROM notificaciones_cache ${whereClause}`).get(...params) as { total: number }

  const filas = db.prepare(
    `SELECT * FROM notificaciones_cache ${whereClause} ORDER BY fecha_deteccion DESC LIMIT ? OFFSET ?`
  ).all(...params, limite, offset) as Record<string, unknown>[]

  return {
    datos: filas.map(mapearFilaNotificacion),
    total: totalRow.total,
  }
}

export function actualizarNotificacionLocal(
  id: string,
  datos: Partial<Pick<NotificacionCache, 'estado' | 'notas' | 'asignadoA' | 'urgencia' | 'categoria'>>
): void {
  const db = obtenerBd()
  const sets: string[] = []
  const params: unknown[] = []

  if (datos.estado !== undefined) { sets.push('estado = ?'); params.push(datos.estado) }
  if (datos.notas !== undefined) { sets.push('notas = ?'); params.push(datos.notas) }
  if (datos.asignadoA !== undefined) { sets.push('asignado_a = ?'); params.push(datos.asignadoA) }
  if (datos.urgencia !== undefined) { sets.push('urgencia = ?'); params.push(datos.urgencia) }
  if (datos.categoria !== undefined) { sets.push('categoria = ?'); params.push(datos.categoria) }

  if (sets.length === 0) return

  sets.push('pendiente_push = 1')
  params.push(id)

  db.prepare(`UPDATE notificaciones_cache SET ${sets.join(', ')} WHERE id = ?`).run(...params)
}

export function contarNotificacionesCache(organizacionId: string): number {
  const db = obtenerBd()
  const fila = db.prepare('SELECT COUNT(*) as total FROM notificaciones_cache WHERE organizacion_id = ?').get(organizacionId) as { total: number }
  return fila.total
}

export function obtenerPendientesPush(): NotificacionCache[] {
  const db = obtenerBd()
  const filas = db.prepare('SELECT * FROM notificaciones_cache WHERE pendiente_push = 1').all() as Record<string, unknown>[]
  return filas.map(mapearFilaNotificacion)
}

export function marcarSincronizada(id: string): void {
  const db = obtenerBd()
  db.prepare('UPDATE notificaciones_cache SET pendiente_push = 0, sincronizado_en = ? WHERE id = ?')
    .run(new Date().toISOString(), id)
}

function mapearFilaNotificacion(f: Record<string, unknown>): NotificacionCache {
  return {
    id: f.id as string,
    organizacionId: f.organizacion_id as string,
    certificadoId: f.certificado_id as string,
    administracion: f.administracion as string,
    tipo: f.tipo as string | null,
    estado: f.estado as string,
    contenido: f.contenido as string | null,
    fechaDeteccion: f.fecha_deteccion as string,
    asignadoA: f.asignado_a as string | null,
    notas: f.notas as string | null,
    urgencia: f.urgencia as string | null,
    categoria: f.categoria as string | null,
    idExterno: f.id_externo as string | null,
    creadoEn: f.creado_en as string,
    sincronizadoEn: f.sincronizado_en as string,
    pendientePush: f.pendiente_push as number,
  }
}
