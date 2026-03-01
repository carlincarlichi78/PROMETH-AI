import { obtenerBd } from './bd-local'
import type { EtiquetaCache } from './tipos-offline'

export function upsertEtiqueta(etiqueta: EtiquetaCache): void {
  const db = obtenerBd()
  db.prepare(`
    INSERT INTO etiquetas_cache (id, organizacion_id, nombre, color, sincronizado_en)
    VALUES (@id, @organizacionId, @nombre, @color, @sincronizadoEn)
    ON CONFLICT(id) DO UPDATE SET
      nombre = excluded.nombre,
      color = excluded.color,
      sincronizado_en = excluded.sincronizado_en
  `).run({
    id: etiqueta.id,
    organizacionId: etiqueta.organizacionId,
    nombre: etiqueta.nombre,
    color: etiqueta.color,
    sincronizadoEn: etiqueta.sincronizadoEn,
  })
}

export function upsertEtiquetas(etiquetas: EtiquetaCache[]): void {
  const db = obtenerBd()
  const tx = db.transaction(() => {
    for (const etiqueta of etiquetas) {
      upsertEtiqueta(etiqueta)
    }
  })
  tx()
}

export function listarEtiquetasCache(organizacionId: string): EtiquetaCache[] {
  const db = obtenerBd()
  const filas = db.prepare(
    'SELECT * FROM etiquetas_cache WHERE organizacion_id = ? ORDER BY nombre ASC'
  ).all(organizacionId) as Record<string, unknown>[]
  return filas.map(mapearFilaEtiqueta)
}

export function eliminarEtiquetasOrg(organizacionId: string): void {
  const db = obtenerBd()
  db.prepare('DELETE FROM etiquetas_cache WHERE organizacion_id = ?').run(organizacionId)
}

function mapearFilaEtiqueta(f: Record<string, unknown>): EtiquetaCache {
  return {
    id: f.id as string,
    organizacionId: f.organizacion_id as string,
    nombre: f.nombre as string,
    color: f.color as string,
    sincronizadoEn: f.sincronizado_en as string,
  }
}
