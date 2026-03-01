import { obtenerBd } from './bd-local'
import type { CertificadoCache, FiltrosCertificadosCache } from './tipos-offline'

export function upsertCertificado(cert: CertificadoCache): void {
  const db = obtenerBd()
  db.prepare(`
    INSERT INTO certificados_cache (
      id, organizacion_id, nombre_titular, dni_cif, numero_serie, emisor,
      organizacion, fecha_expedicion, fecha_vencimiento, activo,
      creado_en, actualizado_en, sincronizado_en, etiquetas_json
    ) VALUES (
      @id, @organizacionId, @nombreTitular, @dniCif, @numeroSerie, @emisor,
      @organizacion, @fechaExpedicion, @fechaVencimiento, @activo,
      @creadoEn, @actualizadoEn, @sincronizadoEn, @etiquetasJson
    ) ON CONFLICT(id) DO UPDATE SET
      nombre_titular = excluded.nombre_titular,
      dni_cif = excluded.dni_cif,
      numero_serie = excluded.numero_serie,
      emisor = excluded.emisor,
      organizacion = excluded.organizacion,
      fecha_expedicion = excluded.fecha_expedicion,
      fecha_vencimiento = excluded.fecha_vencimiento,
      activo = excluded.activo,
      actualizado_en = excluded.actualizado_en,
      sincronizado_en = excluded.sincronizado_en,
      etiquetas_json = excluded.etiquetas_json
  `).run({
    id: cert.id,
    organizacionId: cert.organizacionId,
    nombreTitular: cert.nombreTitular,
    dniCif: cert.dniCif,
    numeroSerie: cert.numeroSerie,
    emisor: cert.emisor,
    organizacion: cert.organizacion,
    fechaExpedicion: cert.fechaExpedicion,
    fechaVencimiento: cert.fechaVencimiento,
    activo: cert.activo,
    creadoEn: cert.creadoEn,
    actualizadoEn: cert.actualizadoEn,
    sincronizadoEn: cert.sincronizadoEn,
    etiquetasJson: cert.etiquetasJson,
  })
}

export function upsertCertificados(certs: CertificadoCache[]): void {
  const db = obtenerBd()
  const tx = db.transaction(() => {
    for (const cert of certs) {
      upsertCertificado(cert)
    }
  })
  tx()
}

export function listarCertificadosCache(
  organizacionId: string,
  filtros: FiltrosCertificadosCache = {}
): { datos: CertificadoCache[]; total: number } {
  const db = obtenerBd()
  const { busqueda, pagina = 1, limite = 50 } = filtros
  const offset = (pagina - 1) * limite

  let whereClause = 'WHERE organizacion_id = ? AND activo = 1'
  const params: unknown[] = [organizacionId]

  if (busqueda) {
    whereClause += ' AND (nombre_titular LIKE ? OR dni_cif LIKE ? OR emisor LIKE ?)'
    const patron = `%${busqueda}%`
    params.push(patron, patron, patron)
  }

  const totalRow = db.prepare(`SELECT COUNT(*) as total FROM certificados_cache ${whereClause}`).get(...params) as { total: number }

  const filas = db.prepare(
    `SELECT * FROM certificados_cache ${whereClause} ORDER BY fecha_vencimiento ASC LIMIT ? OFFSET ?`
  ).all(...params, limite, offset) as Record<string, unknown>[]

  return {
    datos: filas.map(mapearFilaCertificado),
    total: totalRow.total,
  }
}

export function obtenerCertificadoCache(id: string): CertificadoCache | null {
  const db = obtenerBd()
  const fila = db.prepare('SELECT * FROM certificados_cache WHERE id = ?').get(id) as Record<string, unknown> | undefined
  return fila ? mapearFilaCertificado(fila) : null
}

export function contarCertificadosCache(organizacionId: string): number {
  const db = obtenerBd()
  const fila = db.prepare('SELECT COUNT(*) as total FROM certificados_cache WHERE organizacion_id = ? AND activo = 1').get(organizacionId) as { total: number }
  return fila.total
}

function mapearFilaCertificado(f: Record<string, unknown>): CertificadoCache {
  return {
    id: f.id as string,
    organizacionId: f.organizacion_id as string,
    nombreTitular: f.nombre_titular as string,
    dniCif: f.dni_cif as string,
    numeroSerie: f.numero_serie as string | null,
    emisor: f.emisor as string | null,
    organizacion: f.organizacion as string | null,
    fechaExpedicion: f.fecha_expedicion as string | null,
    fechaVencimiento: f.fecha_vencimiento as string,
    activo: f.activo as number,
    creadoEn: f.creado_en as string,
    actualizadoEn: f.actualizado_en as string | null,
    sincronizadoEn: f.sincronizado_en as string,
    etiquetasJson: f.etiquetas_json as string,
  }
}
