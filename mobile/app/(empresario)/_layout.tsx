// mobile/app/(empresario)/_layout.tsx
import { Tabs } from 'expo-router'
import { Home, Upload, Bell, User } from 'lucide-react-native'

export default function EmpresarioLayout() {
  return (
    <Tabs screenOptions={{
      headerShown: false,
      tabBarStyle: { backgroundColor: '#0f172a', borderTopColor: '#1e293b' },
      tabBarActiveTintColor: '#fbbf24',
      tabBarInactiveTintColor: '#64748b',
    }}>
      <Tabs.Screen name="index" options={{ title: 'Inicio', tabBarIcon: ({ color }) => <Home size={22} color={color} /> }} />
      <Tabs.Screen name="subir" options={{ title: 'Subir', tabBarIcon: ({ color }) => <Upload size={22} color={color} /> }} />
      <Tabs.Screen name="notificaciones" options={{ title: 'Alertas', tabBarIcon: ({ color }) => <Bell size={22} color={color} /> }} />
      <Tabs.Screen name="perfil" options={{ title: 'Perfil', tabBarIcon: ({ color }) => <User size={22} color={color} /> }} />
    </Tabs>
  )
}
