// mobile/app/(empresario)/index.tsx
import { View, Text, ScrollView, ActivityIndicator } from 'react-native'
import { useQuery } from '@tanstack/react-query'
import { useAuthStore } from '@/store/auth'
import { apiFetch } from '@/hooks/useApi'

interface Resumen {
  nombre: string
  ejercicio: string
  resultado_acumulado: number
  importe_pendiente_cobro: number
  facturas_pendientes_cobro: number
  importe_pendiente_pago: number
  facturas_pendientes_pago: number
}

interface Documento {
  id: number
  nombre: string
  tipo: string
  estado: string
  fecha: string | null
}

function fmt(n: number) {
  return n.toLocaleString('es-ES', { style: 'currency', currency: 'EUR' })
}

export default function HomeEmpresario() {
  const usuario = useAuthStore((s) => s.usuario)
  const empresaId = usuario?.empresas_asignadas?.[0]

  const { data: resumen, isLoading } = useQuery({
    queryKey: ['resumen', empresaId],
    queryFn: () => apiFetch<Resumen>(`/api/portal/${empresaId}/resumen`),
    enabled: !!empresaId,
  })

  const { data: docsData } = useQuery({
    queryKey: ['documentos', empresaId],
    queryFn: () => apiFetch<{ documentos: Documento[] }>(`/api/portal/${empresaId}/documentos`),
    enabled: !!empresaId,
  })

  if (isLoading) return (
    <View className="flex-1 bg-slate-950 items-center justify-center">
      <ActivityIndicator color="#fbbf24" />
    </View>
  )

  return (
    <ScrollView className="flex-1 bg-slate-950" contentContainerClassName="p-5 gap-4">
      <View className="mt-8">
        <Text className="text-2xl font-bold text-white">{resumen?.nombre ?? 'Mi empresa'}</Text>
        <Text className="text-slate-400 text-sm">Ejercicio {resumen?.ejercicio}</Text>
      </View>

      {/* KPIs */}
      <View className="flex-row gap-3">
        <View className="flex-1 bg-slate-900 rounded-xl p-4">
          <Text className="text-xs text-slate-400">Resultado</Text>
          <Text className={`text-lg font-bold mt-1 ${(resumen?.resultado_acumulado ?? 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {fmt(resumen?.resultado_acumulado ?? 0)}
          </Text>
        </View>
        <View className="flex-1 bg-slate-900 rounded-xl p-4">
          <Text className="text-xs text-slate-400">Cobros pend.</Text>
          <Text className="text-lg font-bold mt-1 text-blue-400">{fmt(resumen?.importe_pendiente_cobro ?? 0)}</Text>
          <Text className="text-xs text-slate-500">{resumen?.facturas_pendientes_cobro} fact.</Text>
        </View>
      </View>

      {/* Documentos recientes */}
      <Text className="text-sm font-semibold text-slate-300">Documentos recientes</Text>
      {(docsData?.documentos ?? []).slice(0, 15).map((d) => (
        <View key={d.id} className="bg-slate-900 rounded-xl px-4 py-3 flex-row items-center gap-3">
          <View className="bg-slate-700 rounded-lg px-2 py-0.5">
            <Text className="text-[10px] text-slate-300 uppercase">{d.tipo}</Text>
          </View>
          <Text className="flex-1 text-slate-200 text-sm" numberOfLines={1}>{d.nombre}</Text>
          <View className={`rounded-full px-2 py-0.5 ${d.estado === 'procesado' ? 'bg-emerald-900' : 'bg-amber-900'}`}>
            <Text className={`text-[10px] ${d.estado === 'procesado' ? 'text-emerald-300' : 'text-amber-300'}`}>{d.estado}</Text>
          </View>
        </View>
      ))}
    </ScrollView>
  )
}
