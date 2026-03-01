// mobile/app/(gestor)/alertas.tsx
import { View, Text, ScrollView, ActivityIndicator } from 'react-native'
import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/hooks/useApi'
import { AlertTriangle, CheckCircle2 } from 'lucide-react-native'

interface Alerta { tipo: string; prioridad: string; titulo: string; descripcion?: string }

export default function AlertasGestor() {
  const { data, isLoading } = useQuery({
    queryKey: ['gestor-alertas'],
    queryFn: () => apiFetch<{ alertas: Alerta[] }>('/api/gestor/alertas'),
  })

  if (isLoading) return (
    <View className="flex-1 bg-slate-950 items-center justify-center">
      <ActivityIndicator color="#fbbf24" />
    </View>
  )

  const alertas = data?.alertas ?? []

  return (
    <ScrollView className="flex-1 bg-slate-950" contentContainerClassName="p-5 gap-4">
      <Text className="text-2xl font-bold text-white mt-8">Alertas</Text>
      {alertas.length === 0
        ? (
          <View className="items-center py-12 gap-3">
            <CheckCircle2 size={48} color="#34d399" />
            <Text className="text-slate-400">Todo en orden</Text>
          </View>
        )
        : alertas.map((a, i) => (
          <View key={i} className="bg-slate-900 rounded-xl p-4 gap-2">
            <View className="flex-row items-center gap-2">
              <AlertTriangle size={16} color={a.prioridad === 'alta' ? '#f87171' : '#fbbf24'} />
              <Text className="text-white font-semibold">{a.titulo}</Text>
            </View>
            {a.descripcion && <Text className="text-slate-400 text-sm">{a.descripcion}</Text>}
          </View>
        ))
      }
    </ScrollView>
  )
}
