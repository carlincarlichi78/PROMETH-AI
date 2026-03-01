// mobile/app/(empresario)/notificaciones.tsx
import { View, Text, ScrollView, ActivityIndicator } from 'react-native'
import { useQuery } from '@tanstack/react-query'
import { useAuthStore } from '@/store/auth'
import { apiFetch } from '@/hooks/useApi'
import { AlertCircle, Info, CheckCircle } from 'lucide-react-native'

interface Notificacion {
  tipo: string
  prioridad: string
  titulo: string
  descripcion?: string
}

const PRIORIDAD_COLOR: Record<string, string> = { alta: '#f87171', media: '#fbbf24', baja: '#94a3b8' }
const PRIORIDAD_ICON: Record<string, typeof AlertCircle> = {
  alta: AlertCircle,
  media: Info,
  baja: CheckCircle,
}

export default function NotificacionesEmpresario() {
  const usuario = useAuthStore((s) => s.usuario)
  const empresaId = usuario?.empresas_asignadas?.[0]

  const { data, isLoading } = useQuery({
    queryKey: ['notificaciones', empresaId],
    queryFn: () => apiFetch<{ notificaciones: Notificacion[] }>(`/api/portal/${empresaId}/notificaciones`),
    enabled: !!empresaId,
  })

  if (isLoading) return (
    <View className="flex-1 bg-slate-950 items-center justify-center">
      <ActivityIndicator color="#fbbf24" />
    </View>
  )

  const notificaciones = data?.notificaciones ?? []

  return (
    <ScrollView className="flex-1 bg-slate-950" contentContainerClassName="p-5 gap-4">
      <Text className="text-2xl font-bold text-white mt-8">Notificaciones</Text>
      {notificaciones.length === 0
        ? <Text className="text-slate-400 text-center py-8">Sin notificaciones pendientes</Text>
        : notificaciones.map((n, i) => {
            const Icon = PRIORIDAD_ICON[n.prioridad] ?? Info
            return (
              <View key={i} className="bg-slate-900 rounded-xl p-4 flex-row gap-3">
                <Icon size={20} color={PRIORIDAD_COLOR[n.prioridad] ?? '#94a3b8'} />
                <View className="flex-1">
                  <Text className="text-white font-medium">{n.titulo}</Text>
                  {n.descripcion && <Text className="text-slate-400 text-sm mt-0.5">{n.descripcion}</Text>}
                </View>
              </View>
            )
          })
      }
    </ScrollView>
  )
}
