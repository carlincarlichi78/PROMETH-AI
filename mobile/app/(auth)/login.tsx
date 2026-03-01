// mobile/app/(auth)/login.tsx
import { useState } from 'react'
import { View, Text, TextInput, TouchableOpacity, ActivityIndicator, Alert, StyleSheet, StatusBar } from 'react-native'
import { router } from 'expo-router'
import { useAuthStore } from '@/store/auth'
import { apiFetch } from '@/hooks/useApi'

interface UsuarioMe {
  id: number; email: string; nombre: string; rol: string
  plan_tier: string; gestoria_id: number | null; empresas_asignadas: number[]
}

export default function LoginScreen() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [cargando, setCargando] = useState(false)
  const { setToken, setUsuario } = useAuthStore()

  const handleLogin = async () => {
    if (!email.trim() || !password.trim()) {
      Alert.alert('Campos vacíos', 'Introduce tu email y contraseña')
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
            const onb = await apiFetch<{ estado: string }>(`/api/onboarding/cliente/${empresaId}`)
            if (onb.estado === 'pendiente_cliente') { router.replace(`/onboarding/${empresaId}`); return }
          } catch { /* ignorar */ }
        }
        router.replace('/(empresario)/')
      } else {
        router.replace('/(gestor)/')
      }
    } catch (err) {
      Alert.alert('Error al entrar', err instanceof Error ? err.message : 'No se pudo iniciar sesión')
    } finally {
      setCargando(false)
    }
  }

  return (
    <View style={s.container}>
      <StatusBar barStyle="light-content" backgroundColor="#0f172a" />

      {/* Logo */}
      <View style={s.logoBox}>
        <Text style={s.logoLetra}>S</Text>
      </View>
      <Text style={s.titulo}>SFCE</Text>
      <Text style={s.subtitulo}>Gestión contable inteligente</Text>

      {/* Formulario */}
      <View style={s.card}>
        <Text style={s.label}>Correo electrónico</Text>
        <TextInput
          style={s.input}
          placeholder="tu@email.com"
          placeholderTextColor="#64748b"
          value={email}
          onChangeText={setEmail}
          keyboardType="email-address"
          autoCapitalize="none"
          autoCorrect={false}
        />

        <Text style={[s.label, { marginTop: 16 }]}>Contraseña</Text>
        <TextInput
          style={s.input}
          placeholder="Tu contraseña"
          placeholderTextColor="#64748b"
          value={password}
          onChangeText={setPassword}
          secureTextEntry
        />

        <TouchableOpacity
          style={[s.boton, cargando && s.botonDesactivado]}
          onPress={handleLogin}
          disabled={cargando}
          activeOpacity={0.8}
        >
          {cargando
            ? <ActivityIndicator color="#0f172a" size="large" />
            : <Text style={s.botonTexto}>Entrar</Text>
          }
        </TouchableOpacity>
      </View>
    </View>
  )
}

const s = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0f172a',
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 28,
  },
  logoBox: {
    width: 88,
    height: 88,
    backgroundColor: '#f59e0b',
    borderRadius: 24,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 20,
    shadowColor: '#f59e0b',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.4,
    shadowRadius: 12,
    elevation: 10,
  },
  logoLetra: {
    fontSize: 44,
    fontWeight: '900',
    color: '#0f172a',
  },
  titulo: {
    fontSize: 40,
    fontWeight: '800',
    color: '#ffffff',
    marginBottom: 6,
    letterSpacing: 2,
  },
  subtitulo: {
    fontSize: 16,
    color: '#94a3b8',
    marginBottom: 40,
  },
  card: {
    width: '100%',
    backgroundColor: '#1e293b',
    borderRadius: 24,
    padding: 28,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.3,
    shadowRadius: 16,
    elevation: 8,
  },
  label: {
    fontSize: 15,
    fontWeight: '600',
    color: '#cbd5e1',
    marginBottom: 8,
  },
  input: {
    backgroundColor: '#0f172a',
    borderRadius: 14,
    paddingHorizontal: 18,
    paddingVertical: 16,
    fontSize: 16,
    color: '#ffffff',
    borderWidth: 1,
    borderColor: '#334155',
  },
  boton: {
    backgroundColor: '#f59e0b',
    borderRadius: 14,
    paddingVertical: 18,
    alignItems: 'center',
    marginTop: 24,
    shadowColor: '#f59e0b',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 6,
  },
  botonDesactivado: {
    opacity: 0.7,
  },
  botonTexto: {
    fontSize: 18,
    fontWeight: '800',
    color: '#0f172a',
    letterSpacing: 0.5,
  },
})
