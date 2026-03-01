// mobile/app/(empresario)/perfil.tsx
import { View, Text, TouchableOpacity } from 'react-native'
import { router } from 'expo-router'
import { useAuthStore } from '@/store/auth'

const TIER_LABEL: Record<string, string> = { basico: 'Básico', pro: 'Pro', premium: 'Premium' }
const TIER_COLOR: Record<string, string> = { basico: '#94a3b8', pro: '#60a5fa', premium: '#fbbf24' }

export default function PerfilEmpresario() {
  const { usuario, cerrarSesion } = useAuthStore()

  const handleLogout = async () => {
    await cerrarSesion()
    router.replace('/(auth)/login')
  }

  return (
    <View className="flex-1 bg-slate-950 p-5 mt-12 gap-4">
      <Text className="text-2xl font-bold text-white">Mi perfil</Text>

      <View className="bg-slate-900 rounded-2xl p-5 gap-3">
        <View>
          <Text className="text-xs text-slate-400">Nombre</Text>
          <Text className="text-white font-medium mt-0.5">{usuario?.nombre}</Text>
        </View>
        <View>
          <Text className="text-xs text-slate-400">Email</Text>
          <Text className="text-white mt-0.5">{usuario?.email}</Text>
        </View>
        <View>
          <Text className="text-xs text-slate-400">Plan</Text>
          <Text style={{ color: TIER_COLOR[usuario?.plan_tier ?? 'basico'] }} className="font-semibold mt-0.5">
            {TIER_LABEL[usuario?.plan_tier ?? 'basico'] ?? 'Básico'}
          </Text>
        </View>
      </View>

      <TouchableOpacity
        className="bg-red-900/50 border border-red-700 rounded-xl py-4 items-center"
        onPress={handleLogout}
      >
        <Text className="text-red-300 font-medium">Cerrar sesión</Text>
      </TouchableOpacity>
    </View>
  )
}
