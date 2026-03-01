// mobile/app/(gestor)/index.tsx
import { View, Text, ScrollView, ActivityIndicator } from 'react-native'
import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/hooks/useApi'

interface Empresa { id: number; nombre: string; cif: string; estado_onboarding: string }

const ESTADO_COLOR: Record<string, string> = {
  configurada:        '#34d399',
  pendiente_cliente:  '#fbbf24',
  cliente_completado: '#60a5fa',
  esqueleto:          '#94a3b8',
}

export default function EmpresasGestor() {
  const { data, isLoading } = useQuery({
    queryKey: ['gestor-resumen'],
    queryFn: () => apiFetch<{ empresas: Empresa[] }>('/api/gestor/resumen'),
  })

  if (isLoading) return (
    <View className="flex-1 bg-slate-950 items-center justify-center">
      <ActivityIndicator color="#fbbf24" />
    </View>
  )

  return (
    <ScrollView className="flex-1 bg-slate-950" contentContainerClassName="p-5 gap-3">
      <Text className="text-2xl font-bold text-white mt-8">Mis empresas</Text>
      <Text className="text-slate-400 text-sm">{data?.empresas.length ?? 0} empresas gestionadas</Text>
      {(data?.empresas ?? []).map((e) => (
        <View key={e.id} className="bg-slate-900 rounded-xl px-4 py-3 flex-row items-center gap-3">
          <View className="w-2 h-2 rounded-full" style={{ backgroundColor: ESTADO_COLOR[e.estado_onboarding] ?? '#94a3b8' }} />
          <View className="flex-1">
            <Text className="text-white font-medium">{e.nombre}</Text>
            <Text className="text-slate-400 text-xs">{e.cif}</Text>
          </View>
          {e.estado_onboarding !== 'configurada' && (
            <Text className="text-xs text-amber-400">{e.estado_onboarding.replace('_', ' ')}</Text>
          )}
        </View>
      ))}
    </ScrollView>
  )
}
