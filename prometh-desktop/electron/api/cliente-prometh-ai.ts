/**
 * Cliente HTTP para enviar datos a la API de PROMETH-AI.
 *
 * Las notificaciones AAPP se envían al endpoint /api/certigestor/webhook
 * firmadas con HMAC-SHA256. Los documentos descargados y certificados
 * usan Bearer JWT.
 */
import crypto from 'crypto'
import log from 'electron-log'
import type { ConfigPromethAI } from '../config/prometh-ai.config'

export interface ResultadoEnvio {
  ok: boolean
  mensaje?: string
}

/** Firma un cuerpo con HMAC-SHA256 usando el secreto configurado. */
function firmarPayload(cuerpo: string, webhookSecret: string): string {
  return crypto.createHmac('sha256', webhookSecret).update(cuerpo).digest('hex')
}

/**
 * Envía una notificación AAPP al webhook de PROMETH-AI.
 * Compatible con el endpoint POST /api/certigestor/webhook del servidor.
 */
export async function enviarNotificacionAPromethAI(
  payload: {
    empresa_cif: string
    organismo: string
    tipo: string
    descripcion: string
    fecha_limite?: string
    url_documento?: string
  },
  config: ConfigPromethAI,
): Promise<ResultadoEnvio> {
  const cuerpo = JSON.stringify(payload)
  const firma = firmarPayload(cuerpo, config.webhookSecret)

  try {
    const resp = await fetch(`${config.apiUrl}/api/certigestor/webhook`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CertiGestor-Signature': firma,
      },
      body: cuerpo,
    })
    if (!resp.ok) {
      const texto = await resp.text().catch(() => '')
      log.warn(`[PromethAI] Webhook rechazado ${resp.status}: ${texto}`)
      return { ok: false, mensaje: `HTTP ${resp.status}` }
    }
    return { ok: true }
  } catch (err) {
    log.error('[PromethAI] Error enviando notificación:', err)
    return { ok: false, mensaje: String(err) }
  }
}

/**
 * Envía un documento descargado al endpoint bridge de PROMETH-AI.
 * El servidor lo depositará en el inbox de la empresa indicada.
 */
export async function enviarDocumentoAPromethAI(
  empresaId: number,
  archivo: Buffer,
  nombre: string,
  config: ConfigPromethAI,
): Promise<ResultadoEnvio> {
  try {
    const form = new FormData()
    form.append('archivo', new Blob([archivo]), nombre)

    const resp = await fetch(
      `${config.apiUrl}/api/certigestor/bridge/documento/${empresaId}`,
      {
        method: 'POST',
        headers: { Authorization: `Bearer ${config.token}` },
        body: form,
      },
    )
    if (!resp.ok) {
      log.warn(`[PromethAI] Bridge documento rechazado ${resp.status}`)
      return { ok: false, mensaje: `HTTP ${resp.status}` }
    }
    return { ok: true }
  } catch (err) {
    log.error('[PromethAI] Error enviando documento:', err)
    return { ok: false, mensaje: String(err) }
  }
}

/**
 * Sincroniza los metadatos de un certificado digital con PROMETH-AI.
 */
export async function sincronizarCertificadoConPromethAI(
  cert: {
    empresa_cif: string
    nombre: string
    caducidad: string
    tipo: string
    organismo?: string
  },
  config: ConfigPromethAI,
): Promise<ResultadoEnvio> {
  try {
    const resp = await fetch(`${config.apiUrl}/api/certificados-aap/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${config.token}`,
      },
      body: JSON.stringify(cert),
    })
    if (!resp.ok) {
      log.warn(`[PromethAI] Cert sincronización rechazada ${resp.status}`)
      return { ok: false, mensaje: `HTTP ${resp.status}` }
    }
    return { ok: true }
  } catch (err) {
    log.error('[PromethAI] Error sincronizando certificado:', err)
    return { ok: false, mensaje: String(err) }
  }
}

/** Verifica conectividad con la instancia PROMETH-AI. */
export async function probarConexionPromethAI(apiUrl: string): Promise<boolean> {
  try {
    const resp = await fetch(`${apiUrl}/api/salud`, { signal: AbortSignal.timeout(5000) })
    return resp.ok
  } catch {
    return false
  }
}
