import log from 'electron-log'
import { obtenerBd } from './bd-local'
import { upsertCertificados } from './repositorio-certificados'
import { upsertNotificaciones } from './repositorio-notificaciones'
import { upsertEtiquetas, eliminarEtiquetasOrg } from './repositorio-etiquetas'
import {
  obtenerCambiosPendientes,
  eliminarCambio,
  registrarErrorCambio,
  moverADeadLetter,
} from './cola-cambios'
import type { ResultadoSync, CertificadoCache, NotificacionCache, EtiquetaCache } from './tipos-offline'

const MAX_INTENTOS = 5

// ── Metadata sync ──

function obtenerMeta(clave: string): string | null {
  const db = obtenerBd()
  const fila = db.prepare('SELECT valor FROM metadata_sync WHERE clave = ?').get(clave) as { valor: string } | undefined
  return fila?.valor ?? null
}

function guardarMeta(clave: string, valor: string): void {
  const db = obtenerBd()
  db.prepare(`
    INSERT INTO metadata_sync (clave, valor, actualizado_en)
    VALUES (?, ?, ?)
    ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor, actualizado_en = excluded.actualizado_en
  `).run(clave, valor, new Date().toISOString())
}

export function obtenerUltimaSync(): { certificados: string | null; notificaciones: string | null; etiquetas: string | null } {
  return {
    certificados: obtenerMeta('ultima_sync_certificados'),
    notificaciones: obtenerMeta('ultima_sync_notificaciones'),
    etiquetas: obtenerMeta('ultima_sync_etiquetas'),
  }
}

// ── Pull: cloud → cache local ──

export async function pullDesdeCloud(apiUrl: string, token: string, organizacionId: string): Promise<ResultadoSync> {
  const resultado: ResultadoSync = { certificados: 0, notificaciones: 0, etiquetas: 0, errores: [] }
  const headers = { Authorization: `Bearer ${token}` }
  const ahora = new Date().toISOString()

  // 1. Etiquetas (descarga completa — pocas por org)
  try {
    const resp = await fetch(`${apiUrl}/etiquetas`, { headers })
    if (resp.ok) {
      const datos = await resp.json()
      const lista: unknown[] = datos.datos ?? datos ?? []
      if (Array.isArray(lista) && lista.length > 0) {
        eliminarEtiquetasOrg(organizacionId)
        const etiquetas: EtiquetaCache[] = lista.map((e: Record<string, unknown>) => ({
          id: e.id as string,
          organizacionId: e.organizacionId as string ?? organizacionId,
          nombre: e.nombre as string,
          color: e.color as string,
          sincronizadoEn: ahora,
        }))
        upsertEtiquetas(etiquetas)
        resultado.etiquetas = etiquetas.length
      }
      guardarMeta('ultima_sync_etiquetas', ahora)
    }
  } catch (err) {
    resultado.errores.push(`etiquetas: ${String(err)}`)
  }

  // 2. Certificados (incremental por actualizadoEn, paginado)
  try {
    const desde = obtenerMeta('ultima_sync_certificados')
    let pagina = 1
    let hayMas = true

    while (hayMas) {
      let url = `${apiUrl}/certificados?limite=100&pagina=${pagina}`
      if (desde) url += `&desde=${encodeURIComponent(desde)}`

      const resp = await fetch(url, { headers })
      if (!resp.ok) break

      const datos = await resp.json()
      const lista: unknown[] = datos.datos?.certificados ?? datos.certificados ?? []
      if (!Array.isArray(lista) || lista.length === 0) {
        hayMas = false
        break
      }

      const certs: CertificadoCache[] = lista.map((c: Record<string, unknown>) => ({
        id: c.id as string,
        organizacionId: c.organizacionId as string ?? organizacionId,
        nombreTitular: c.nombreTitular as string ?? '',
        dniCif: c.dniCif as string ?? '',
        numeroSerie: (c.numeroSerie as string) ?? null,
        emisor: (c.emisor as string) ?? null,
        organizacion: (c.organizacion as string) ?? null,
        fechaExpedicion: (c.fechaExpedicion as string) ?? null,
        fechaVencimiento: c.fechaVencimiento as string ?? '',
        activo: c.activo ? 1 : 0,
        creadoEn: c.creadoEn as string ?? ahora,
        actualizadoEn: (c.actualizadoEn as string) ?? null,
        sincronizadoEn: ahora,
        etiquetasJson: JSON.stringify(c.etiquetas ?? []),
      }))
      upsertCertificados(certs)
      resultado.certificados += certs.length

      hayMas = lista.length === 100
      pagina++
    }

    guardarMeta('ultima_sync_certificados', ahora)
  } catch (err) {
    resultado.errores.push(`certificados: ${String(err)}`)
  }

  // 3. Notificaciones (incremental por creadoEn, paginado)
  try {
    const desde = obtenerMeta('ultima_sync_notificaciones')
    let pagina = 1
    let hayMas = true

    while (hayMas) {
      let url = `${apiUrl}/notificaciones?limite=100&pagina=${pagina}`
      if (desde) url += `&desde=${encodeURIComponent(desde)}`

      const resp = await fetch(url, { headers })
      if (!resp.ok) break

      const datos = await resp.json()
      const lista: unknown[] = datos.datos?.notificaciones ?? datos.notificaciones ?? []
      if (!Array.isArray(lista) || lista.length === 0) {
        hayMas = false
        break
      }

      const notifs: NotificacionCache[] = lista.map((n: Record<string, unknown>) => ({
        id: n.id as string,
        organizacionId: n.organizacionId as string ?? organizacionId,
        certificadoId: n.certificadoId as string ?? '',
        administracion: n.administracion as string ?? '',
        tipo: (n.tipo as string) ?? null,
        estado: n.estado as string ?? 'pendiente',
        contenido: (n.contenido as string) ?? null,
        fechaDeteccion: n.fechaDeteccion as string ?? ahora,
        asignadoA: (n.asignadoA as string) ?? null,
        notas: (n.notas as string) ?? null,
        urgencia: (n.urgencia as string) ?? null,
        categoria: (n.categoria as string) ?? null,
        idExterno: (n.idExterno as string) ?? null,
        creadoEn: n.creadoEn as string ?? ahora,
        sincronizadoEn: ahora,
        pendientePush: 0,
      }))
      upsertNotificaciones(notifs)
      resultado.notificaciones += notifs.length

      hayMas = lista.length === 100
      pagina++
    }

    guardarMeta('ultima_sync_notificaciones', ahora)
  } catch (err) {
    resultado.errores.push(`notificaciones: ${String(err)}`)
  }

  if (resultado.errores.length > 0) {
    log.warn('[Sync] Pull con errores:', resultado.errores)
  } else {
    log.info(`[Sync] Pull completado: ${resultado.certificados} certs, ${resultado.notificaciones} notifs, ${resultado.etiquetas} etiquetas`)
  }

  return resultado
}

