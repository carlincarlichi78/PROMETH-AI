// mobile/app/_layout.tsx
import { useEffect } from 'react'
import { Stack, router } from 'expo-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { SafeAreaProvider } from 'react-native-safe-area-context'
import { useAuthStore } from '@/store/auth'
import { apiFetch } from '@/hooks/useApi'
import '../global.css'

const queryClient = new QueryClient()

interface UsuarioMe {
  id: number
  email: string
  nombre: string
  rol: string
  plan_tier: string
  gestoria_id: number | null
  empresas_asignadas: number[]
}

function AuthGate({ children }: { children: React.ReactNode }) {
  const { cargarTokenGuardado, setUsuario, cerrarSesion } = useAuthStore()

  useEffect(() => {
    const init = async () => {
      const token = await cargarTokenGuardado()
      if (!token) {
        router.replace('/(auth)/login')
        return
      }
      try {
        const usuario = await apiFetch<UsuarioMe>('/api/auth/me')
        setUsuario(usuario)

        const rol = usuario.rol
        if (rol === 'cliente') {
          const empresaId = usuario.empresas_asignadas?.[0]
          if (empresaId) {
            try {
              const onb = await apiFetch<{ estado: string }>(
                `/api/onboarding/cliente/${empresaId}`
              )
              if (onb.estado === 'pendiente_cliente') {
                router.replace(`/onboarding/${empresaId}`)
                return
              }
            } catch { /* ignorar */ }
          }
          router.replace('/(empresario)/')
        } else {
          router.replace('/(gestor)/')
        }
      } catch {
        await cerrarSesion()
        router.replace('/(auth)/login')
      }
    }
    init()
  }, [])

  return <>{children}</>
}

export default function RootLayout() {
  return (
    <SafeAreaProvider>
      <QueryClientProvider client={queryClient}>
        <AuthGate>
          <Stack screenOptions={{ headerShown: false }} />
        </AuthGate>
      </QueryClientProvider>
    </SafeAreaProvider>
  )
}
