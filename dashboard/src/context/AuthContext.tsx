import { createContext, useContext, useEffect, useState, useCallback, useRef, type ReactNode } from 'react'
import type { Usuario, LoginResponse } from '../types'

interface AuthContextType {
  token: string | null
  usuario: Usuario | null
  login: (email: string, password: string) => Promise<void>
  loginConToken: (accessToken: string) => Promise<void>
  logout: () => void
  cargando: boolean
}

const AuthContext = createContext<AuthContextType | null>(null)

const CLAVE_TOKEN = 'sfce_token'
const IDLE_MS = 30 * 60 * 1000 // 30 minutos de inactividad

/** Proveedor de autenticacion — gestiona JWT en sessionStorage + idle timer */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => sessionStorage.getItem(CLAVE_TOKEN))
  const [usuario, setUsuario] = useState<Usuario | null>(null)
  const [cargando, setCargando] = useState(true)
  const idleTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const limpiarSesion = useCallback(() => {
    sessionStorage.removeItem(CLAVE_TOKEN)
    setToken(null)
    setUsuario(null)
    if (idleTimer.current) clearTimeout(idleTimer.current)
  }, [])

  const reiniciarIdleTimer = useCallback(() => {
    if (idleTimer.current) clearTimeout(idleTimer.current)
    idleTimer.current = setTimeout(limpiarSesion, IDLE_MS)
  }, [limpiarSesion])

  // Registrar eventos de actividad del usuario
  useEffect(() => {
    if (!token) return
    const eventos: string[] = ['mousedown', 'keydown', 'touchstart', 'scroll']
    const handler = () => reiniciarIdleTimer()
    eventos.forEach(e => document.addEventListener(e, handler, { passive: true }))
    reiniciarIdleTimer()
    return () => {
      eventos.forEach(e => document.removeEventListener(e, handler))
      if (idleTimer.current) clearTimeout(idleTimer.current)
    }
  }, [token, reiniciarIdleTimer])

  const validarToken = useCallback(async (tokenActual: string) => {
    try {
      const respuesta = await fetch('/api/auth/me', {
        headers: { Authorization: `Bearer ${tokenActual}` },
      })
      if (!respuesta.ok) throw new Error('Token invalido')
      const datos: Usuario = await respuesta.json()
      setUsuario(datos)
    } catch {
      limpiarSesion()
    }
  }, [limpiarSesion])

  useEffect(() => {
    if (token) {
      validarToken(token).finally(() => setCargando(false))
    } else {
      setCargando(false)
    }
  }, [token, validarToken])

  const login = useCallback(async (email: string, password: string) => {
    const respuesta = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })
    if (!respuesta.ok) {
      const error = await respuesta.json().catch(() => ({ detail: 'Error de autenticacion' }))
      throw new Error(error.detail ?? 'Credenciales incorrectas')
    }
    const datos: LoginResponse = await respuesta.json()
    const nuevoToken = datos.access_token
    sessionStorage.setItem(CLAVE_TOKEN, nuevoToken)
    setToken(nuevoToken)
    await validarToken(nuevoToken)
  }, [validarToken])

  const loginConToken = useCallback(async (accessToken: string) => {
    sessionStorage.setItem(CLAVE_TOKEN, accessToken)
    setToken(accessToken)
    await validarToken(accessToken)
  }, [validarToken])

  const logout = useCallback(() => limpiarSesion(), [limpiarSesion])

  return (
    <AuthContext.Provider value={{ token, usuario, login, loginConToken, logout, cargando }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextType {
  const contexto = useContext(AuthContext)
  if (!contexto) throw new Error('useAuth debe usarse dentro de AuthProvider')
  return contexto
}
