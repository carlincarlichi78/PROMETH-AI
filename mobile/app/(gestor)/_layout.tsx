// mobile/app/(gestor)/_layout.tsx
import { Tabs } from 'expo-router'
import { Building2, Upload, Bell } from 'lucide-react-native'

export default function GestorLayout() {
  return (
    <Tabs screenOptions={{
      headerShown: false,
      tabBarStyle: {
        backgroundColor: '#1e293b',
        borderTopWidth: 0,
        height: 76,
        paddingBottom: 12,
        paddingTop: 10,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: -4 },
        shadowOpacity: 0.3,
        shadowRadius: 12,
        elevation: 16,
      },
      tabBarActiveTintColor: '#f59e0b',
      tabBarInactiveTintColor: '#475569',
      tabBarLabelStyle: { fontSize: 13, fontWeight: '700', marginTop: 4 },
    }}>
      <Tabs.Screen
        name="index"
        options={{ title: 'Empresas', tabBarIcon: ({ color, size }) => <Building2 size={28} color={color} /> }}
      />
      <Tabs.Screen
        name="subir"
        options={{ title: 'Subir doc', tabBarIcon: ({ color, size }) => <Upload size={28} color={color} /> }}
      />
      <Tabs.Screen
        name="alertas"
        options={{ title: 'Alertas', tabBarIcon: ({ color, size }) => <Bell size={28} color={color} /> }}
      />
    </Tabs>
  )
}
