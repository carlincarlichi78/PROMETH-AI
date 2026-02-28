// Hook: useCopilot — acceso al estado y acciones del copiloto IA
// Usa fetch directo (sin React Query) para compatibilidad con streaming futuro

import { useState, useCallback } from 'react'
import type { MensajeCopilot, RespuestaCopilot, ConversacionResumen } from '@/types/copilot'

async function apiFetch<T>(url: string, opts?: RequestInit): Promise<T> {
  const token = localStorage.getItem('sfce_token')
  const res = await fetch(url, {
    ...opts,
    headers: {
      Authorization: token ? `Bearer ${token}` : '',
      'Content-Type': 'application/json',
      ...(opts?.headers ?? {}),
    },
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

export function useCopilot(empresaId: number) {
  const [mensajes, setMensajes] = useState<MensajeCopilot[]>([])
  const [conversacionId, setConversacionId] = useState<number | null>(null)
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [historial, setHistorial] = useState<ConversacionResumen[]>([])

  const cargarHistorial = useCallback(async () => {
    try {
      const convs = await apiFetch<ConversacionResumen[]>(`/api/copilot/conversaciones/${empresaId}`)
      setHistorial(convs)
    } catch {
      // Silencioso — el historial es opcional
    }
  }, [empresaId])

  const enviarMensaje = useCallback(async (texto: string) => {
    const ahora = new Date().toISOString()
    const msgUsuario: MensajeCopilot = { rol: 'user', contenido: texto, timestamp: ahora }
    setMensajes((prev) => [...prev, msgUsuario])
    setCargando(true)
    setError(null)

    try {
      const resp = await apiFetch<RespuestaCopilot>('/api/copilot/chat', {
        method: 'POST',
        body: JSON.stringify({ mensaje: texto, conversacion_id: conversacionId }),
      })

      setConversacionId(resp.conversacion_id)
      const msgIA: MensajeCopilot = {
        rol: 'assistant',
        contenido: resp.respuesta,
        timestamp: new Date().toISOString(),
        datos_enriquecidos: resp.datos_enriquecidos ?? undefined,
      }
      setMensajes((prev) => [...prev, msgIA])
    } catch (e) {
      const msg = (e as Error).message
      setError(msg)
      const msgError: MensajeCopilot = {
        rol: 'assistant',
        contenido: 'Lo siento, hubo un error al procesar tu pregunta.',
        timestamp: new Date().toISOString(),
      }
      setMensajes((prev) => [...prev, msgError])
    } finally {
      setCargando(false)
    }
  }, [conversacionId])

  const enviarFeedback = useCallback(async (mensajeIdx: number, valoracion: 1 | 5) => {
    if (!conversacionId) return
    try {
      await apiFetch('/api/copilot/feedback', {
        method: 'POST',
        body: JSON.stringify({ conversacion_id: conversacionId, mensaje_idx: mensajeIdx, valoracion }),
      })
    } catch {
      // Silencioso — el feedback es no-critico
    }
  }, [conversacionId])

  const nuevaConversacion = useCallback(() => {
    setMensajes([])
    setConversacionId(null)
    setError(null)
  }, [])

  return {
    mensajes,
    conversacionId,
    historial,
    cargando,
    error,
    enviarMensaje,
    enviarFeedback,
    nuevaConversacion,
    cargarHistorial,
  }
}
