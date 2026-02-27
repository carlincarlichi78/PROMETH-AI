import { useCallback } from 'react'
import { useAuth } from '../context/AuthContext'

interface OpcionesFetch {
  method?: string
  body?: unknown
  headers?: Record<string, string>
}

/**
 * Hook que envuelve fetch anadiendo el header Authorization automaticamente.
 * Redirige a /login si recibe 401.
 */
export function useApi() {
  const { token, logout } = useAuth()

  const fetchConAuth = useCallback(
    async <T>(ruta: string, opciones: OpcionesFetch = {}): Promise<T> => {
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        ...opciones.headers,
      }

      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }

      const respuesta = await fetch(ruta, {
        method: opciones.method ?? 'GET',
        headers,
        body: opciones.body ? JSON.stringify(opciones.body) : undefined,
      })

      // Token expirado o invalido
      if (respuesta.status === 401) {
        logout()
        throw new Error('Sesion expirada')
      }

      if (!respuesta.ok) {
        const error = await respuesta.json().catch(() => ({ detail: 'Error del servidor' }))
        throw new Error(error.detail ?? `Error HTTP ${respuesta.status}`)
      }

      return respuesta.json() as Promise<T>
    },
    [token, logout]
  )

  return { fetchConAuth }
}
