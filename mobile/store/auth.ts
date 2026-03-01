// mobile/store/auth.ts
import { create } from 'zustand'
import * as SecureStore from 'expo-secure-store'

interface Usuario {
  id: number
  email: string
  nombre: string
  rol: string
  plan_tier: string
  gestoria_id: number | null
  empresas_asignadas: number[]
}

interface AuthStore {
  token: string | null
  usuario: Usuario | null
  setToken: (token: string) => Promise<void>
  setUsuario: (usuario: Usuario) => void
  cerrarSesion: () => Promise<void>
  cargarTokenGuardado: () => Promise<string | null>
}

const CLAVE_TOKEN = 'sfce_token'

export const useAuthStore = create<AuthStore>((set) => ({
  token: null,
  usuario: null,

  setToken: async (token) => {
    await SecureStore.setItemAsync(CLAVE_TOKEN, token)
    set({ token })
  },

  setUsuario: (usuario) => set({ usuario }),

  cerrarSesion: async () => {
    await SecureStore.deleteItemAsync(CLAVE_TOKEN)
    set({ token: null, usuario: null })
  },

  cargarTokenGuardado: async () => {
    const token = await SecureStore.getItemAsync(CLAVE_TOKEN)
    if (token) set({ token })
    return token
  },
}))
