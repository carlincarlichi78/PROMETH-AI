// mobile/app/(empresario)/subir.tsx
import { useState } from 'react'
import { View, Text, TextInput, TouchableOpacity, ScrollView, Alert, ActivityIndicator, StyleSheet } from 'react-native'
import * as ImagePicker from 'expo-image-picker'
import { Image } from 'react-native'
import { router } from 'expo-router'
import { useAuthStore } from '@/store/auth'
import { ProveedorSelector } from '@/components/upload/ProveedorSelector'
import { apiUpload } from '@/hooks/useApi'
import { useTiene } from '@/hooks/useTiene'
import { Camera, Image as ImageIcon, CheckCircle } from 'lucide-react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

const TIPOS_DOC = [
  { id: 'Factura',  icono: '🧾', desc: 'Factura de proveedor' },
  { id: 'Ticket',   icono: '🏪', desc: 'Ticket o recibo' },
  { id: 'Nómina',   icono: '👷', desc: 'Nómina de empleado' },
  { id: 'Extracto', icono: '🏦', desc: 'Extracto bancario' },
  { id: 'Otro',     icono: '📄', desc: 'Otro documento' },
]

const PASOS = ['Tipo', 'Foto', 'Datos', 'Confirmar']

interface Proveedor {
  cif: string; nombre: string
  base_imponible?: string; total?: string
  nif_trabajador?: string; salario_bruto?: string; retencion_irpf?: string; cuota_ss?: string
  entidad?: string; iban?: string; periodo?: string; saldo_final?: string
  descripcion?: string; importe?: string
}

