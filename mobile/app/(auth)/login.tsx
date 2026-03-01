// mobile/app/(auth)/login.tsx
import { useState } from 'react'
import { View, Text, TextInput, TouchableOpacity, ActivityIndicator, Alert } from 'react-native'
import { router } from 'expo-router'
import { useAuthStore } from '@/store/auth'
import { apiFetch } from '@/hooks/useApi'

interface UsuarioMe {
  id: number
  email: string
  nombre: string
  rol: string
  plan_tier: string
  gestoria_id: number | null
  empresas_asignadas: number[]
}

export default function LoginScreen() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [cargando, setCargando] = useState(false)
  const { setToken, setUsuario } = useAuthStore()

  const handleLogin = async () => {
    if (!email.trim() || !password.trim()) {
      Alert.alert('Error', 'Introduce tu email y contraseña')
      return
    }
    setCargando(true)
    try {
      const datos = await apiFetch<{ access_token: string }>(
        '/api/auth/login',
        { method: 'POST', body: JSON.stringify({ email, password }) }
      )
      await setToken(datos.access_token)

      const usuario = await apiFetch<UsuarioMe>('/api/auth/me')
      setUsuario(usuario)

      if (usuario.rol === 'cliente') {
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
    } catch (err) {
      Alert.alert('Error', err instanceof Error ? err.message : 'No se pudo iniciar sesión')
    } finally {
      setCargando(false)
    }
  }

  return (
    <View className="flex-1 bg-slate-950 items-center justify-center px-6">
      <View className="w-16 h-16 bg-amber-400 rounded-2xl items-center justify-center mb-6">
        <Text className="text-2xl font-bold text-slate-900">S</Text>
      </View>
      <Text className="text-3xl font-semibold text-white mb-1">SFCE</Text>
      <Text className="text-slate-400 text-sm mb-8">Gestión contable inteligente</Text>

      <View className="w-full bg-slate-900 rounded-2xl p-6 gap-4">
        <View className="gap-1.5">
          <Text className="text-sm text-slate-300">Email</Text>
          <TextInput
            className="bg-slate-800 text-white rounded-xl px-4 py-3"
            placeholder="tu@email.com"
            placeholderTextColor="#64748b"
            value={email}
            onChangeText={setEmail}
            keyboardType="email-address"
            autoCapitalize="none"
            autoCorrect={false}
          />
        </View>
        <View className="gap-1.5">
          <Text className="text-sm text-slate-300">Contraseña</Text>
          <TextInput
            className="bg-slate-800 text-white rounded-xl px-4 py-3"
            placeholder="Mínimo 8 caracteres"
            placeholderTextColor="#64748b"
            value={password}
            onChangeText={setPassword}
            secureTextEntry
          />
        </View>
        <TouchableOpacity
          className="bg-amber-400 rounded-xl py-3 items-center mt-2"
          onPress={handleLogin}
          disabled={cargando}
        >
          {cargando
            ? <ActivityIndicator color="#1e293b" />
            : <Text className="text-slate-900 font-semibold">Entrar</Text>
          }
        </TouchableOpacity>
      </View>
    </View>
  )
}
