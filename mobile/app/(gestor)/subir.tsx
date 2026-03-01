// mobile/app/(gestor)/subir.tsx
import { useState } from 'react'
import { View, Text, TouchableOpacity, ScrollView, Alert, ActivityIndicator, StyleSheet } from 'react-native'
import * as ImagePicker from 'expo-image-picker'
import { useQuery } from '@tanstack/react-query'
import { router } from 'expo-router'
import { apiFetch, apiUpload } from '@/hooks/useApi'
import { ProveedorSelector } from '@/components/upload/ProveedorSelector'
import { Camera, ImageIcon, CheckCircle, Building2, ChevronRight } from 'lucide-react-native'

const TIPOS_DOC = [
  { id: 'Factura',  icono: '🧾', desc: 'Factura de proveedor' },
  { id: 'Ticket',   icono: '🏪', desc: 'Ticket o recibo' },
  { id: 'Nómina',   icono: '👷', desc: 'Nómina de empleado' },
  { id: 'Extracto', icono: '🏦', desc: 'Extracto bancario' },
  { id: 'Otro',     icono: '📄', desc: 'Otro documento' },
]

const PASOS = ['Empresa', 'Tipo', 'Archivo', 'Proveedor', 'Confirmar']

interface Empresa { id: number; nombre: string; cif: string; estado_onboarding: string }
interface Proveedor { cif: string; nombre: string }

