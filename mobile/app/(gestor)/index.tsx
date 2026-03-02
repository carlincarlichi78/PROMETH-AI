// mobile/app/(gestor)/index.tsx
import {
  ScrollView, View, Text, TouchableOpacity,
  StyleSheet, ActivityIndicator, RefreshControl,
} from 'react-native'
import { router } from 'expo-router'
import { useResumenGestor, type EmpresaResumen } from '@/hooks/useResumenGestor'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

const SEM_CONFIG = {
  rojo:     { color: '#f87171', bg: '#7f1d1d33', etiqueta: 'URGENTE' },
  amarillo: { color: '#fbbf24', bg: '#78350f33', etiqueta: 'ATENCIÓN' },
  verde:    { color: '#4ade80', bg: '#14532d33', etiqueta: 'EN ORDEN' },
}

function EmpresaCard({ e }: { e: EmpresaResumen }) {
  const cfg = SEM_CONFIG[e.semaforo] ?? SEM_CONFIG.verde
  return (
    <TouchableOpacity
      style={[s.card, { borderLeftColor: cfg.color }]}
      activeOpacity={0.75}
      onPress={() => router.push(`/(gestor)/empresa/${e.id}` as never)}
    >
      <View style={s.cardFila}>
        <View style={{ flex: 1 }}>
          <Text style={s.cardNombre} numberOfLines={1}>{e.nombre}</Text>
          <Text style={s.cardCif}>{e.cif}</Text>
        </View>
        <View style={[s.chip, { backgroundColor: cfg.bg }]}>
          <Text style={[s.chipTexto, { color: cfg.color }]}>{cfg.etiqueta}</Text>
        </View>
      </View>
      {e.alerta_texto && (
        <Text style={s.cardAlerta}>· {e.alerta_texto}</Text>
      )}
    </TouchableOpacity>
  )
}

export default function HomeGestor() {
  const insets = useSafeAreaInsets()
  const { data, isLoading, refetch, isRefetching } = useResumenGestor()

  if (isLoading) {
    return (
      <View style={s.centered}>
        <ActivityIndicator color="#f59e0b" size="large" />
      </View>
    )
  }

  const empresas = data?.empresas ?? []
  const rojas     = empresas.filter(e => e.semaforo === 'rojo')
  const amarillas = empresas.filter(e => e.semaforo === 'amarillo')
  const verdes    = empresas.filter(e => e.semaforo === 'verde')

  return (
    <ScrollView
      style={s.scroll}
      contentContainerStyle={[s.contenido, { paddingTop: insets.top + 16 }]}
      refreshControl={
        <RefreshControl refreshing={isRefetching} onRefresh={refetch} tintColor="#f59e0b" />
      }
    >
      {/* Cabecera */}
      <View style={s.cabecera}>
        <Text style={s.titulo}>Mis clientes</Text>
        <View style={s.badge}>
          <Text style={s.badgeTexto}>{empresas.length}</Text>
        </View>
      </View>

      {/* Urgentes */}
      {rojas.length > 0 && (
        <>
          <Text style={[s.grupo, { color: '#f87171' }]}>
            🔴 URGENTE ({rojas.length})
          </Text>
          {rojas.map(e => <EmpresaCard key={e.id} e={e} />)}
        </>
      )}

      {/* Atención */}
      {amarillas.length > 0 && (
        <>
          <Text style={[s.grupo, { color: '#fbbf24' }]}>
            🟡 REQUIEREN ATENCIÓN ({amarillas.length})
          </Text>
          {amarillas.map(e => <EmpresaCard key={e.id} e={e} />)}
        </>
      )}

      {/* En orden */}
      {verdes.length > 0 && (
        <>
          <Text style={[s.grupo, { color: '#4ade80' }]}>
            🟢 EN ORDEN ({verdes.length})
          </Text>
          {verdes.map(e => <EmpresaCard key={e.id} e={e} />)}
        </>
      )}

      {empresas.length === 0 && (
        <Text style={s.vacio}>Sin empresas asignadas</Text>
      )}
    </ScrollView>
  )
}

const s = StyleSheet.create({
  scroll: { flex: 1, backgroundColor: '#0f172a' },
  contenido: { paddingHorizontal: 20, paddingBottom: 40 },
  centered: {
    flex: 1, backgroundColor: '#0f172a',
    alignItems: 'center', justifyContent: 'center',
  },
  cabecera: {
    flexDirection: 'row', alignItems: 'center',
    marginBottom: 24, gap: 12,
  },
  titulo: { fontSize: 32, fontWeight: '800', color: '#fff', flex: 1 },
  badge: {
    backgroundColor: '#f59e0b', borderRadius: 20,
    minWidth: 36, height: 36,
    alignItems: 'center', justifyContent: 'center',
    paddingHorizontal: 10,
  },
  badgeTexto: { color: '#0f172a', fontWeight: '800', fontSize: 16 },
  grupo: { fontSize: 12, fontWeight: '700', letterSpacing: 1, marginTop: 20, marginBottom: 10 },
  card: {
    backgroundColor: '#1e293b', borderRadius: 16,
    padding: 16, marginBottom: 10, borderLeftWidth: 4,
  },
  cardFila: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  cardNombre: { fontSize: 16, fontWeight: '700', color: '#f1f5f9' },
  cardCif: { fontSize: 12, color: '#64748b', marginTop: 2 },
  chip: { borderRadius: 12, paddingHorizontal: 10, paddingVertical: 4 },
  chipTexto: { fontSize: 11, fontWeight: '700' },
  cardAlerta: { fontSize: 13, color: '#94a3b8', marginTop: 8 },
  vacio: { color: '#475569', textAlign: 'center', marginTop: 60, fontSize: 16 },
})
