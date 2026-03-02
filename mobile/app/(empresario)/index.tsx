// mobile/app/(empresario)/index.tsx
import {
  ScrollView, View, Text, TouchableOpacity,
  StyleSheet, ActivityIndicator,
} from 'react-native'
import { router } from 'expo-router'
import { useQuery } from '@tanstack/react-query'
import { useAuthStore } from '@/store/auth'
import { apiFetch } from '@/hooks/useApi'
import { useSemaforo } from '@/hooks/useSemaforo'
import { useAhorraX } from '@/hooks/useAhorraX'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

const COLOR_SEMAFORO = {
  verde:    { bg: '#052e16', texto: '#4ade80', emoji: '🟢', etiqueta: 'Todo en orden' },
  amarillo: { bg: '#422006', texto: '#fbbf24', emoji: '🟡', etiqueta: 'Requiere atención' },
  rojo:     { bg: '#450a0a', texto: '#f87171', emoji: '🔴', etiqueta: 'Urgente' },
}

function fmt(n: number) {
  return n.toLocaleString('es-ES', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 })
}

export default function HomeEmpresario() {
  const insets = useSafeAreaInsets()
  const usuario = useAuthStore((s) => s.usuario)
  const empresaId = usuario?.empresas_asignadas?.[0]

  const { data: semaforo, isLoading: cargandoSem } = useSemaforo(empresaId)
  const { data: ahorra } = useAhorraX(empresaId)
  const { data: docsData } = useQuery({
    queryKey: ['documentos-recientes', empresaId],
    queryFn: () => apiFetch<{
      documentos: {
        id: number
        tipo_doc?: string
        tipo?: string
        nombre_archivo?: string
        nombre?: string
        estado: string
      }[]
    }>(`/api/portal/${empresaId}/documentos`),
    enabled: !!empresaId,
  })

  const cfg = COLOR_SEMAFORO[semaforo?.color ?? 'verde']

  if (cargandoSem) {
    return (
      <View style={s.centered}>
        <ActivityIndicator color="#f59e0b" size="large" />
      </View>
    )
  }

  return (
    <ScrollView
      style={s.scroll}
      contentContainerStyle={[s.contenido, { paddingTop: insets.top + 16 }]}
    >
      {/* Semáforo */}
      <View style={[s.semaforo, { backgroundColor: cfg.bg }]}>
        <Text style={s.semaforoEmoji}>{cfg.emoji}</Text>
        <Text style={[s.semaforoTexto, { color: cfg.texto }]}>{cfg.etiqueta}</Text>
      </View>

      {/* Widget Ahorra X€ */}
      {ahorra && ahorra.aparta_mes > 0 && (
        <View style={s.card}>
          <Text style={s.cardLabel}>💰 APARTA ESTE MES</Text>
          <Text style={s.ahorraImporte}>{fmt(ahorra.aparta_mes)}</Text>
          <View style={s.ahorraDetalle}>
            <Text style={s.ahorraLinea}>
              IVA {ahorra.trimestre}  {fmt(ahorra.iva_estimado_trimestre)}
            </Text>
            {ahorra.irpf_estimado_trimestre > 0 && (
              <Text style={s.ahorraLinea}>
                IRPF {ahorra.trimestre}  {fmt(ahorra.irpf_estimado_trimestre)}
              </Text>
            )}
            <Text style={[s.ahorraLinea, { color: '#64748b', marginTop: 4 }]}>
              Vence: {new Date(ahorra.vencimiento_trimestre).toLocaleDateString('es-ES')}
            </Text>
          </View>
        </View>
      )}

      {/* Alertas */}
      {(semaforo?.alertas ?? []).length > 0 && (
        <View style={s.card}>
          <Text style={s.cardLabel}>⚠️ ALERTAS</Text>
          {semaforo!.alertas.map((a, i) => (
            <Text key={i} style={s.alertaTexto}>· {a.mensaje}</Text>
          ))}
        </View>
      )}

      {/* Documentos recientes */}
      <Text style={s.seccionTitulo}>📄 Documentos recientes</Text>
      {(docsData?.documentos ?? []).slice(0, 8).map((d) => (
        <View key={d.id} style={s.docFila}>
          <View style={s.docChip}>
            <Text style={s.docChipTexto}>{d.tipo_doc ?? d.tipo}</Text>
          </View>
          <Text style={s.docNombre} numberOfLines={1}>
            {d.nombre_archivo ?? d.nombre}
          </Text>
          <Text style={[s.docEstado, { color: d.estado === 'procesado' ? '#4ade80' : '#fbbf24' }]}>
            {d.estado === 'procesado' ? '✓' : '⏳'}
          </Text>
        </View>
      ))}

      {/* Acciones */}
      <View style={s.acciones}>
        <TouchableOpacity
          style={s.boton}
          onPress={() => router.push('/(empresario)/subir')}
        >
          <Text style={s.botonTexto}>+ Subir documento</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[s.boton, s.botonSecundario]}
          onPress={() => router.push('/(empresario)/mensajes')}
        >
          <Text style={[s.botonTexto, { color: '#f59e0b' }]}>💬 Mensajes</Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  )
}

const s = StyleSheet.create({
  scroll: { flex: 1, backgroundColor: '#0f172a' },
  contenido: { paddingHorizontal: 20, paddingBottom: 40, gap: 14 },
  centered: {
    flex: 1, backgroundColor: '#0f172a',
    alignItems: 'center', justifyContent: 'center',
  },
  semaforo: { borderRadius: 20, padding: 24, alignItems: 'center', gap: 8 },
  semaforoEmoji: { fontSize: 40 },
  semaforoTexto: { fontSize: 20, fontWeight: '700' },
  card: { backgroundColor: '#1e293b', borderRadius: 20, padding: 20, gap: 8 },
  cardLabel: { fontSize: 11, fontWeight: '700', color: '#64748b', letterSpacing: 1.2 },
  ahorraImporte: { fontSize: 48, fontWeight: '900', color: '#f59e0b' },
  ahorraDetalle: { gap: 2 },
  ahorraLinea: { fontSize: 14, color: '#94a3b8' },
  alertaTexto: { fontSize: 14, color: '#fca5a5' },
  seccionTitulo: { fontSize: 13, fontWeight: '600', color: '#64748b', letterSpacing: 0.5 },
  docFila: {
    flexDirection: 'row', alignItems: 'center',
    backgroundColor: '#1e293b', borderRadius: 14,
    paddingHorizontal: 14, paddingVertical: 12, gap: 10,
  },
  docChip: {
    backgroundColor: '#334155', borderRadius: 8,
    paddingHorizontal: 8, paddingVertical: 3,
  },
  docChipTexto: { fontSize: 10, color: '#94a3b8', fontWeight: '600' },
  docNombre: { flex: 1, fontSize: 14, color: '#e2e8f0' },
  docEstado: { fontSize: 16 },
  acciones: { flexDirection: 'row', gap: 10, marginTop: 4 },
  boton: {
    flex: 1, backgroundColor: '#f59e0b', borderRadius: 14,
    paddingVertical: 16, alignItems: 'center',
  },
  botonSecundario: {
    backgroundColor: '#1e293b', borderWidth: 1, borderColor: '#f59e0b',
  },
  botonTexto: { fontSize: 15, fontWeight: '700', color: '#0f172a' },
})