export default function SubirGestor() {
  const [paso, setPaso] = useState(0)
  const [empresa, setEmpresa] = useState<Empresa | null>(null)
  const [tipo, setTipo] = useState<string | null>(null)
  const [archivo, setArchivo] = useState<ImagePicker.ImagePickerAsset | null>(null)
  const [proveedor, setProveedor] = useState<Proveedor | null>(null)
  const [enviando, setEnviando] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ['gestor-resumen'],
    queryFn: () => apiFetch<{ empresas: Empresa[] }>('/api/gestor/resumen'),
  })

  const seleccionarImagen = async (fuente: 'camara' | 'galeria') => {
    let result: ImagePicker.ImagePickerResult
    if (fuente === 'camara') {
      const { status } = await ImagePicker.requestCameraPermissionsAsync()
      if (status !== 'granted') { Alert.alert('Permiso denegado', 'Necesitamos acceso a la cámara'); return }
      result = await ImagePicker.launchCameraAsync({ mediaTypes: ['images'], quality: 0.85 })
    } else {
      result = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['images'], quality: 0.85 })
    }
    if (!result.canceled && result.assets[0]) {
      setArchivo(result.assets[0])
      setPaso(3)
    }
  }

  const enviar = async () => {
    if (!empresa || !archivo || !tipo) return
    setEnviando(true)
    try {
      const form = new FormData()
      // @ts-ignore
      form.append('archivo', { uri: archivo.uri, name: archivo.fileName ?? 'doc.jpg', type: archivo.mimeType ?? 'image/jpeg' })
      form.append('tipo', tipo)
      if (proveedor?.cif) form.append('proveedor_cif', proveedor.cif)
      if (proveedor?.nombre) form.append('proveedor_nombre', proveedor.nombre)
      await apiUpload(`/api/portal/${empresa.id}/documentos/subir`, form)
      setPaso(5)
    } catch (err) {
      Alert.alert('Error al enviar', err instanceof Error ? err.message : 'No se pudo enviar')
    } finally {
      setEnviando(false)
    }
  }

  const resetear = () => {
    setPaso(0); setEmpresa(null); setTipo(null); setArchivo(null); setProveedor(null)
    router.replace('/(gestor)/')
  }

  if (paso === 5) {
    return (
      <View style={s.centered}>
        <View style={s.exitoIcono}>
          <CheckCircle size={52} color="#10b981" />
        </View>
        <Text style={s.exitoTitulo}>¡Documento enviado!</Text>
        <Text style={s.exitoDesc}>Subido para {empresa?.nombre}.{'\n'}El pipeline lo procesará en breve.</Text>
        <TouchableOpacity style={s.botonPrimario} onPress={resetear} activeOpacity={0.8}>
          <Text style={s.botonPrimarioTexto}>Volver a empresas</Text>
        </TouchableOpacity>
      </View>
    )
  }

  return (
    <ScrollView style={s.scroll} contentContainerStyle={s.contenido} keyboardShouldPersistTaps="handled">
      <Text style={s.titulo}>Subir documento</Text>

      <View style={s.stepper}>
        {PASOS.map((nombre, i) => (
          <View key={i} style={[s.stepItem, i === paso && s.stepActivo, i < paso && s.stepHecho]}>
            <Text style={[s.stepTexto, i === paso && s.stepTextoActivo, i < paso && s.stepTextoHecho]}>{nombre}</Text>
          </View>
        ))}
      </View>

      {paso === 0 && (
        <View>
          <Text style={s.seccionTitulo}>¿Para qué empresa?</Text>
          {isLoading
            ? <ActivityIndicator color="#f59e0b" size="large" style={{ marginTop: 32 }} />
            : (data?.empresas ?? []).map((e) => (
              <TouchableOpacity key={e.id} style={s.opcionCard} onPress={() => { setEmpresa(e); setPaso(1) }} activeOpacity={0.7}>
                <View style={s.opcionIcono}><Building2 size={22} color="#f59e0b" /></View>
                <View style={{ flex: 1 }}>
                  <Text style={s.opcionTitulo}>{e.nombre}</Text>
                  <Text style={s.opcionDesc}>{e.cif}</Text>
                </View>
                <ChevronRight size={20} color="#475569" />
              </TouchableOpacity>
            ))
          }
        </View>
      )}

      {paso === 1 && (
        <View>
          <Text style={s.seccionTitulo}>¿Qué tipo de documento?</Text>
          {TIPOS_DOC.map((t) => (
            <TouchableOpacity key={t.id} style={[s.opcionCard, tipo === t.id && s.opcionSeleccionada]} onPress={() => { setTipo(t.id); setPaso(2) }} activeOpacity={0.7}>
              <Text style={s.opcionEmoji}>{t.icono}</Text>
              <View style={{ flex: 1 }}>
                <Text style={s.opcionTitulo}>{t.id}</Text>
                <Text style={s.opcionDesc}>{t.desc}</Text>
              </View>
              <ChevronRight size={20} color="#475569" />
            </TouchableOpacity>
          ))}
        </View>
      )}

      {paso === 2 && (
        <View>
          <Text style={s.seccionTitulo}>Selecciona el documento</Text>
          <TouchableOpacity style={s.archivoCard} onPress={() => seleccionarImagen('camara')} activeOpacity={0.7}>
            <View style={[s.archivoIcono, { backgroundColor: '#f59e0b22' }]}>
              <Camera size={36} color="#f59e0b" />
            </View>
            <Text style={s.archivoTitulo}>Usar cámara</Text>
            <Text style={s.archivoDesc}>Fotografía el documento</Text>
          </TouchableOpacity>
          <TouchableOpacity style={s.archivoCard} onPress={() => seleccionarImagen('galeria')} activeOpacity={0.7}>
            <View style={[s.archivoIcono, { backgroundColor: '#3b82f622' }]}>
              <ImageIcon size={36} color="#3b82f6" />
            </View>
            <Text style={s.archivoTitulo}>Galería de fotos</Text>
            <Text style={s.archivoDesc}>Elige un archivo existente</Text>
          </TouchableOpacity>
        </View>
      )}

      {paso === 3 && empresa && (
        <View>
          <Text style={s.seccionTitulo}>¿Quién es el proveedor?</Text>
          <Text style={s.seccionDesc}>Para {empresa.nombre}</Text>
          <ProveedorSelector empresaId={empresa.id} seleccionado={proveedor} onSeleccionar={(p) => { setProveedor(p); setPaso(4) }} />
          <TouchableOpacity style={s.botonSecundario} onPress={() => setPaso(4)} activeOpacity={0.7}>
            <Text style={s.botonSecundarioTexto}>Asignar después</Text>
          </TouchableOpacity>
        </View>
      )}

      {paso === 4 && (
        <View>
          <Text style={s.seccionTitulo}>Confirmar envío</Text>
          <View style={s.resumenCard}>
            {[
              { e: 'Empresa', v: empresa?.nombre ?? '-' },
              { e: 'Tipo', v: tipo ?? '-' },
              { e: 'Archivo', v: archivo?.fileName ?? 'imagen.jpg' },
              ...(proveedor ? [{ e: 'Proveedor', v: proveedor.nombre }] : []),
            ].map((f) => (
              <View key={f.e} style={s.resumenFila}>
                <Text style={s.resumenEtiqueta}>{f.e}</Text>
                <Text style={s.resumenValor} numberOfLines={1}>{f.v}</Text>
              </View>
            ))}
          </View>
          <TouchableOpacity style={[s.botonPrimario, enviando && s.botonDesactivado]} onPress={enviar} disabled={enviando} activeOpacity={0.8}>
            {enviando ? <ActivityIndicator color="#0f172a" size="large" /> : <Text style={s.botonPrimarioTexto}>Enviar al pipeline</Text>}
          </TouchableOpacity>
          <TouchableOpacity style={s.botonSecundario} onPress={() => setPaso(3)} activeOpacity={0.7}>
            <Text style={s.botonSecundarioTexto}>← Atrás</Text>
          </TouchableOpacity>
        </View>
      )}
    </ScrollView>
  )
}

