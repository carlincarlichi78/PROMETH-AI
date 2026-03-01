// mobile/app/(gestor)/index.tsx
import { View, Text, ScrollView, ActivityIndicator, StyleSheet, TouchableOpacity } from 'react-native'
import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/hooks/useApi'

interface Empresa { id: number; nombre: string; cif: string; estado_onboarding: string }

const ESTADO_CONFIG: Record<string, { color: string; etiqueta: string }> = {
  configurada:        { color: '#10b981', etiqueta: 'Activa' },
  pendiente_cliente:  { color: '#f59e0b', etiqueta: 'Pendiente cliente' },
  cliente_completado: { color: '#3b82f6', etiqueta: 'Lista para configurar' },
  esqueleto:          { color: '#64748b', etiqueta: 'Esqueleto' },
}

export default function EmpresasGestor() {
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['gestor-resumen'],
    queryFn: () => apiFetch<{ empresas: Empresa[] }>('/api/gestor/resumen'),
  })

  if (isLoading) return (
    <View style={s.centered}>
      <ActivityIndicator color="#f59e0b" size="large" />
      <Text style={s.cargandoTexto}>Cargando empresas...</Text>
    </View>
  )

  const empresas = data?.empresas ?? []

  return (
    <ScrollView style={s.scroll} contentContainerStyle={s.contenido}>
      {/* Cabecera */}
      <View style={s.cabecera}>
        <Text style={s.titulo}>Mis empresas</Text>
        <View style={s.badgeTotal}>
          <Text style={s.badgeTexto}>{empresas.length}</Text>
        </View>
      </View>

      {empresas.length === 0 ? (
        <View style={s.vacio}>
          <Text style={s.vacioTexto}>No hay empresas asignadas</Text>
        </View>
      ) : (
        empresas.map((e) => {
          const cfg = ESTADO_CONFIG[e.estado_onboarding] ?? { color: '#64748b', etiqueta: e.estado_onboarding }
          return (
            <TouchableOpacity key={e.id} style={s.card} activeOpacity={0.7}>
              {/* Barra de estado lateral */}
              <View style={[s.barraEstado, { backgroundColor: cfg.color }]} />

              <View style={s.cardContenido}>
                <View style={s.cardFila}>
                  <Text style={s.cardNombre} numberOfLines={1}>{e.nombre}</Text>
                </View>
                <Text style={s.cardCif}>{e.cif}</Text>
                <View style={[s.chip, { backgroundColor: cfg.color + '22' }]}>
                  <View style={[s.chipDot, { backgroundColor: cfg.color }]} />
                  <Text style={[s.chipTexto, { color: cfg.color }]}>{cfg.etiqueta}</Text>
                </View>
              </View>
            </TouchableOpacity>
          )
        })
      )}
    </ScrollView>
  )
}

const s = StyleSheet.create({
  scroll: { flex: 1, backgroundColor: '#0f172a' },
  contenido: { paddingHorizontal: 20, paddingBottom: 32 },
  centered: { flex: 1, backgroundColor: '#0f172a', alignItems: 'center', justifyContent: 'center', gap: 12 },
  cargandoTexto: { color: '#94a3b8', fontSize: 16, marginTop: 8 },

  cabecera: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginTop: 60,
    marginBottom: 24,
  },
  titulo: { fontSize: 32, fontWeight: '800', color: '#ffffff', flex: 1 },
  badgeTotal: {
    backgroundColor: '#f59e0b',
    borderRadius: 20,
    minWidth: 36,
    height: 36,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 10,
  },
  badgeTexto: { color: '#0f172a', fontWeight: '800', fontSize: 16 },

  vacio: { alignItems: 'center', paddingVertical: 60 },
  vacioTexto: { color: '#475569', fontSize: 17 },

  card: {
    backgroundColor: '#1e293b',
    borderRadius: 20,
    marginBottom: 14,
    flexDirection: 'row',
    overflow: 'hidden',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 6,
    elevation: 4,
  },
  barraEstado: { width: 6 },
  cardContenido: { flex: 1, padding: 18 },
  cardFila: { flexDirection: 'row', alignItems: 'center', marginBottom: 4 },
  cardNombre: { fontSize: 18, fontWeight: '700', color: '#f1f5f9', flex: 1 },
  cardCif: { fontSize: 14, color: '#64748b', marginBottom: 12 },
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
    borderRadius: 20,
    paddingHorizontal: 12,
    paddingVertical: 5,
    gap: 6,
  },
  chipDot: { width: 7, height: 7, borderRadius: 4 },
  chipTexto: { fontSize: 13, fontWeight: '600' },
})