export default function SubirDocumento() {
  const insets = useSafeAreaInsets()
  const puedeSubir = useTiene('subir_docs')
  const usuario = useAuthStore((s) => s.usuario)
  const empresaId = usuario?.empresas_asignadas?.[0]

  const [paso, setPaso] = useState(0)
  const [tipo, setTipo] = useState<string | null>(null)
  const [archivo, setArchivo] = useState<ImagePicker.ImagePickerAsset | null>(null)
  const [proveedor, setProveedor] = useState<Proveedor | null>(null)
  const [nota, setNota] = useState('')
  const [enviando, setEnviando] = useState(false)

  if (!puedeSubir) {
    return (
      <View style={s.bloqueado}>
        <Text style={s.bloqueadoEmoji}>🔒</Text>
        <Text style={s.bloqueadoTitulo}>Disponible en Plan Pro</Text>
        <Text style={s.bloqueadoDesc}>Actualiza tu plan para subir documentos desde la app.</Text>
      </View>
    )
  }

  const seleccionarImagen = async (fuente: 'camara' | 'galeria') => {
    let resultado: ImagePicker.ImagePickerResult
    if (fuente === 'camara') {
      const { status } = await ImagePicker.requestCameraPermissionsAsync()
      if (status !== 'granted') { Alert.alert('Permiso denegado', 'Necesitamos acceso a la cámara'); return }
      resultado = await ImagePicker.launchCameraAsync({ mediaTypes: ['images'], quality: 0.9 })
    } else {
      resultado = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['images'], quality: 0.9 })
    }
    if (!resultado.canceled && resultado.assets[0]) {
      setArchivo(resultado.assets[0])
      setPaso(2)
    }
  }

  const enviar = async () => {
    if (!empresaId || !archivo || !tipo) return
    setEnviando(true)
    try {
      const form = new FormData()
      // @ts-ignore — React Native FormData acepta este formato
      form.append('archivo', { uri: archivo.uri, name: archivo.fileName ?? 'doc.jpg', type: archivo.mimeType ?? 'image/jpeg' })
      form.append('tipo', tipo)
      if (proveedor?.cif) form.append('proveedor_cif', proveedor.cif)
      if (proveedor?.nombre) form.append('proveedor_nombre', proveedor.nombre)
      if (proveedor?.base_imponible) form.append('base_imponible', proveedor.base_imponible)
      if (proveedor?.total) form.append('total', proveedor.total)
      if (proveedor?.salario_bruto) form.append('salario_bruto', proveedor.salario_bruto)
      if (proveedor?.retencion_irpf) form.append('retencion_irpf', proveedor.retencion_irpf)
      if (proveedor?.cuota_ss) form.append('cuota_ss', proveedor.cuota_ss)
      if (proveedor?.entidad) form.append('entidad', proveedor.entidad)
      if (proveedor?.iban) form.append('iban', proveedor.iban)
      if (proveedor?.periodo) form.append('periodo', proveedor.periodo)
      if (proveedor?.saldo_final) form.append('saldo_final', proveedor.saldo_final)
      if (proveedor?.descripcion) form.append('descripcion', proveedor.descripcion)
      if (proveedor?.importe) form.append('importe', proveedor.importe)
      if (nota.trim()) form.append('nota_gestor', nota.trim())

      await apiUpload(`/api/portal/${empresaId}/documentos/subir`, form)
      setPaso(4)
    } catch (err) {
      Alert.alert('Error', err instanceof Error ? err.message : 'No se pudo enviar el documento')
    } finally {
      setEnviando(false)
    }
  }

  // Paso 4: éxito
  if (paso === 4) {
    return (
      <View style={[s.centered, { paddingBottom: insets.bottom + 20 }]}>
        <View style={s.exitoIcono}><CheckCircle size={64} color="#34d399" /></View>
        <Text style={s.exitoTitulo}>Documento enviado</Text>
        <Text style={s.exitoDesc}>Tu gestoría lo procesará en breve.</Text>
        <TouchableOpacity
          style={s.botonPrimario}
          onPress={() => { setPaso(0); setTipo(null); setArchivo(null); setProveedor(null); router.replace('/(empresario)/') }}
          activeOpacity={0.8}
        >
          <Text style={s.botonPrimarioTexto}>Volver al inicio</Text>
        </TouchableOpacity>
      </View>
    )
  }

  return (
    <View style={[s.root, { paddingTop: insets.top }]}>
      {/* Stepper */}
      <View style={s.stepper}>
        {PASOS.map((nombre, i) => (
          <View key={i} style={[s.stepItem, i === paso && s.stepActivo, i < paso && s.stepHecho]}>
            <Text style={[s.stepTexto, i === paso && s.stepTextoActivo, i < paso && s.stepTextoHecho]}>{nombre}</Text>
          </View>
        ))}
      </View>

      <ScrollView style={s.scroll} contentContainerStyle={[s.contenido, { paddingBottom: insets.bottom + 40 }]} keyboardShouldPersistTaps="handled">
        <Text style={s.titulo}>Subir documento</Text>

        {/* Paso 0: tipo */}
        {paso === 0 && (
          <View style={s.seccion}>
            <Text style={s.seccionDesc}>¿Qué tipo de documento es?</Text>
            {TIPOS_DOC.map((t) => (
              <TouchableOpacity
                key={t.id}
                style={[s.opcionCard, tipo === t.id && s.opcionSeleccionada]}
                onPress={() => { setTipo(t.id); setPaso(1) }}
                activeOpacity={0.7}
              >
                <Text style={s.opcionEmoji}>{t.icono}</Text>
                <View style={{ flex: 1 }}>
                  <Text style={s.opcionTitulo}>{t.id}</Text>
                  <Text style={s.opcionDesc}>{t.desc}</Text>
                </View>
              </TouchableOpacity>
            ))}
          </View>
        )}

        {/* Paso 1: archivo */}
        {paso === 1 && (
          <View style={s.seccion}>
            <Text style={s.seccionDesc}>Selecciona o captura el documento</Text>
            <TouchableOpacity style={[s.archivoCard, s.archivoPrincipal]} onPress={() => seleccionarImagen('camara')} activeOpacity={0.7}>
              <View style={[s.archivoIcono, { backgroundColor: '#f59e0b22' }]}>
                <Camera size={36} color="#f59e0b" />
              </View>
              <Text style={s.archivoTitulo}>Usar cámara</Text>
              <Text style={s.archivoSubtitulo}>Fotografía el documento ahora</Text>
            </TouchableOpacity>
            <TouchableOpacity style={s.archivoCard} onPress={() => seleccionarImagen('galeria')} activeOpacity={0.7}>
              <View style={[s.archivoIcono, { backgroundColor: '#94a3b822' }]}>
                <ImageIcon size={34} color="#94a3b8" />
              </View>
              <Text style={s.archivoTitulo}>Elegir de galería</Text>
              <Text style={s.archivoSubtitulo}>Selecciona una imagen existente</Text>
            </TouchableOpacity>
          </View>
        )}

        {/* Paso 2: datos del documento */}
        {paso === 2 && empresaId && (
          <View style={s.seccion}>
            {/* Preview de la foto */}
            {archivo && (
              <View style={s.previewBox}>
                <Text style={s.previewLabel}>Vista previa</Text>
                <Image source={{ uri: archivo.uri }} style={s.previewImagen} resizeMode="contain" />
              </View>
            )}
            <Text style={s.seccionTitulo}>Datos del documento</Text>
            <Text style={s.seccionDesc}>Introduce los datos para que el OCR sea más preciso</Text>
            <ProveedorSelector
              empresaId={empresaId}
              seleccionado={proveedor}
              onSeleccionar={(p) => { setProveedor(p) }}
              obligatorio
              tipoDoc={tipo ?? 'Factura'}
            />
            <Text style={s.notaLabel}>Nota para tu gestor (opcional)</Text>
            <TextInput
              style={s.notaInput}
              placeholder="Ej: Esta es la factura de la feria de agosto..."
              placeholderTextColor="#475569"
              value={nota}
              onChangeText={setNota}
              multiline
              maxLength={500}
            />
            <TouchableOpacity
              style={[s.botonSiguiente, !proveedor && { opacity: 0.4 }]}
              onPress={() => { if (proveedor) setPaso(3) }}
              disabled={!proveedor}
            >
              <Text style={s.botonSiguienteTexto}>Siguiente →</Text>
            </TouchableOpacity>
          </View>
        )}

        {/* Paso 3: confirmar */}
        {paso === 3 && (
          <View style={s.seccion}>
            <Text style={s.seccionTitulo}>Confirmar envío</Text>
            <View style={s.resumenCard}>
              {(() => {
                const etiqueta = proveedor?.entidad ? 'Entidad' : proveedor?.descripcion ? 'Documento' : 'Proveedor'
                const valor = proveedor?.nombre || proveedor?.entidad || proveedor?.descripcion
                return [
                  { e: 'Tipo', v: tipo ?? '-' },
                  { e: 'Archivo', v: archivo?.fileName ?? 'imagen.jpg' },
                  ...(valor ? [{ e: etiqueta, v: valor }] : []),
                ]
              })().map((f, i, arr) => (
                <View key={f.e} style={[s.resumenFila, i === arr.length - 1 && { borderBottomWidth: 0 }]}>
                  <Text style={s.resumenEtiqueta}>{f.e}</Text>
                  <Text style={s.resumenValor} numberOfLines={1}>{f.v}</Text>
                </View>
              ))}
            </View>
            <TouchableOpacity
              style={[s.botonPrimario, enviando && s.botonDesactivado]}
              onPress={enviar}
              disabled={enviando}
              activeOpacity={0.8}
            >
              {enviando
                ? <ActivityIndicator color="#0f172a" size="large" />
                : <Text style={s.botonPrimarioTexto}>Enviar documento</Text>}
            </TouchableOpacity>
          </View>
        )}
      </ScrollView>
    </View>
  )
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#0f172a' },
  scroll: { flex: 1 },
  contenido: { paddingHorizontal: 20 },
  centered: { flex: 1, backgroundColor: '#0f172a', alignItems: 'center', justifyContent: 'center', padding: 32 },

  bloqueado: { flex: 1, backgroundColor: '#0f172a', alignItems: 'center', justifyContent: 'center', padding: 24 },
  bloqueadoEmoji: { fontSize: 48, marginBottom: 16 },
  bloqueadoTitulo: { fontSize: 20, fontWeight: '700', color: '#ffffff', marginBottom: 8, textAlign: 'center' },
  bloqueadoDesc: { fontSize: 14, color: '#64748b', textAlign: 'center' },

  stepper: { flexDirection: 'row', gap: 5, paddingHorizontal: 20, paddingTop: 16, marginBottom: 20 },
  stepItem: { flex: 1, backgroundColor: '#1e293b', borderRadius: 8, paddingVertical: 8, alignItems: 'center' },
  stepActivo: { backgroundColor: '#f59e0b' },
  stepHecho: { backgroundColor: '#10b981' },
  stepTexto: { fontSize: 10, fontWeight: '700', color: '#475569' },
  stepTextoActivo: { color: '#0f172a' },
  stepTextoHecho: { color: '#ffffff' },

  titulo: { fontSize: 28, fontWeight: '800', color: '#ffffff', marginBottom: 20, marginTop: 8 },
  seccion: { gap: 12 },
  seccionTitulo: { fontSize: 20, fontWeight: '800', color: '#f1f5f9', marginBottom: 4 },
  seccionDesc: { fontSize: 15, color: '#64748b', marginBottom: 8 },

  opcionCard: { backgroundColor: '#1e293b', borderRadius: 16, paddingHorizontal: 18, paddingVertical: 16, flexDirection: 'row', alignItems: 'center', gap: 14, borderWidth: 2, borderColor: 'transparent' },
  opcionSeleccionada: { borderColor: '#f59e0b' },
  opcionEmoji: { fontSize: 26, width: 36, textAlign: 'center' },
  opcionTitulo: { fontSize: 17, fontWeight: '700', color: '#f1f5f9' },
  opcionDesc: { fontSize: 13, color: '#64748b', marginTop: 2 },

  archivoCard: { backgroundColor: '#1e293b', borderRadius: 20, padding: 24, alignItems: 'center', gap: 10, borderWidth: 2, borderColor: 'transparent' },
  archivoPrincipal: { borderColor: '#f59e0b' },
  archivoIcono: { width: 72, height: 72, borderRadius: 20, alignItems: 'center', justifyContent: 'center', marginBottom: 4 },
  archivoTitulo: { fontSize: 19, fontWeight: '800', color: '#f1f5f9' },
  archivoSubtitulo: { fontSize: 13, color: '#94a3b8', textAlign: 'center' },

  previewBox: { backgroundColor: '#1e293b', borderRadius: 16, padding: 12, marginBottom: 16, gap: 8 },
  previewLabel: { fontSize: 12, color: '#64748b', fontWeight: '600' },
  previewImagen: { width: '100%', height: 200, borderRadius: 10 },

  resumenCard: { backgroundColor: '#1e293b', borderRadius: 18, padding: 20, marginBottom: 24 },
  resumenFila: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 14, borderBottomWidth: 1, borderBottomColor: '#0f172a' },
  resumenEtiqueta: { fontSize: 15, color: '#64748b', fontWeight: '500' },
  resumenValor: { fontSize: 15, color: '#f1f5f9', fontWeight: '700', flex: 1, textAlign: 'right', marginLeft: 12 },

  botonPrimario: { backgroundColor: '#f59e0b', borderRadius: 16, paddingVertical: 20, alignItems: 'center', marginTop: 8 },
  botonDesactivado: { opacity: 0.5 },
  botonPrimarioTexto: { fontSize: 18, fontWeight: '800', color: '#0f172a' },

  exitoIcono: { backgroundColor: '#10b98122', borderRadius: 44, padding: 28, marginBottom: 28 },
  exitoTitulo: { fontSize: 28, fontWeight: '800', color: '#ffffff', marginBottom: 12, textAlign: 'center' },
  exitoDesc: { fontSize: 16, color: '#94a3b8', textAlign: 'center', lineHeight: 24, marginBottom: 40 },

  notaLabel: { fontSize: 14, color: '#94a3b8', marginTop: 16, marginBottom: 6 },
  notaInput: {
    backgroundColor: '#1e293b', borderRadius: 12, padding: 14,
    color: '#f1f5f9', fontSize: 15, height: 80,
    textAlignVertical: 'top', marginBottom: 16,
  },
  botonSiguiente: {
    backgroundColor: '#f59e0b', borderRadius: 14,
    paddingVertical: 16, alignItems: 'center',
  },
  botonSiguienteTexto: { fontSize: 15, fontWeight: '700', color: '#0f172a' },
})
