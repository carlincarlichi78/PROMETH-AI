// mobile/app/(auth)/recuperar-password.tsx
import { useState } from 'react'
import {
  View, Text, TextInput, TouchableOpacity, ActivityIndicator,
  Alert, StyleSheet, StatusBar, KeyboardAvoidingView, Platform, ScrollView,
} from 'react-native'
import { router } from 'expo-router'
import { apiFetch } from '@/hooks/useApi'

type Paso = 'email' | 'token'

export default function RecuperarPasswordScreen() {
  const [paso, setPaso] = useState<Paso>('email')
  const [email, setEmail] = useState('')
  const [token, setToken] = useState('')
  const [nuevaPassword, setNuevaPassword] = useState('')
  const [cargando, setCargando] = useState(false)

  const enviarSolicitud = async () => {
    if (!email.trim()) {
      Alert.alert('Campo vacío', 'Introduce tu correo electrónico')
      return
    }
    setCargando(true)
    try {
      await apiFetch('/api/auth/recuperar-password', {
        method: 'POST',
        body: JSON.stringify({ email: email.trim().toLowerCase() }),
      })
      setPaso('token')
    } catch (err) {
      Alert.alert('Error', err instanceof Error ? err.message : 'No se pudo procesar la solicitud')
    } finally {
      setCargando(false)
    }
  }

  const cambiarPassword = async () => {
    if (!token.trim() || !nuevaPassword.trim()) {
      Alert.alert('Campos vacíos', 'Introduce el código y la nueva contraseña')
      return
    }
    if (nuevaPassword.length < 8) {
      Alert.alert('Contraseña corta', 'La contraseña debe tener al menos 8 caracteres')
      return
    }
    setCargando(true)
    try {
      await apiFetch('/api/auth/reset-password', {
        method: 'POST',
        body: JSON.stringify({ token: token.trim(), nueva_password: nuevaPassword }),
      })
      Alert.alert(
        '¡Listo!',
        'Contraseña actualizada correctamente. Ya puedes iniciar sesión.',
        [{ text: 'Entrar', onPress: () => router.replace('/(auth)/login') }],
      )
    } catch (err) {
      Alert.alert('Error', err instanceof Error ? err.message : 'Código inválido o expirado')
    } finally {
      setCargando(false)
    }
  }

  return (
    <KeyboardAvoidingView
      style={s.flex}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <ScrollView contentContainerStyle={s.container} keyboardShouldPersistTaps="handled">
        <StatusBar barStyle="light-content" backgroundColor="#0f172a" />

        {/* Cabecera */}
        <View style={s.logoBox}>
          <Text style={s.logoLetra}>S</Text>
        </View>
        <Text style={s.titulo}>
          {paso === 'email' ? 'Recuperar acceso' : 'Nueva contraseña'}
        </Text>
        <Text style={s.subtitulo}>
          {paso === 'email'
            ? 'Te enviaremos un código de recuperación'
            : 'Introduce el código que recibiste y tu nueva contraseña'}
        </Text>

        {/* Formulario */}
        <View style={s.card}>
          {paso === 'email' ? (
            <>
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
                autoFocus
              />
              <TouchableOpacity
                style={[s.boton, cargando && s.botonOff]}
                onPress={enviarSolicitud}
                disabled={cargando}
                activeOpacity={0.8}
              >
                {cargando
                  ? <ActivityIndicator color="#0f172a" />
                  : <Text style={s.botonTexto}>Enviar código</Text>
                }
              </TouchableOpacity>
            </>
          ) : (
            <>
              <Text style={s.aviso}>
                Si el correo está registrado, tu gestor te facilitará el código (válido 2 horas).
              </Text>

              <Text style={s.label}>Código de recuperación</Text>
              <TextInput
                style={s.input}
                placeholder="Código recibido"
                placeholderTextColor="#64748b"
                value={token}
                onChangeText={setToken}
                autoCapitalize="none"
                autoCorrect={false}
                autoFocus
              />

              <Text style={[s.label, { marginTop: 16 }]}>Nueva contraseña</Text>
              <TextInput
                style={s.input}
                placeholder="Mínimo 8 caracteres"
                placeholderTextColor="#64748b"
                value={nuevaPassword}
                onChangeText={setNuevaPassword}
                secureTextEntry
              />

              <TouchableOpacity
                style={[s.boton, cargando && s.botonOff]}
                onPress={cambiarPassword}
                disabled={cargando}
                activeOpacity={0.8}
              >
                {cargando
                  ? <ActivityIndicator color="#0f172a" />
                  : <Text style={s.botonTexto}>Cambiar contraseña</Text>
                }
              </TouchableOpacity>

              <TouchableOpacity style={s.linkVolver} onPress={() => setPaso('email')}>
                <Text style={s.linkTexto}>← Volver</Text>
              </TouchableOpacity>
            </>
          )}
        </View>

        <TouchableOpacity style={s.linkVolver} onPress={() => router.back()}>
          <Text style={s.linkTexto}>Volver al login</Text>
        </TouchableOpacity>
      </ScrollView>
    </KeyboardAvoidingView>
  )
}

const s = StyleSheet.create({
  flex: { flex: 1, backgroundColor: '#0f172a' },
  container: {
    flexGrow: 1,
    backgroundColor: '#0f172a',
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 28,
    paddingVertical: 40,
  },
  logoBox: {
    width: 72,
    height: 72,
    backgroundColor: '#f59e0b',
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 16,
    shadowColor: '#f59e0b',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.4,
    shadowRadius: 10,
    elevation: 8,
  },
  logoLetra: { fontSize: 36, fontWeight: '900', color: '#0f172a' },
  titulo: {
    fontSize: 28,
    fontWeight: '800',
    color: '#ffffff',
    marginBottom: 6,
    textAlign: 'center',
  },
  subtitulo: {
    fontSize: 14,
    color: '#94a3b8',
    marginBottom: 32,
    textAlign: 'center',
    lineHeight: 20,
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
  aviso: {
    fontSize: 13,
    color: '#94a3b8',
    marginBottom: 20,
    lineHeight: 18,
    backgroundColor: '#0f172a',
    borderRadius: 10,
    padding: 12,
  },
  label: { fontSize: 15, fontWeight: '600', color: '#cbd5e1', marginBottom: 8 },
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
  botonOff: { opacity: 0.7 },
  botonTexto: { fontSize: 17, fontWeight: '800', color: '#0f172a' },
  linkVolver: { marginTop: 20, alignItems: 'center' },
  linkTexto: { color: '#94a3b8', fontSize: 14 },
})
