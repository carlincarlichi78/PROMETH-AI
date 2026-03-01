// mobile/app/(gestor)/_layout.tsx
import { Tabs } from 'expo-router'
import { Building2, Upload, Bell } from 'lucide-react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

export default function GestorLayout() {
  const insets = useSafeAreaInsets()
  return (
    <Tabs screenOptions={{
      headerShown: false,
      tabBarStyle: {
        backgroundColor: '#1e293b',
        borderTopWidth: 0,
        height: 60 + insets.bottom,
        paddingBottom: insets.bottom + 8,
        paddingTop: 10,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: -4 },
        shadowOpacity: 0.4,
        shadowRadius: 12,
        elevation: 20,
      },
      tabBarActiveTintColor: '#f59e0b',
      tabBarInactiveTintColor: '#475569',
      tabBarLabelStyle: { fontSize: 13, fontWeight: '700' },
    }}>
      <Tabs.Screen name="index" options={{ title: 'Empresas', tabBarIcon: ({ color }) => <Building2 size={26} color={color} /> }} />
      <Tabs.Screen name="subir" options={{ title: 'Subir doc', tabBarIcon: ({ color }) => <Upload size={26} color={color} /> }} />
      <Tabs.Screen name="alertas" options={{ title: 'Alertas', tabBarIcon: ({ color }) => <Bell size={26} color={color} /> }} />
    </Tabs>
  )
}
