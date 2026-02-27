import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from 'react'
import type { Usuario, LoginResponse } from '../types'

interface AuthContextType {
  token: string | null
  usuario: Usuario | null
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  cargando: boolean
}

const AuthContext = createContext<AuthContextType | null>(null)

const CLAVE_TOKEN = 'sfce_token'

/** Proveedor de autenticacion — gestiona JWT y estado del usuario */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(CLAVE_TOKEN))
  const [usuario, setUsuario] = useState<Usuario | null>(null)
  const [cargando, setCargando] = useState(true)

  /** Valida el token existente contra el backend */
  const validarToken = useCallback(async (tokenActual: string) => {
    try {
      const respuesta = await fetch('/api/auth/me', {
        headers: { Authorization: `Bearer ${tokenActual}` },
      })
      if (!respuesta.ok) {
        throw new Error('Token invalido')
      }
      const datos: Usuario = await respuesta.json()
      setUsuario(datos)
    } catch {
      // Token invalido o expirado — limpiar
      localStorage.removeItem(CLAVE_TOKEN)
      setToken(null)
      setUsuario(null)
    }
  }, [])

  // Validar token al montar
  useEffect(() => {
    if (token) {
      validarToken(token).finally(() => setCargando(false))
    } else {
      setCargando(false)
    }
  }, [token, validarToken])

  /** Inicia sesion con email y password */
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
    localStorage.setItem(CLAVE_TOKEN, nuevoToken)
    setToken(nuevoToken)

    // Obtener datos del usuario
    await validarToken(nuevoToken)
  }, [validarToken])

  /** Cierra sesion */
  const logout = useCallback(() => {
    localStorage.removeItem(CLAVE_TOKEN)
    setToken(null)
    setUsuario(null)
  }, [])

  return (
    <AuthContext.Provider value={{ token, usuario, login, logout, cargando }}>
      {children}
    </AuthContext.Provider>
  )
}

/** Hook para acceder al contexto de autenticacion */
export function useAuth(): AuthContextType {
  const contexto = useContext(AuthContext)
  if (!contexto) {
    throw new Error('useAuth debe usarse dentro de AuthProvider')
  }
  return contexto
}
