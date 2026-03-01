// mobile/hooks/useApi.ts
import { router } from 'expo-router'
import * as SecureStore from 'expo-secure-store'
import { BASE_URL } from '@/constants/api'

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = await SecureStore.getItemAsync('sfce_token')

  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  })

  if (res.status === 401) {
    await SecureStore.deleteItemAsync('sfce_token')
    router.replace('/(auth)/login')
    throw new Error('Sesión expirada')
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error((body as { detail?: string }).detail ?? `Error ${res.status}`)
  }

  return res.json()
}

export async function apiUpload<T>(
  path: string,
  formData: FormData
): Promise<T> {
  const token = await SecureStore.getItemAsync('sfce_token')
  const res = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  })
  if (res.status === 401) {
    await SecureStore.deleteItemAsync('sfce_token')
    router.replace('/(auth)/login')
    throw new Error('Sesión expirada')
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error((body as { detail?: string }).detail ?? `Error ${res.status}`)
  }
  return res.json()
}