const s = StyleSheet.create({
  scroll: { flex: 1, backgroundColor: '#0f172a' },
  contenido: { paddingHorizontal: 20, paddingBottom: 40 },
  centered: { flex: 1, backgroundColor: '#0f172a', alignItems: 'center', justifyContent: 'center', padding: 32 },
  titulo: { fontSize: 30, fontWeight: '800', color: '#ffffff', marginTop: 60, marginBottom: 20 },
  stepper: { flexDirection: 'row', gap: 6, marginBottom: 32 },
  stepItem: { flex: 1, backgroundColor: '#1e293b', borderRadius: 8, paddingVertical: 7, alignItems: 'center' },
  stepActivo: { backgroundColor: '#f59e0b' },
  stepHecho: { backgroundColor: '#10b981' },
  stepTexto: { fontSize: 10, fontWeight: '600', color: '#475569' },
  stepTextoActivo: { color: '#0f172a' },
  stepTextoHecho: { color: '#ffffff' },
  seccionTitulo: { fontSize: 22, fontWeight: '700', color: '#f1f5f9', marginBottom: 6 },
  seccionDesc: { fontSize: 15, color: '#64748b', marginBottom: 20 },
  opcionCard: { backgroundColor: '#1e293b', borderRadius: 18, padding: 18, flexDirection: 'row', alignItems: 'center', gap: 16, marginBottom: 12, borderWidth: 2, borderColor: 'transparent' },
  opcionSeleccionada: { borderColor: '#f59e0b' },
  opcionIcono: { width: 48, height: 48, backgroundColor: '#0f172a', borderRadius: 14, alignItems: 'center', justifyContent: 'center' },
  opcionEmoji: { fontSize: 28, width: 48, textAlign: 'center' },
  opcionTitulo: { fontSize: 17, fontWeight: '700', color: '#f1f5f9' },
  opcionDesc: { fontSize: 13, color: '#64748b', marginTop: 2 },
  archivoCard: { backgroundColor: '#1e293b', borderRadius: 18, padding: 28, alignItems: 'center', gap: 12, marginBottom: 16 },
  archivoIcono: { width: 72, height: 72, borderRadius: 20, alignItems: 'center', justifyContent: 'center' },
  archivoTitulo: { fontSize: 19, fontWeight: '700', color: '#f1f5f9' },
  archivoDesc: { fontSize: 14, color: '#64748b' },
  resumenCard: { backgroundColor: '#1e293b', borderRadius: 18, padding: 20, marginBottom: 24 },
  resumenFila: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: '#0f172a' },
  resumenEtiqueta: { fontSize: 15, color: '#64748b', fontWeight: '500' },
  resumenValor: { fontSize: 15, color: '#f1f5f9', fontWeight: '600', flex: 1, textAlign: 'right' },
  botonPrimario: { backgroundColor: '#f59e0b', borderRadius: 16, paddingVertical: 20, alignItems: 'center', marginBottom: 12, shadowColor: '#f59e0b', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.3, shadowRadius: 8, elevation: 6 },
  botonDesactivado: { opacity: 0.6 },
  botonPrimarioTexto: { fontSize: 18, fontWeight: '800', color: '#0f172a' },
  botonSecundario: { paddingVertical: 16, alignItems: 'center' },
  botonSecundarioTexto: { fontSize: 16, color: '#64748b', fontWeight: '600' },
  exitoIcono: { backgroundColor: '#10b98122', borderRadius: 40, padding: 24, marginBottom: 24 },
  exitoTitulo: { fontSize: 28, fontWeight: '800', color: '#ffffff', marginBottom: 12, textAlign: 'center' },
  exitoDesc: { fontSize: 16, color: '#94a3b8', textAlign: 'center', lineHeight: 24, marginBottom: 36 },
})
