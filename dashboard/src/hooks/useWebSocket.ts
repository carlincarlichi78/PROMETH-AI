import { useEffect, useRef, useState, useCallback } from 'react'
import { useAuth } from '../context/AuthContext'
import type { EventoWS } from '../types'

/** Tiempo base para reconexion (ms) */
const RECONEXION_BASE_MS = 1000
/** Maximo tiempo entre intentos de reconexion (ms) */
const RECONEXION_MAX_MS = 30000

interface UseWebSocketResult {
  conectado: boolean
  ultimoEvento: EventoWS | null
  addEventListener: (tipo: string, handler: (datos: unknown) => void) => () => void
}

/**
 * Hook WebSocket con auto-reconexion y backoff exponencial.
 * Se conecta a /api/ws/{canal} con token JWT como query param.
 */
export function useWebSocket(canal?: string): UseWebSocketResult {
  const { token } = useAuth()
  const [conectado, setConectado] = useState(false)
  const [ultimoEvento, setUltimoEvento] = useState<EventoWS | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const listenersRef = useRef<Map<string, Set<(datos: unknown) => void>>>(new Map())
  const intentosRef = useRef(0)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  /** Registra un listener para un tipo de evento. Retorna funcion de limpieza. */
  const addEventListener = useCallback((tipo: string, handler: (datos: unknown) => void) => {
    if (!listenersRef.current.has(tipo)) {
      listenersRef.current.set(tipo, new Set())
    }
    listenersRef.current.get(tipo)!.add(handler)

    // Retornar funcion para desregistrar
    return () => {
      const conjunto = listenersRef.current.get(tipo)
      if (conjunto) {
        conjunto.delete(handler)
        if (conjunto.size === 0) {
          listenersRef.current.delete(tipo)
        }
      }
    }
  }, [])

  /** Notifica a los listeners registrados */
  const notificarListeners = useCallback((evento: EventoWS) => {
    const conjunto = listenersRef.current.get(evento.tipo)
    if (conjunto) {
      conjunto.forEach((handler) => handler(evento.datos))
    }
    // Notificar tambien a listeners globales ('*')
    const globales = listenersRef.current.get('*')
    if (globales) {
      globales.forEach((handler) => handler(evento))
    }
  }, [])

  useEffect(() => {
    if (!token || !canal) return

    const conectar = () => {
      // Limpiar conexion previa
      if (wsRef.current) {
        wsRef.current.close()
      }

      const protocolo = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const url = `${protocolo}//${window.location.host}/api/ws/${canal}?token=${encodeURIComponent(token)}`
      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => {
        setConectado(true)
        intentosRef.current = 0 // Resetear intentos al conectar
      }

      ws.onmessage = (evento) => {
        try {
          const datos: EventoWS = JSON.parse(evento.data)
          setUltimoEvento(datos)
          notificarListeners(datos)
        } catch {
          // Mensaje no parseable — ignorar
        }
      }

      ws.onclose = () => {
        setConectado(false)
        wsRef.current = null

        // Reconexion con backoff exponencial
        const intentos = intentosRef.current
        const delay = Math.min(RECONEXION_BASE_MS * Math.pow(2, intentos), RECONEXION_MAX_MS)
        intentosRef.current = intentos + 1

        timerRef.current = setTimeout(conectar, delay)
      }

      ws.onerror = () => {
        ws.close()
      }
    }

    conectar()

    // Limpieza al desmontar
    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current)
        timerRef.current = null
      }
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [token, canal, notificarListeners])

  return { conectado, ultimoEvento, addEventListener }
}
