// mobile/app/(empresario)/documentos.tsx
import { View, Text, FlatList, StyleSheet, ActivityIndicator, TouchableOpacity } from 'react-native'
import { useQuery } from '@tanstack/react-query'
import { useSafeAreaInsets } from 'react-native-safe-area-context'
import { useAuthStore } from '@/store/auth'
import { apiFetch } from '@/hooks/useApi'
import { FileText, RefreshCw } from 'lucide-react-native'

interface DocItem {
  id: number
  nombre: string
  tipo: string
  estado: string
  fecha: string | null
}

const ESTADO_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  pendiente:  { label: 'Pendiente',  color: '#fbbf24', bg: '#f59e0b22' },
  procesado:  { label: 'Procesado',  color: '#34d399', bg: '#10b98122' },
  cuarentena: { label: 'Cuarentena', color: '#f87171', bg: '#ef444422' },
  error:      { label: 'Error',      color: '#f87171', bg: '#ef444422' },
}

const TIPO_LABEL: Record<string, string> = {
  FV: 'Factura', BAN: 'Extracto', NOM: 'Nómina', FC: 'Venta',
}

function DocCard({ item }: { item: DocItem }) {
  const estadoCfg = ESTADO_CONFIG[item.estado] ?? { label: item.estado, color: '#94a3b8', bg: '#94a3b822' }
  const nombre = item.nombre?.split('/').pop()?.split('\\').pop() ?? item.nombre ?? '—'
  const tipo = TIPO_LABEL[item.tipo] ?? item.tipo ?? '—'
  const fecha = item.fecha
    ? new Date(item.fecha).toLocaleDateString('es-ES', { day: '2-digit', month: 'short', year: 'numeric' })
    : null

  return (
    <View style={s.card}>
      <View style={s.cardIcono}>
        <FileText size={22} color="#64748b" />
      </View>
      <View style={{ flex: 1, gap: 4 }}>
        <Text style={s.cardNombre} numberOfLines={1}>{nombre}</Text>
        <View style={s.cardMeta}>
          <Text style={s.cardTipo}>{tipo}</Text>
          {fecha && <Text style={s.cardFecha}>{fecha}</Text>}
        </View>
      </View>
      <View style={[s.estadoChip, { backgroundColor: estadoCfg.bg }]}>
        <Text style={[s.estadoTexto, { color: estadoCfg.color }]}>{estadoCfg.label}</Text>
      </View>
    </View>
  )
}

export default function DocumentosScreen() {
  const insets = useSafeAreaInsets()
  const usuario = useAuthStore((s) => s.usuario)
  const empresaId = usuario?.empresas_asignadas?.[0]

  const { data, isLoading, refetch, isRefetching } = useQuery({
    queryKey: ['documentos-portal', empresaId],
    queryFn: () => apiFetch<{ documentos: DocItem[] }>(`/api/portal/${empresaId}/documentos`),
    enabled: !!empresaId,
    staleTime: 30_000,
  })

  const docs = data?.documentos ?? []

  return (
    <View style={[s.root, { paddingTop: insets.top }]}>
      <View style={s.header}>
        <Text style={s.titulo}>Mis documentos</Text>
        <TouchableOpacity onPress={() => refetch()} activeOpacity={0.7} style={s.btnRefresh}>
          {isRefetching
            ? <ActivityIndicator size="small" color="#f59e0b" />
            : <RefreshCw size={18} color="#64748b" />}
        </TouchableOpacity>
      </View>

      {isLoading ? (
        <View style={s.centered}>
          <ActivityIndicator color="#f59e0b" size="large" />
        </View>
      ) : docs.length === 0 ? (
        <View style={s.centered}>
          <FileText size={48} color="#334155" />
          <Text style={s.vaciaTitulo}>Sin documentos</Text>
          <Text style={s.vaciaDesc}>Aún no has subido ningún documento.</Text>
        </View>
      ) : (
        <FlatList
          data={docs}
          keyExtractor={(d) => String(d.id)}
          renderItem={({ item }) => <DocCard item={item} />}
          contentContainerStyle={[s.lista, { paddingBottom: insets.bottom + 20 }]}
          showsVerticalScrollIndicator={false}
        />
      )}
    </View>
  )
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#0f172a' },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 20, paddingVertical: 16 },
  titulo: { fontSize: 24, fontWeight: '800', color: '#f1f5f9' },
  btnRefresh: { width: 38, height: 38, borderRadius: 19, backgroundColor: '#1e293b', alignItems: 'center', justifyContent: 'center' },

  centered: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 12 },
  vaciaTitulo: { fontSize: 18, fontWeight: '700', color: '#94a3b8', marginTop: 8 },
  vaciaDesc: { fontSize: 14, color: '#475569', textAlign: 'center' },

  lista: { paddingHorizontal: 16, gap: 10 },

  card: { backgroundColor: '#1e293b', borderRadius: 16, padding: 16, flexDirection: 'row', alignItems: 'center', gap: 14 },
  cardIcono: { width: 44, height: 44, borderRadius: 12, backgroundColor: '#0f172a', alignItems: 'center', justifyContent: 'center' },
  cardNombre: { fontSize: 15, fontWeight: '600', color: '#f1f5f9' },
  cardMeta: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  cardTipo: { fontSize: 12, color: '#64748b', fontWeight: '500' },
  cardFecha: { fontSize: 12, color: '#475569' },

  estadoChip: { borderRadius: 10, paddingHorizontal: 10, paddingVertical: 5 },
  estadoTexto: { fontSize: 11, fontWeight: '700' },
})
