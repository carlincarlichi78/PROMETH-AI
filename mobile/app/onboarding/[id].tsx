// mobile/app/onboarding/[id].tsx
import { useState } from 'react'
import { View, Text, TextInput, TouchableOpacity, ScrollView, Alert, ActivityIndicator } from 'react-native'
import { useLocalSearchParams, router } from 'expo-router'
import { apiFetch } from '@/hooks/useApi'

const PASOS = ['Datos empresa', 'Cuenta bancaria', 'Documentación']

interface DatosForm {
  domicilio: string
  telefono: string
  persona_contacto: string
  iban: string
  banco_nombre: string
  email_facturas: string
  proveedores: string[]
  nuevo_proveedor: string
}

export default function OnboardingMovil() {
  const { id } = useLocalSearchParams<{ id: string }>()
  const empresaId = Number(id)
  const [paso, setPaso] = useState(0)
  const [datos, setDatos] = useState<DatosForm>({
    domicilio: '', telefono: '', persona_contacto: '',
    iban: '', banco_nombre: '',
    email_facturas: '', proveedores: [],
    nuevo_proveedor: '',
  })
  const [enviando, setEnviando] = useState(false)

  const actualizar = (campo: keyof DatosForm, valor: string) =>
    setDatos((d) => ({ ...d, [campo]: valor }))

  const agregarProveedor = () => {
    const nombre = datos.nuevo_proveedor.trim()
    if (nombre && !datos.proveedores.includes(nombre)) {
      setDatos((d) => ({ ...d, proveedores: [...d.proveedores, nombre], nuevo_proveedor: '' }))
    }
  }

  const enviar = async () => {
    setEnviando(true)
    try {
      await apiFetch(`/api/onboarding/cliente/${empresaId}`, {
        method: 'PUT',
        body: JSON.stringify({
          iban: datos.iban, banco_nombre: datos.banco_nombre,
          email_facturas: datos.email_facturas, proveedores: datos.proveedores,
        }),
      })
      router.replace('/(empresario)/')
    } catch (err) {
      Alert.alert('Error', err instanceof Error ? err.message : 'No se pudo guardar')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <ScrollView className="flex-1 bg-slate-950" contentContainerClassName="p-5 gap-5">
      <View className="mt-8">
        <Text className="text-2xl font-bold text-white">Completa tu alta</Text>
        <Text className="text-slate-400 text-sm mt-1">Tu gestoría ha iniciado el proceso.</Text>
      </View>

      {/* Stepper */}
      <View className="flex-row gap-1">
        {PASOS.map((nombre, i) => (
          <View key={i} className={`flex-1 py-1.5 rounded items-center ${i === paso ? 'bg-amber-400' : i < paso ? 'bg-emerald-700' : 'bg-slate-800'}`}>
            <Text className={`text-xs ${i === paso ? 'text-slate-900 font-semibold' : i < paso ? 'text-white' : 'text-slate-500'}`}>{nombre}</Text>
          </View>
        ))}
      </View>

      {/* Paso 0: datos empresa */}
      {paso === 0 && (
        <View className="gap-3">
          <Text className="text-slate-300">Datos de tu empresa</Text>
          {[
            { campo: 'domicilio' as keyof DatosForm, label: 'Domicilio fiscal', placeholder: 'Calle Mayor 1, 28001 Madrid' },
            { campo: 'telefono' as keyof DatosForm, label: 'Teléfono (opcional)', placeholder: '600 000 000' },
            { campo: 'persona_contacto' as keyof DatosForm, label: 'Persona de contacto', placeholder: 'Juan García' },
          ].map(({ campo, label, placeholder }) => (
            <View key={campo} className="gap-1">
              <Text className="text-sm text-slate-400">{label}</Text>
              <TextInput
                className="bg-slate-800 text-white rounded-xl px-4 py-3"
                placeholder={placeholder}
                placeholderTextColor="#64748b"
                value={datos[campo] as string}
                onChangeText={(v) => actualizar(campo, v)}
              />
            </View>
          ))}
          <TouchableOpacity className="bg-amber-400 rounded-xl py-4 items-center mt-2" onPress={() => setPaso(1)}>
            <Text className="text-slate-900 font-semibold">Siguiente →</Text>
          </TouchableOpacity>
        </View>
      )}

      {/* Paso 1: cuenta bancaria */}
      {paso === 1 && (
        <View className="gap-3">
          <Text className="text-slate-300">Cuenta bancaria</Text>
          {[
            { campo: 'iban' as keyof DatosForm, label: 'IBAN', placeholder: 'ES91 2100 0418 4502 0005 1332' },
            { campo: 'banco_nombre' as keyof DatosForm, label: 'Banco', placeholder: 'CaixaBank' },
          ].map(({ campo, label, placeholder }) => (
            <View key={campo} className="gap-1">
              <Text className="text-sm text-slate-400">{label}</Text>
              <TextInput
                className="bg-slate-800 text-white rounded-xl px-4 py-3"
                placeholder={placeholder}
                placeholderTextColor="#64748b"
                value={datos[campo] as string}
                onChangeText={(v) => actualizar(campo, v)}
                autoCapitalize="characters"
              />
            </View>
          ))}
          <TouchableOpacity className="bg-amber-400 rounded-xl py-4 items-center mt-2" onPress={() => setPaso(2)}>
            <Text className="text-slate-900 font-semibold">Siguiente →</Text>
          </TouchableOpacity>
        </View>
      )}

      {/* Paso 2: documentación */}
      {paso === 2 && (
        <View className="gap-3">
          <Text className="text-slate-300">Documentación</Text>
          <View className="gap-1">
            <Text className="text-sm text-slate-400">Email de facturas</Text>
            <TextInput
              className="bg-slate-800 text-white rounded-xl px-4 py-3"
              placeholder="facturas@miempresa.com"
              placeholderTextColor="#64748b"
              value={datos.email_facturas}
              onChangeText={(v) => actualizar('email_facturas', v)}
              keyboardType="email-address"
              autoCapitalize="none"
            />
          </View>
          <View className="gap-1">
            <Text className="text-sm text-slate-400">Proveedores habituales</Text>
            <View className="flex-row gap-2">
              <TextInput
                className="flex-1 bg-slate-800 text-white rounded-xl px-4 py-3"
                placeholder="Repsol, Endesa..."
                placeholderTextColor="#64748b"
                value={datos.nuevo_proveedor}
                onChangeText={(v) => actualizar('nuevo_proveedor', v)}
                onSubmitEditing={agregarProveedor}
              />
              <TouchableOpacity className="bg-slate-700 rounded-xl px-4 items-center justify-center" onPress={agregarProveedor}>
                <Text className="text-white">+</Text>
              </TouchableOpacity>
            </View>
            <View className="flex-row flex-wrap gap-2 pt-1">
              {datos.proveedores.map((p) => (
                <TouchableOpacity
                  key={p}
                  className="bg-slate-700 rounded-full px-3 py-1"
                  onPress={() => setDatos((d) => ({ ...d, proveedores: d.proveedores.filter((x) => x !== p) }))}
                >
                  <Text className="text-slate-300 text-xs">{p} ✕</Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>
          <TouchableOpacity
            className="bg-amber-400 rounded-xl py-4 items-center mt-2"
            onPress={enviar}
            disabled={enviando}
          >
            {enviando ? <ActivityIndicator color="#1e293b" /> : <Text className="text-slate-900 font-semibold">Completar alta</Text>}
          </TouchableOpacity>
        </View>
      )}
    </ScrollView>
  )
}
