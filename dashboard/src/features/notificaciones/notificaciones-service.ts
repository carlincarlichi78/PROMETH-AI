/** Servicio de gestión de suscripciones Web Push */

const VAPID_PUBLIC_KEY = import.meta.env.VITE_VAPID_PUBLIC_KEY ?? ''

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const rawData = atob(base64)
  return Uint8Array.from([...rawData].map(c => c.charCodeAt(0)))
}

export function notificacionesSoportadas(): boolean {
  return 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window
}

export async function obtenerPermiso(): Promise<NotificationPermission> {
  if (!('Notification' in window)) return 'denied'
  return Notification.permission
}

export async function suscribirNotificaciones(token: string): Promise<boolean> {
  if (!notificacionesSoportadas()) return false

  const permiso = await Notification.requestPermission()
  if (permiso !== 'granted') return false

  try {
    const registro = await navigator.serviceWorker.ready
    const opciones: PushSubscriptionOptionsInit = { userVisibleOnly: true }
    if (VAPID_PUBLIC_KEY) {
      opciones.applicationServerKey = urlBase64ToUint8Array(VAPID_PUBLIC_KEY)
    }
    await registro.pushManager.subscribe(opciones)
    // TODO: enviar suscripcion al backend cuando el endpoint /api/notificaciones/suscribir esté disponible
    // await fetch('/api/notificaciones/suscribir', {
    //   method: 'POST',
    //   headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    //   body: JSON.stringify(suscripcion.toJSON()),
    // })
    void token // evitar warning unused
    return true
  } catch {
    return false
  }
}

export async function desuscribir(): Promise<void> {
  try {
    const registro = await navigator.serviceWorker.ready
    const suscripcion = await registro.pushManager.getSubscription()
    await suscripcion?.unsubscribe()
  } catch {
    // ignorar errores de desuscripcion
  }
}
