// mobile/app/(gestor)/subir.tsx
import { useState } from 'react'
import { View, Text, TouchableOpacity, ScrollView, Alert, ActivityIndicator, StyleSheet, Platform } from 'react-native'
import * as ImagePicker from 'expo-image-picker'
import * as DocumentPicker from 'expo-document-picker'
import { useSafeAreaInsets } from 'react-native-safe-area-context'
import { useQuery } from '@tanstack/react-query'
import { router } from 'expo-router'
import { apiFetch, apiUpload } from '@/hooks/useApi'
import { ProveedorSelector } from '@/components/upload/ProveedorSelector'
import { Camera, FileText, CheckCircle, Building2, ChevronRight, ArrowLeft, ExternalLink } from 'lucide-react-native'
import { Image } from 'react-native'
import * as Sharing from 'expo-sharing'

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
  const insets = useSafeAreaInsets()
  const [paso, setPaso] = useState(0)
  const [empresa, setEmpresa] = useState<Empresa | null>(null)
  const [tipo, setTipo] = useState<string | null>(null)
  const [archivo, setArchivo] = useState<{ uri: string; name: string; mimeType: string; esFoto: boolean } | null>(null)
  const [proveedor, setProveedor] = useState<Proveedor | null>(null)
  const [enviando, setEnviando] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ['gestor-resumen'],
    queryFn: () => apiFetch<{ empresas: Empresa[] }>('/api/gestor/resumen'),
  })

  const seleccionarPDF = async () => {
    const result = await DocumentPicker.getDocumentAsync({
      type: [
        'application/pdf',
        'image/*',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'text/csv',
        'text/plain',
      ],
      copyToCacheDirectory: true,
    })
    if (!result.canceled && result.assets[0]) {
      const asset = result.assets[0]
      const esFoto = (asset.mimeType ?? '').startsWith('image/')
      setArchivo({ uri: asset.uri, name: asset.name, mimeType: asset.mimeType ?? 'application/pdf', esFoto })
      setPaso(3)
    }
  }

  const seleccionarFoto = async () => {
    const { status } = await ImagePicker.requestCameraPermissionsAsync()
    if (status !== 'granted') { Alert.alert('Permiso denegado', 'Necesitamos acceso a la cámara'); return }
    const result = await ImagePicker.launchCameraAsync({ mediaTypes: ['images'], quality: 0.9 })
    if (!result.canceled && result.assets[0]) {
      const asset = result.assets[0]
      setArchivo({ uri: asset.uri, name: asset.fileName ?? 'foto.jpg', mimeType: asset.mimeType ?? 'image/jpeg', esFoto: true })
      setPaso(3)
    }
  }

  const enviar = async () => {
    if (!empresa || !archivo || !tipo) return
    setEnviando(true)
    try {
      const form = new FormData()
      // @ts-ignore
      form.append('archivo', { uri: archivo.uri, name: archivo.name, type: archivo.mimeType })
      form.append('tipo', tipo)
      if (proveedor?.cif) form.append('proveedor_cif', proveedor.cif)
      if (proveedor?.nombre) form.append('proveedor_nombre', proveedor.nombre)
      if (proveedor?.base_imponible) form.append('base_imponible', proveedor.base_imponible)
      if (proveedor?.total) form.append('total', proveedor.total)
      await apiUpload(`/api/portal/${empresa.id}/documentos/subir`, form)
      setPaso(5)
    } catch (err) {
      Alert.alert('Error al enviar', err instanceof Error ? err.message : 'No se pudo enviar')
    } finally {
      setEnviando(false)
    }
  }

  const retroceder = () => {
    if (paso > 0) setPaso(paso - 1)
    else router.replace('/(gestor)/')
  }

  const resetear = () => {
    setPaso(0); setEmpresa(null); setTipo(null); setArchivo(null); setProveedor(null)
    router.replace('/(gestor)/')
  }

  // ── Éxito ──
  if (paso === 5) {
    return (
      <View style={[s.centered, { paddingBottom: insets.bottom + 20 }]}>
        <View style={s.exitoIcono}><CheckCircle size={56} color="#10b981" /></View>
        <Text style={s.exitoTitulo}>¡Documento enviado!</Text>
        <Text style={s.exitoDesc}>Subido para {empresa?.nombre}.{'\n'}El pipeline lo procesará en breve.</Text>
        <TouchableOpacity style={s.botonPrimario} onPress={resetear} activeOpacity={0.8}>
          <Text style={s.botonPrimarioTexto}>Volver a empresas</Text>
        </TouchableOpacity>
      </View>
    )
  }

  return (
    <View style={[s.root, { paddingTop: insets.top }]}>
      {/* Cabecera con botón atrás */}
      <View style={s.header}>
        <TouchableOpacity style={s.btnAtras} onPress={retroceder} activeOpacity={0.7}>
          <ArrowLeft size={24} color="#f59e0b" />
        </TouchableOpacity>
        <Text style={s.headerTitulo}>Subir documento</Text>
        <View style={{ width: 44 }} />
      </View>

      {/* Stepper */}
      <View style={s.stepper}>
        {PASOS.map((nombre, i) => (
          <View key={i} style={[s.stepItem, i === paso && s.stepActivo, i < paso && s.stepHecho]}>
            <Text style={[s.stepTexto, i === paso && s.stepTextoActivo, i < paso && s.stepTextoHecho]}>{nombre}</Text>
          </View>
        ))}
      </View>

      <ScrollView style={s.scroll} contentContainerStyle={[s.contenido, { paddingBottom: insets.bottom + 40 }]} keyboardShouldPersistTaps="handled">

        {/* ── Paso 0: Empresa ── */}
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
                  <ChevronRight size={22} color="#475569" />
                </TouchableOpacity>
              ))
            }
          </View>
        )}

        {/* ── Paso 1: Tipo ── */}
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
                <ChevronRight size={22} color="#475569" />
              </TouchableOpacity>
            ))}
          </View>
        )}

        {/* ── Paso 2: Archivo ── */}
        {paso === 2 && (
          <View>
            <Text style={s.seccionTitulo}>Selecciona el archivo</Text>

            {/* PDF — opción principal */}
            <TouchableOpacity style={[s.archivoCard, s.archivoPrincipal]} onPress={seleccionarPDF} activeOpacity={0.7}>
              <View style={[s.archivoIcono, { backgroundColor: '#ef444422' }]}>
                <FileText size={38} color="#ef4444" />
              </View>
              <Text style={s.archivoTitulo}>PDF o imagen del móvil</Text>
              <Text style={s.archivoDesc}>PDF · Excel · CSV · TXT · Imagen{'\n'}El sistema reconoce el texto automáticamente</Text>
            </TouchableOpacity>

            {/* Cámara — opción secundaria */}
            <TouchableOpacity style={s.archivoCard} onPress={seleccionarFoto} activeOpacity={0.7}>
              <View style={[s.archivoIcono, { backgroundColor: '#f59e0b22' }]}>
                <Camera size={36} color="#f59e0b" />
              </View>
              <Text style={s.archivoTitulo}>Fotografiar ahora</Text>
              <Text style={s.archivoDesc}>Saca una foto con la cámara</Text>
            </TouchableOpacity>
          </View>
        )}

        {/* ── Paso 3: Proveedor + Preview ── */}
        {paso === 3 && empresa && (
          <View>
            {/* Preview del documento */}
            {archivo?.esFoto ? (
              <View style={s.previewBox}>
                <Text style={s.previewLabel}>📄 Documento seleccionado</Text>
                <Image source={{ uri: archivo.uri }} style={s.previewImagen} resizeMode="contain" />
                <Text style={s.previewNombre}>{archivo.name}</Text>
              </View>
            ) : archivo ? (
              <TouchableOpacity style={s.previewArchivo} onPress={async () => { if (await Sharing.isAvailableAsync()) await Sharing.shareAsync(archivo.uri) }} activeOpacity={0.7}>
                <View style={s.previewArchivoIcono}>
                  <FileText size={28} color={archivo.mimeType.includes('pdf') ? '#ef4444' : archivo.mimeType.includes('sheet') || archivo.mimeType.includes('excel') || archivo.mimeType.includes('csv') ? '#10b981' : '#94a3b8'} />
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={s.previewArchivoNombre} numberOfLines={1}>{archivo.name}</Text>
                  <Text style={s.previewArchivoTipo}>{archivo.mimeType.includes('pdf') ? 'PDF' : archivo.mimeType.includes('sheet') || archivo.mimeType.includes('excel') ? 'Excel' : archivo.mimeType.includes('csv') ? 'CSV' : 'Archivo'}</Text>
                </View>
                <ExternalLink size={18} color="#475569" />
              </TouchableOpacity>
            ) : null}

            <Text style={s.seccionTitulo}>Datos del documento</Text>
            <Text style={s.seccionDesc}>Para {empresa.nombre}</Text>
            <ProveedorSelector empresaId={empresa.id} seleccionado={proveedor} onSeleccionar={(p) => { setProveedor(p); setPaso(4) }} obligatorio={archivo?.esFoto ?? false} tipoDoc={tipo ?? 'Factura'} />
            {!archivo?.esFoto && (
              <TouchableOpacity style={s.botonSecundario} onPress={() => setPaso(4)} activeOpacity={0.7}>
                <Text style={s.botonSecundarioTexto}>Omitir — el OCR extraerá los datos</Text>
              </TouchableOpacity>
            )}
          </View>
        )}

        {/* ── Paso 4: Confirmar ── */}
        {paso === 4 && (
          <View>
            <Text style={s.seccionTitulo}>Confirmar envío</Text>
            <View style={s.resumenCard}>
              {[
                { e: 'Empresa', v: empresa?.nombre ?? '-' },
                { e: 'Tipo', v: tipo ?? '-' },
                { e: 'Archivo', v: archivo?.name ?? '-' },
                ...(proveedor ? [{ e: 'Proveedor', v: proveedor.nombre }] : []),
              ].map((f, i, arr) => (
                <View key={f.e} style={[s.resumenFila, i === arr.length - 1 && { borderBottomWidth: 0 }]}>
                  <Text style={s.resumenEtiqueta}>{f.e}</Text>
                  <Text style={s.resumenValor} numberOfLines={1}>{f.v}</Text>
                </View>
              ))}
            </View>
            <TouchableOpacity style={[s.botonPrimario, enviando && s.botonDesactivado]} onPress={enviar} disabled={enviando} activeOpacity={0.8}>
              {enviando ? <ActivityIndicator color="#0f172a" size="large" /> : <Text style={s.botonPrimarioTexto}>Enviar al pipeline →</Text>}
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

  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 16, paddingVertical: 12 },
  btnAtras: { width: 44, height: 44, borderRadius: 22, backgroundColor: '#1e293b', alignItems: 'center', justifyContent: 'center' },
  headerTitulo: { fontSize: 18, fontWeight: '700', color: '#ffffff' },

  stepper: { flexDirection: 'row', gap: 5, paddingHorizontal: 20, marginBottom: 28 },
  stepItem: { flex: 1, backgroundColor: '#1e293b', borderRadius: 8, paddingVertical: 8, alignItems: 'center' },
  stepActivo: { backgroundColor: '#f59e0b' },
  stepHecho: { backgroundColor: '#10b981' },
  stepTexto: { fontSize: 10, fontWeight: '700', color: '#475569' },
  stepTextoActivo: { color: '#0f172a' },
  stepTextoHecho: { color: '#ffffff' },

  seccionTitulo: { fontSize: 24, fontWeight: '800', color: '#f1f5f9', marginBottom: 6 },
  seccionDesc: { fontSize: 15, color: '#64748b', marginBottom: 20 },

  opcionCard: { backgroundColor: '#1e293b', borderRadius: 18, padding: 18, flexDirection: 'row', alignItems: 'center', gap: 16, marginBottom: 12, borderWidth: 2, borderColor: 'transparent' },
  opcionSeleccionada: { borderColor: '#f59e0b' },
  opcionIcono: { width: 50, height: 50, backgroundColor: '#0f172a', borderRadius: 14, alignItems: 'center', justifyContent: 'center' },
  opcionEmoji: { fontSize: 28, width: 50, textAlign: 'center' },
  opcionTitulo: { fontSize: 18, fontWeight: '700', color: '#f1f5f9' },
  opcionDesc: { fontSize: 13, color: '#64748b', marginTop: 3 },

  archivoCard: { backgroundColor: '#1e293b', borderRadius: 20, padding: 24, alignItems: 'center', gap: 10, marginBottom: 14 },
  archivoPrincipal: { borderWidth: 2, borderColor: '#ef4444' },
  archivoIcono: { width: 76, height: 76, borderRadius: 22, alignItems: 'center', justifyContent: 'center', marginBottom: 4 },
  archivoTitulo: { fontSize: 20, fontWeight: '800', color: '#f1f5f9' },
  archivoDesc: { fontSize: 14, color: '#94a3b8', textAlign: 'center', lineHeight: 20 },

  resumenCard: { backgroundColor: '#1e293b', borderRadius: 18, padding: 20, marginBottom: 24 },
  resumenFila: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 14, borderBottomWidth: 1, borderBottomColor: '#0f172a' },
  resumenEtiqueta: { fontSize: 15, color: '#64748b', fontWeight: '500' },
  resumenValor: { fontSize: 15, color: '#f1f5f9', fontWeight: '700', flex: 1, textAlign: 'right' },

  botonPrimario: { backgroundColor: '#f59e0b', borderRadius: 16, paddingVertical: 20, alignItems: 'center', shadowColor: '#f59e0b', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.35, shadowRadius: 10, elevation: 8 },
  botonDesactivado: { opacity: 0.6 },
  botonPrimarioTexto: { fontSize: 18, fontWeight: '800', color: '#0f172a' },
  botonSecundario: { paddingVertical: 18, alignItems: 'center' },
  botonSecundarioTexto: { fontSize: 16, color: '#475569', fontWeight: '600' },

  previewBox: { backgroundColor: '#1e293b', borderRadius: 18, padding: 14, marginBottom: 20, alignItems: 'center', gap: 10 },
  previewLabel: { fontSize: 13, color: '#64748b', fontWeight: '600', alignSelf: 'flex-start' },
  previewImagen: { width: '100%', height: 220, borderRadius: 12 },
  previewNombre: { fontSize: 12, color: '#475569', alignSelf: 'flex-start' },
  previewArchivo: { backgroundColor: '#1e293b', borderRadius: 16, padding: 16, flexDirection: 'row', alignItems: 'center', gap: 14, marginBottom: 20 },
  previewArchivoIcono: { width: 52, height: 52, backgroundColor: '#0f172a', borderRadius: 14, alignItems: 'center', justifyContent: 'center' },
  previewArchivoNombre: { fontSize: 16, fontWeight: '700', color: '#f1f5f9' },
  previewArchivoTipo: { fontSize: 13, color: '#64748b', marginTop: 2 },
  exitoIcono: { backgroundColor: '#10b98122', borderRadius: 44, padding: 28, marginBottom: 28 },
  exitoTitulo: { fontSize: 30, fontWeight: '800', color: '#ffffff', marginBottom: 14, textAlign: 'center' },
  exitoDesc: { fontSize: 17, color: '#94a3b8', textAlign: 'center', lineHeight: 26, marginBottom: 40 },
})
