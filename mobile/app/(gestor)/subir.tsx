// mobile/app/(gestor)/subir.tsx
import { useState } from 'react'
import { View, Text, TouchableOpacity, ScrollView, Alert, ActivityIndicator } from 'react-native'
import * as ImagePicker from 'expo-image-picker'
import { useQuery } from '@tanstack/react-query'
import { router } from 'expo-router'
import { apiFetch, apiUpload } from '@/hooks/useApi'
import { ProveedorSelector } from '@/components/upload/ProveedorSelector'
import { Camera, Image, CheckCircle } from 'lucide-react-native'

const TIPOS_DOC = ['Factura', 'Ticket', 'Nómina', 'Extracto', 'Otro']

interface Empresa { id: number; nombre: string; cif: string; estado_onboarding: string }
interface Proveedor { cif: string; nombre: string }

export default function SubirGestor() {
  const [paso, setPaso] = useState(0)
  const [empresaSeleccionada, setEmpresaSeleccionada] = useState<Empresa | null>(null)
  const [tipo, setTipo] = useState<string | null>(null)
  const [archivo, setArchivo] = useState<ImagePicker.ImagePickerAsset | null>(null)
  const [proveedor, setProveedor] = useState<Proveedor | null>(null)
  const [enviando, setEnviando] = useState(false)

  const { data: gestorData, isLoading } = useQuery({
    queryKey: ['gestor-resumen'],
    queryFn: () => apiFetch<{ empresas: Empresa[] }>('/api/gestor/resumen'),
  })

  const seleccionarImagen = async (fuente: 'camara' | 'galeria') => {
    let resultado: ImagePicker.ImagePickerResult
    if (fuente === 'camara') {
      const { status } = await ImagePicker.requestCameraPermissionsAsync()
      if (status !== 'granted') { Alert.alert('Permiso denegado', 'Necesitamos acceso a la cámara'); return }
      resultado = await ImagePicker.launchCameraAsync({ mediaTypes: ['images'], quality: 0.8 })
    } else {
      resultado = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['images'], quality: 0.8 })
    }
    if (!resultado.canceled && resultado.assets[0]) {
      setArchivo(resultado.assets[0])
      setPaso(3)
    }
  }

  const enviar = async () => {
    if (!empresaSeleccionada || !archivo || !tipo) return
    setEnviando(true)
    try {
      const form = new FormData()
      // @ts-ignore
      form.append('archivo', { uri: archivo.uri, name: archivo.fileName ?? 'doc.jpg', type: archivo.mimeType ?? 'image/jpeg' })
      form.append('tipo', tipo)
      if (proveedor?.cif) form.append('proveedor_cif', proveedor.cif)
      if (proveedor?.nombre) form.append('proveedor_nombre', proveedor.nombre)

      await apiUpload(`/api/portal/${empresaSeleccionada.id}/documentos/subir`, form)
      setPaso(5)
    } catch (err) {
      Alert.alert('Error', err instanceof Error ? err.message : 'No se pudo enviar el documento')
    } finally {
      setEnviando(false)
    }
  }

  if (paso === 5) {
    return (
      <View className="flex-1 bg-slate-950 items-center justify-center p-6 gap-4">
        <CheckCircle size={64} color="#34d399" />
        <Text className="text-white text-xl font-bold">Documento enviado</Text>
        <Text className="text-slate-400 text-center">Subido para {empresaSeleccionada?.nombre}.</Text>
        <TouchableOpacity
          className="bg-amber-400 rounded-xl px-8 py-3"
          onPress={() => { setPaso(0); setEmpresaSeleccionada(null); setTipo(null); setArchivo(null); setProveedor(null); router.replace('/(gestor)/') }}
        >
          <Text className="text-slate-900 font-semibold">Volver a empresas</Text>
        </TouchableOpacity>
      </View>
    )
  }

  return (
    <ScrollView className="flex-1 bg-slate-950" contentContainerClassName="p-5 gap-5">
      <Text className="text-2xl font-bold text-white mt-8">Subir documento</Text>

      {/* Stepper */}
      <View className="flex-row gap-1">
        {['Empresa', 'Tipo', 'Archivo', 'Proveedor', 'Confirmar'].map((nombre, i) => (
          <View key={i} className={`flex-1 py-1 rounded items-center ${i === paso ? 'bg-amber-400' : i < paso ? 'bg-emerald-700' : 'bg-slate-800'}`}>
            <Text className={`text-[10px] font-medium ${i === paso ? 'text-slate-900' : i < paso ? 'text-white' : 'text-slate-500'}`}>{nombre}</Text>
          </View>
        ))}
      </View>

      {/* Paso 0: empresa */}
      {paso === 0 && (
        <View className="gap-3">
          <Text className="text-slate-300">Selecciona la empresa cliente</Text>
          {isLoading
            ? <ActivityIndicator color="#fbbf24" />
            : (gestorData?.empresas ?? []).map((e) => (
              <TouchableOpacity
                key={e.id}
                className="bg-slate-900 rounded-xl px-4 py-4"
                onPress={() => { setEmpresaSeleccionada(e); setPaso(1) }}
              >
                <Text className="text-white font-medium">{e.nombre}</Text>
                <Text className="text-slate-400 text-xs">{e.cif}</Text>
              </TouchableOpacity>
            ))
          }
        </View>
      )}

      {/* Paso 1: tipo */}
      {paso === 1 && (
        <View className="gap-3">
          <Text className="text-slate-300">¿Qué tipo de documento es?</Text>
          {TIPOS_DOC.map((t) => (
            <TouchableOpacity
              key={t}
              className={`bg-slate-900 rounded-xl px-4 py-4 ${tipo === t ? 'border border-amber-400' : ''}`}
              onPress={() => { setTipo(t); setPaso(2) }}
            >
              <Text className="text-white font-medium">{t}</Text>
            </TouchableOpacity>
          ))}
        </View>
      )}

      {/* Paso 2: archivo */}
      {paso === 2 && (
        <View className="gap-3">
          <Text className="text-slate-300">Selecciona o captura el documento</Text>
          <TouchableOpacity className="bg-slate-900 rounded-xl p-6 items-center gap-3" onPress={() => seleccionarImagen('camara')}>
            <Camera size={32} color="#fbbf24" />
            <Text className="text-white font-medium">Usar cámara</Text>
          </TouchableOpacity>
          <TouchableOpacity className="bg-slate-900 rounded-xl p-6 items-center gap-3" onPress={() => seleccionarImagen('galeria')}>
            <Image size={32} color="#94a3b8" />
            <Text className="text-slate-300">Elegir de galería</Text>
          </TouchableOpacity>
        </View>
      )}

      {/* Paso 3: proveedor */}
      {paso === 3 && empresaSeleccionada && (
        <View className="gap-3">
          <Text className="text-slate-300">¿De qué proveedor es? ({empresaSeleccionada.nombre})</Text>
          <ProveedorSelector
            empresaId={empresaSeleccionada.id}
            seleccionado={proveedor}
            onSeleccionar={(p) => { setProveedor(p); setPaso(4) }}
          />
          <TouchableOpacity onPress={() => setPaso(4)}>
            <Text className="text-slate-500 text-center text-sm">Saltar (asignar después)</Text>
          </TouchableOpacity>
        </View>
      )}

      {/* Paso 4: confirmar */}
      {paso === 4 && (
        <View className="gap-4">
          <Text className="text-slate-300">Resumen</Text>
          <View className="bg-slate-900 rounded-xl p-4 gap-2">
            <Text className="text-slate-400 text-sm">Empresa: <Text className="text-white">{empresaSeleccionada?.nombre}</Text></Text>
            <Text className="text-slate-400 text-sm">Tipo: <Text className="text-white">{tipo}</Text></Text>
            <Text className="text-slate-400 text-sm">Archivo: <Text className="text-white">{archivo?.fileName ?? 'imagen.jpg'}</Text></Text>
            {proveedor && <Text className="text-slate-400 text-sm">Proveedor: <Text className="text-white">{proveedor.nombre}</Text></Text>}
          </View>
          <TouchableOpacity
            className="bg-amber-400 rounded-xl py-4 items-center"
            onPress={enviar}
            disabled={enviando}
          >
            {enviando ? <ActivityIndicator color="#1e293b" /> : <Text className="text-slate-900 font-semibold">Enviar documento</Text>}
          </TouchableOpacity>
        </View>
      )}
    </ScrollView>
  )
}
