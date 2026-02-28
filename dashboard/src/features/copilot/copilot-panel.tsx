// Copiloto IA — Panel principal de chat
import { useState, useEffect, useRef } from 'react'
import type { MensajeCopilot, RespuestaCopilot, ConversacionResumen } from '@/types/copilot'
import { CopilotMessage } from './copilot-message'
import { CopilotInput } from './copilot-input'

interface Props {
  empresaId: number
}

async function apiFetch<T>(url: string, opts?: RequestInit): Promise<T> {
  const token = sessionStorage.getItem('sfce_token')
  const res = await fetch(url, {
    ...opts,
    headers: { Authorization: token ? `Bearer ${token}` : '', 'Content-Type': 'application/json', ...(opts?.headers ?? {}) },
  })
  if (!res.ok) throw new Error(`${res.status}`)
  return res.json()
}

export default function CopilotPanel({ empresaId }: Props) {
  const [mensajes, setMensajes] = useState<MensajeCopilot[]>([])
  const [conversacionId, setConversacionId] = useState<number | null>(null)
  const [historial, setHistorial] = useState<ConversacionResumen[]>([])
  const [cargando, setCargando] = useState(false)
  const [mostrarHistorial, setMostrarHistorial] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  // Cargar historial de conversaciones
  useEffect(() => {
    apiFetch<ConversacionResumen[]>(`/api/copilot/conversaciones/${empresaId}`)
      .then(setHistorial)
      .catch(() => {})
  }, [empresaId])

  // Auto-scroll al ultimo mensaje
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [mensajes])

  const enviarMensaje = async (texto: string) => {
    const ahora = new Date().toISOString()
    const msgUsuario: MensajeCopilot = { rol: 'user', contenido: texto, timestamp: ahora }
    setMensajes((prev) => [...prev, msgUsuario])
    setCargando(true)

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

      // Actualizar historial local
      setHistorial((prev) => {
        const existe = prev.find((c) => c.id === resp.conversacion_id)
        if (existe) return prev.map((c) => c.id === resp.conversacion_id ? { ...c, num_mensajes: c.num_mensajes + 2 } : c)
        return [{ id: resp.conversacion_id, titulo: texto.slice(0, 50), num_mensajes: 2, fecha_creacion: ahora, fecha_actualizacion: ahora }, ...prev]
      })
    } catch (e) {
      const msgError: MensajeCopilot = {
        rol: 'assistant',
        contenido: 'Lo siento, hubo un error al procesar tu pregunta. Por favor intenta de nuevo.',
        timestamp: new Date().toISOString(),
      }
      setMensajes((prev) => [...prev, msgError])
    } finally {
      setCargando(false)
    }
  }

  const enviarFeedback = async (mensajeIdx: number, valoracion: 1 | 5) => {
    if (!conversacionId) return
    try {
      await apiFetch('/api/copilot/feedback', {
        method: 'POST',
        body: JSON.stringify({ conversacion_id: conversacionId, mensaje_idx: mensajeIdx, valoracion }),
      })
    } catch {
      // silencioso
    }
  }

  const nuevaConversacion = () => {
    setMensajes([])
    setConversacionId(null)
    setMostrarHistorial(false)
  }

  const cargarConversacion = async (id: number) => {
    try {
      await apiFetch<{ mensajes: MensajeCopilot[] }>(`/api/copilot/conversaciones/${empresaId}`)
      // Por ahora mostramos el historial desde la lista — en produccion se cargan los mensajes del ID
      setConversacionId(id)
      setMostrarHistorial(false)
    } catch {
      //
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: '#fff' }}>
      {/* Header */}
      <div style={{ padding: '14px 16px', borderBottom: '1px solid #e5e7eb', display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{ width: 32, height: 32, borderRadius: '50%', background: '#1e293b', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <span style={{ color: '#fff', fontSize: 16 }}>✦</span>
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 700, fontSize: 14, color: '#1e293b' }}>Copiloto Contable</div>
          <div style={{ fontSize: 11, color: '#9ca3af' }}>Asistente IA especializado</div>
        </div>
        <button onClick={() => setMostrarHistorial(!mostrarHistorial)} title="Historial"
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#6b7280', fontSize: 18, padding: '2px 6px' }}>
          ☰
        </button>
        <button onClick={nuevaConversacion} title="Nueva conversacion"
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#6b7280', fontSize: 18, padding: '2px 6px' }}>
          ✎
        </button>
      </div>

      {/* Historial lateral */}
      {mostrarHistorial && (
        <div style={{ borderBottom: '1px solid #e5e7eb', background: '#f8fafc', maxHeight: 200, overflowY: 'auto' }}>
          <div style={{ padding: '8px 12px', fontSize: 12, fontWeight: 600, color: '#6b7280', textTransform: 'uppercase' }}>Conversaciones</div>
          {historial.length === 0 && <p style={{ padding: '8px 16px', color: '#9ca3af', fontSize: 13 }}>Sin conversaciones previas</p>}
          {historial.map((c) => (
            <button key={c.id} onClick={() => cargarConversacion(c.id)}
              style={{ width: '100%', textAlign: 'left', padding: '8px 16px', background: conversacionId === c.id ? '#e0e7ff' : 'none', border: 'none', cursor: 'pointer', borderBottom: '1px solid #e5e7eb' }}>
              <div style={{ fontSize: 13, color: '#1e293b', fontWeight: 500 }}>{c.titulo}</div>
              <div style={{ fontSize: 11, color: '#9ca3af' }}>{c.num_mensajes} mensajes</div>
            </button>
          ))}
        </div>
      )}

      {/* Area de mensajes */}
      <div ref={scrollRef} style={{ flex: 1, overflowY: 'auto', padding: '16px' }}>
        {mensajes.length === 0 && (
          <div style={{ textAlign: 'center', color: '#9ca3af', paddingTop: 40 }}>
            <div style={{ fontSize: 32, marginBottom: 12 }}>✦</div>
            <div style={{ fontSize: 15, fontWeight: 600, color: '#374151', marginBottom: 8 }}>Copiloto Contable</div>
            <div style={{ fontSize: 13, lineHeight: 1.6 }}>
              Preguntame sobre ratios, impuestos,<br />facturas o cualquier duda contable.
            </div>
            {/* Sugerencias */}
            <div style={{ marginTop: 20, display: 'flex', flexDirection: 'column', gap: 6 }}>
              {['¿Cuales son los ratios de liquidez?', 'Estado del modelo 303', 'Facturas pendientes de pago'].map((sugerencia) => (
                <button key={sugerencia} onClick={() => enviarMensaje(sugerencia)}
                  style={{ padding: '8px 14px', border: '1px solid #e5e7eb', borderRadius: 8, background: '#fff', cursor: 'pointer', fontSize: 13, color: '#374151', textAlign: 'left' }}>
                  {sugerencia}
                </button>
              ))}
            </div>
          </div>
        )}

        {mensajes.map((msg, i) => (
          <CopilotMessage
            key={i}
            mensaje={msg}
            onFeedback={msg.rol === 'assistant' ? (v) => enviarFeedback(i, v) : undefined}
          />
        ))}

        {cargando && (
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', padding: '8px 0' }}>
            <div style={{ width: 28, height: 28, borderRadius: '50%', background: '#f1f5f9', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, fontWeight: 700, color: '#475569' }}>AI</div>
            <div style={{ padding: '10px 14px', background: '#f8fafc', border: '1px solid #e5e7eb', borderRadius: '4px 16px 16px 16px' }}>
              <div style={{ display: 'flex', gap: 4 }}>
                {[0, 1, 2].map((i) => (
                  <div key={i} style={{ width: 6, height: 6, borderRadius: '50%', background: '#94a3b8' }} />
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <CopilotInput onEnviar={enviarMensaje} cargando={cargando} />
    </div>
  )
}
