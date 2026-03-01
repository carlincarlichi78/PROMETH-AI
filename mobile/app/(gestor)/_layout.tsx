// mobile/app/(gestor)/_layout.tsx
import { Tabs } from 'expo-router'
import { Building2, Upload, Bell } from 'lucide-react-native'

export default function GestorLayout() {
  return (
    <Tabs screenOptions={{
      headerShown: false,
      tabBarStyle: { backgroundColor: '#0f172a', borderTopColor: '#1e293b' },
      tabBarActiveTintColor: '#fbbf24',
      tabBarInactiveTintColor: '#64748b',
    }}>
      <Tabs.Screen name="index" options={{ title: 'Empresas', tabBarIcon: ({ color }) => <Building2 size={22} color={color} /> }} />
      <Tabs.Screen name="subir" options={{ title: 'Subir', tabBarIcon: ({ color }) => <Upload size={22} color={color} /> }} />
      <Tabs.Screen name="alertas" options={{ title: 'Alertas', tabBarIcon: ({ color }) => <Bell size={22} color={color} /> }} />
    </Tabs>
  )
}