// ── Push: cola local → cloud ──

export async function pushAlCloud(apiUrl: string, token: string): Promise<{ enviados: number; fallidos: number }> {
  const pendientes = obtenerCambiosPendientes()
  let enviados = 0
  let fallidos = 0
  const headers = { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }

  for (const cambio of pendientes) {
    if (cambio.intentos >= MAX_INTENTOS) {
      log.warn(`[Sync] Moviendo cambio ${cambio.id} a dead-letter tras ${MAX_INTENTOS} intentos`)
      moverADeadLetter(cambio)
      fallidos++
      continue
    }

    try {
      let resp: Response | undefined

      if (cambio.recurso === 'notificacion' && cambio.operacion === 'patch') {
        resp = await fetch(`${apiUrl}/notificaciones/${cambio.recursoId}`, {
          method: 'PATCH',
          headers,
          body: cambio.payloadJson,
        })
      }

      if (!resp) {
        log.warn(`[Sync] Operacion no soportada: ${cambio.recurso}/${cambio.operacion}`)
        eliminarCambio(cambio.id)
        continue
      }

      if (resp.ok || resp.status === 409) {
        eliminarCambio(cambio.id)
        enviados++
      } else {
        registrarErrorCambio(cambio.id, `HTTP ${resp.status}`)
        fallidos++
      }
    } catch (err) {
      registrarErrorCambio(cambio.id, String(err))
      fallidos++
    }
  }

  if (enviados > 0 || fallidos > 0) {
    log.info(`[Sync] Push completado: ${enviados} enviados, ${fallidos} fallidos`)
  }

  return { enviados, fallidos }
}

// ── Sync completa ──

export async function sincronizarCompleto(apiUrl: string, token: string, organizacionId: string): Promise<ResultadoSync> {
  // Push primero (enviar cambios locales antes de descargar)
  await pushAlCloud(apiUrl, token)
  // Pull después
  return pullDesdeCloud(apiUrl, token, organizacionId)
}
