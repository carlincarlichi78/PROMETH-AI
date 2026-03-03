import { useCallback, useEffect, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'

const TOKEN_KEY = 'sfce_token'
const BACKOFF_MS = [3_000, 10_000, 30_000]

export interface UltimaActividad {
  nombreArchivo: string
  timestamp: string // ISO8601
  estado: 'registrado' | 'cuarentena' | 'error'
}

export interface AlertaCuarentena {
  nombreArchivo: string
  motivo: string
}

export interface EstadoWS {
  procesandoAhora: boolean
  ultimaActividad: UltimaActividad | null
  alertaCuarentena: AlertaCuarentena | null
  clearAlertaCuarentena: () => void
}

export function useEmpresaWebSocket(empresaId: number): EstadoWS {
  const qc = useQueryClient()
  const wsRef = useRef<WebSocket | null>(null)
  const intentosRef = useRef(0)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const [procesandoAhora, setProcesandoAhora] = useState(false)
  const [ultimaActividad, setUltimaActividad] = useState<UltimaActividad | null>(null)
  const [alertaCuarentena, setAlertaCuarentena] = useState<AlertaCuarentena | null>(null)

  const clearAlertaCuarentena = useCallback(() => setAlertaCuarentena(null), [])

  useEffect(() => {
    const token = sessionStorage.getItem(TOKEN_KEY)
    if (!token) return

    const protocolo = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const url = `${protocolo}//${host}/api/ws/${empresaId}?token=${token}`

    function conectar() {
      const ws = new WebSocket(url)
      wsRef.current = ws

      const pingTimer = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ tipo: 'ping' }))
        }
      }, 25_000)

      ws.onopen = () => {
        intentosRef.current = 0
      }

      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data as string) as {
            evento: string
            datos: Record<string, unknown>
          }

          if (msg.evento === 'pipeline_progreso') {
            setProcesandoAhora(true)
          }

          if (msg.evento === 'documento_procesado') {
            setProcesandoAhora(false)
            setUltimaActividad({
              nombreArchivo: String(msg.datos.nombre_archivo ?? ''),
              timestamp: msg.datos.timestamp
                ? String(msg.datos.timestamp)
                : new Date().toISOString(),
              estado: (msg.datos.estado as UltimaActividad['estado']) ?? 'registrado',
            })
            void qc.invalidateQueries({ queryKey: ['resumen-empresa', empresaId] })
          }

          if (msg.evento === 'cuarentena_nuevo') {
            setAlertaCuarentena({
              nombreArchivo: String(msg.datos.nombre_archivo ?? ''),
              motivo: String(msg.datos.motivo ?? 'Revision requerida'),
            })
            void qc.invalidateQueries({ queryKey: ['resumen-empresa', empresaId] })
          }
        } catch {
          // JSON malformado — ignorar
        }
      }

      ws.onclose = (ev) => {
        clearInterval(pingTimer)
        // 4401/4403 = auth error, no reconectar
        if (ev.code === 4401 || ev.code === 4403) return
        setProcesandoAhora(false)
        const delay = BACKOFF_MS[Math.min(intentosRef.current, BACKOFF_MS.length - 1)]
        intentosRef.current += 1
        reconnectTimerRef.current = setTimeout(conectar, delay)
      }

      ws.onerror = () => {
        ws.close()
      }
    }

    conectar()

    return () => {
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current)
      wsRef.current?.close()
    }
  }, [empresaId, qc])

  return { procesandoAhora, ultimaActividad, alertaCuarentena, clearAlertaCuarentena }
}
