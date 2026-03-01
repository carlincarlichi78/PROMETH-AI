import { useQuery } from '@tanstack/react-query'
import type { SesionSalud, SesionDetalle, Tendencias } from './types'

const BASE = '/api/salud'

async function get<T>(path: string): Promise<T> {
  const token = sessionStorage.getItem('sfce_token')
  const r = await fetch(`${BASE}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!r.ok) throw new Error(`Error ${r.status}`)
  return r.json()
}

export function useSesiones() {
  return useQuery<SesionSalud[]>({
    queryKey: ['salud', 'sesiones'],
    queryFn: () => get('/sesiones'),
  })
}

export function useSesionDetalle(id: number) {
  return useQuery<SesionDetalle>({
    queryKey: ['salud', 'sesiones', id],
    queryFn: () => get(`/sesiones/${id}`),
    enabled: id > 0,
  })
}

export function useTendencias() {
  return useQuery<Tendencias>({
    queryKey: ['salud', 'tendencias'],
    queryFn: () => get('/tendencias'),
  })
}
