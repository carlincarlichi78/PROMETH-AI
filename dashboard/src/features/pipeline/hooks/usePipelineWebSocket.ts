// dashboard/src/features/pipeline/hooks/usePipelineWebSocket.ts
import { useEffect, useRef, useState, useCallback } from 'react'
import { useAuth } from '@/context/AuthContext'

// Tipos de evento que emite el backend
export type EventoPipeline =
  | 'pipeline_progreso'
  | 'documento_procesado'
  | 'cuarentena_nuevo'
  | 'cuarentena_resuelta'
  | 'watcher_nuevo_pdf'
  | 'error'

export interface EventoWS {
  id: string            // generado en frontend para React keys
  evento: EventoPipeline
  datos: {
    documento_id?: number
    empresa_id?: number
    tipo_doc?: string   // FC, FV, NC, SUM, IMP, NOM, BAN...
    estado?: string
    fase_actual?: string
    factura_id_fs?: number
    motivo?: string
    nombre_archivo?: string
  }
  timestamp: string
  recibido_en: number   // Date.now() para TTL
}

export interface ParticulaActiva {
  id: string
  tipo_doc: string
  empresa_id: number
  nodo_origen: string  // 'inbox' | 'ocr' | 'validacion' | 'fs' | 'asiento'
  nodo_destino: string
  iniciado_en: number
  fuente: 'correo' | 'manual' | 'watcher' | 'pipeline'
}

interface Estado {
  eventos: EventoWS[]
  particulas: ParticulaActiva[]
  conectado: boolean
  contadores_fuente: { correo: number; manual: number; watcher: number }
}

const MAX_EVENTOS = 15
const TTL_EVENTO_MS = 30_000   // 30s
const FASES_A_NODO: Record<string, string> = {
  intake: 'ocr',
  pre_validacion: 'validacion',
  registro: 'fs',
  asientos: 'asiento',
  correccion: 'asiento',
  validacion_cruzada: 'asiento',
  salidas: 'asiento',
}

function generarId() {
  return Math.random().toString(36).slice(2, 9)
}

export function usePipelineWebSocket(empresaId?: number) {
  const { token } = useAuth()
  const wsRef = useRef<WebSocket | null>(null)
  const [estado, setEstado] = useState<Estado>({
    eventos: [],
    particulas: [],
    conectado: false,
    contadores_fuente: { correo: 0, manual: 0, watcher: 0 },
  })

  const limpiarEventosViejos = useCallback(() => {
    const ahora = Date.now()
    setEstado(prev => ({
      ...prev,
      eventos: prev.eventos.filter(e => ahora - e.recibido_en < TTL_EVENTO_MS),
    }))
  }, [])

  const procesarMensaje = useCallback((raw: string) => {
    let msg: { evento: EventoPipeline; datos: EventoWS['datos']; timestamp: string }
    try { msg = JSON.parse(raw) } catch { return }

    const evento: EventoWS = {
      id: generarId(),
      evento: msg.evento,
      datos: msg.datos,
      timestamp: msg.timestamp,
      recibido_en: Date.now(),
    }

    setEstado(prev => {
      const nuevosEventos = [evento, ...prev.eventos].slice(0, MAX_EVENTOS)
      let nuevasParticulas = [...prev.particulas]

      // Crear partícula si el evento indica movimiento entre nodos
      if (msg.evento === 'pipeline_progreso' && msg.datos.fase_actual) {
        const nodoActual = FASES_A_NODO[msg.datos.fase_actual] ?? 'inbox'
        const nodoDestino = (() => {
          const fases = Object.keys(FASES_A_NODO)
          const idx = fases.indexOf(msg.datos.fase_actual!)
          if (idx >= 0 && idx < fases.length - 1) return FASES_A_NODO[fases[idx + 1]!]
          return 'done'
        })()
        nuevasParticulas.push({
          id: generarId(),
          tipo_doc: msg.datos.tipo_doc ?? 'FV',
          empresa_id: msg.datos.empresa_id ?? 0,
          nodo_origen: nodoActual,
          nodo_destino: nodoDestino ?? 'done',
          iniciado_en: Date.now(),
          fuente: 'pipeline',
        })
      }

      if (msg.evento === 'documento_procesado') {
        nuevasParticulas.push({
          id: generarId(),
          tipo_doc: msg.datos.tipo_doc ?? 'FV',
          empresa_id: msg.datos.empresa_id ?? 0,
          nodo_origen: 'asiento',
          nodo_destino: 'done',
          iniciado_en: Date.now(),
          fuente: 'pipeline',
        })
      }

      if (msg.evento === 'watcher_nuevo_pdf') {
        const fuente = (msg.datos as { fuente?: string }).fuente as ParticulaActiva['fuente'] ?? 'manual'
        nuevasParticulas.push({
          id: generarId(),
          tipo_doc: msg.datos.tipo_doc ?? 'FV',
          empresa_id: msg.datos.empresa_id ?? 0,
          nodo_origen: 'inbox',
          nodo_destino: 'ocr',
          iniciado_en: Date.now(),
          fuente,
        })
        // Acumular contador de fuente
        const nuevosContadores = { ...prev.contadores_fuente }
        if (fuente === 'correo') nuevosContadores.correo++
        else if (fuente === 'watcher') nuevosContadores.watcher++
        else nuevosContadores.manual++

        // Limpiar partículas > 4s (tiempo de animación)
        const ahora2 = Date.now()
        nuevasParticulas = nuevasParticulas.filter(p => ahora2 - p.iniciado_en < 4000)

        return { ...prev, eventos: nuevosEventos, particulas: nuevasParticulas, contadores_fuente: nuevosContadores }
      }

      // Limpiar partículas > 4s (tiempo de animación)
      const ahora = Date.now()
      nuevasParticulas = nuevasParticulas.filter(p => ahora - p.iniciado_en < 4000)

      return { ...prev, eventos: nuevosEventos, particulas: nuevasParticulas }
    })
  }, [])

  useEffect(() => {
    if (!token) return

    // En producción usamos same-origin para que nginx proxy /api/ws correctamente.
    // VITE_API_URL solo aplica en dev con servidor externo explícito.
    const apiBase = import.meta.env.VITE_API_URL
    const wsBase = apiBase
      ? apiBase.replace(/^http/, 'ws')
      : `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}`
    const url = empresaId
      ? `${wsBase}/api/ws/${empresaId}?token=${token}`
      : `${wsBase}/api/ws?token=${token}`

    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => setEstado(prev => ({ ...prev, conectado: true }))
    ws.onclose = () => setEstado(prev => ({ ...prev, conectado: false }))
    ws.onmessage = e => procesarMensaje(e.data)

    // Limpiar eventos viejos cada 10s
    const intervalo = setInterval(limpiarEventosViejos, 10_000)

    return () => {
      ws.close()
      clearInterval(intervalo)
    }
  }, [token, empresaId, procesarMensaje, limpiarEventosViejos])

  const eliminarParticula = useCallback((id: string) => {
    setEstado(prev => ({
      ...prev,
      particulas: prev.particulas.filter(p => p.id !== id),
    }))
  }, [])

  return {
    eventos: estado.eventos,
    particulas: estado.particulas,
    conectado: estado.conectado,
    contadores_fuente: estado.contadores_fuente,
    eliminarParticula,
  }
}
