// mobile/hooks/usePushNotifications.ts
import { useEffect } from 'react'
import { Platform } from 'react-native'
import * as Notifications from 'expo-notifications'
import { apiFetch } from '@/hooks/useApi'
import { useAuthStore } from '@/store/auth'

Notifications.setNotificationHandler({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
  } as any),
})

export function usePushNotifications(empresaId: number | undefined) {
  const usuario = useAuthStore((s) => s.usuario)

  useEffect(() => {
    // Solo en dispositivos nativos (no web)
    if (Platform.OS === 'web' || !empresaId || !usuario) return

    const registrar = async () => {
      const { status: existente } = await Notifications.getPermissionsAsync()
      let permiso = existente
      if (existente !== 'granted') {
        const { status } = await Notifications.requestPermissionsAsync()
        permiso = status
      }
      if (permiso !== 'granted') return

      if (Platform.OS === 'android') {
        await Notifications.setNotificationChannelAsync('default', {
          name: 'SFCE',
          importance: Notifications.AndroidImportance.MAX,
          vibrationPattern: [0, 250, 250, 250],
        })
      }

      try {
        const tokenData = await Notifications.getExpoPushTokenAsync()
        await apiFetch(`/api/portal/${empresaId}/push-token`, {
          method: 'POST',
          body: JSON.stringify({
            token: tokenData.data,
            plataforma: Platform.OS,
          }),
        })
      } catch {
        // No bloquear la app si falla el registro
      }
    }

    registrar()
  }, [empresaId, usuario])
}
