// mobile/app/(empresario)/mensajes.tsx
import { useState, useRef } from 'react'
import {
  View, Text, TextInput, TouchableOpacity, FlatList,
  StyleSheet, KeyboardAvoidingView, Platform,
} from 'react-native'
import { useAuthStore } from '@/store/auth'
import { useMensajes } from '@/hooks/useMensajes'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

export default function MensajesCliente() {
  const insets = useSafeAreaInsets()
  const usuario = useAuthStore((s) => s.usuario)
  const empresaId = usuario?.empresas_asignadas?.[0]
  const { data, enviar } = useMensajes(empresaId, 'cliente')
  const [texto, setTexto] = useState('')
  const flatRef = useRef<FlatList>(null)

  const mensajes = data?.mensajes ?? []

  const handleEnviar = () => {
    if (!texto.trim() || !empresaId) return
    enviar.mutate({ contenido: texto.trim(), contexto_tipo: 'libre' })
    setTexto('')
    setTimeout(() => flatRef.current?.scrollToEnd(), 300)
  }

  return (
    <KeyboardAvoidingView
      style={s.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      keyboardVerticalOffset={insets.bottom + 60}
    >
      <FlatList
        ref={flatRef}
        data={mensajes}
        keyExtractor={(m) => String(m.id)}
        contentContainerStyle={{ padding: 16, gap: 12 }}
        onContentSizeChange={() => flatRef.current?.scrollToEnd({ animated: false })}
        ListEmptyComponent={
          <View style={s.vacio}>
            <Text style={s.vacioTexto}>
              Sin mensajes. Escribe a tu gestor aquí.
            </Text>
          </View>
        }
        renderItem={({ item: m }) => {
          const esMio = m.autor_id === usuario?.id
          return (
            <View style={{ alignItems: esMio ? 'flex-end' : 'flex-start' }}>
              {m.contexto_desc && (
                <View style={s.contextChip}>
                  <Text style={s.contextTexto}>📎 {m.contexto_desc}</Text>
                </View>
              )}
              <View style={[s.burbuja, esMio ? s.burbujaPropia : s.burbujaAjena]}>
                <Text style={[s.burbujaTexto, esMio ? { color: '#0f172a' } : { color: '#f1f5f9' }]}>
                  {m.contenido}
                </Text>
              </View>
              <Text style={s.hora}>
                {new Date(m.fecha).toLocaleTimeString('es-ES', {
                  hour: '2-digit', minute: '2-digit',
                })}
              </Text>
            </View>
          )
        }}
      />

      <View style={[s.inputBar, { paddingBottom: insets.bottom + 8 }]}>
        <TextInput
          style={s.input}
          placeholder="Escribe un mensaje..."
          placeholderTextColor="#475569"
          value={texto}
          onChangeText={setTexto}
          multiline
          maxLength={1000}
        />
        <TouchableOpacity
          style={[s.enviarBtn, !texto.trim() && { opacity: 0.4 }]}
          onPress={handleEnviar}
          disabled={!texto.trim()}
        >
          <Text style={s.enviarTexto}>→</Text>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  )
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0f172a' },
  vacio: { flex: 1, alignItems: 'center', marginTop: 80 },
  vacioTexto: { color: '#475569', fontSize: 15, textAlign: 'center' },
  contextChip: {
    backgroundColor: '#1e3a5f', borderRadius: 10,
    paddingHorizontal: 10, paddingVertical: 4, marginBottom: 4,
  },
  contextTexto: { fontSize: 11, color: '#93c5fd' },
  burbuja: { maxWidth: '80%', borderRadius: 18, paddingHorizontal: 16, paddingVertical: 10 },
  burbujaPropia: { backgroundColor: '#f59e0b', borderBottomRightRadius: 4 },
  burbujaAjena: { backgroundColor: '#1e293b', borderBottomLeftRadius: 4 },
  burbujaTexto: { fontSize: 15 },
  hora: { fontSize: 11, color: '#475569', marginTop: 3 },
  inputBar: {
    flexDirection: 'row', alignItems: 'flex-end',
    padding: 12, borderTopWidth: 1, borderTopColor: '#1e293b', gap: 10,
  },
  input: {
    flex: 1, backgroundColor: '#1e293b', borderRadius: 20,
    paddingHorizontal: 16, paddingVertical: 10,
    color: '#f1f5f9', fontSize: 15, maxHeight: 100,
  },
  enviarBtn: {
    backgroundColor: '#f59e0b', width: 44, height: 44,
    borderRadius: 22, alignItems: 'center', justifyContent: 'center',
  },
  enviarTexto: { fontSize: 20, color: '#0f172a', fontWeight: '700' },
})
