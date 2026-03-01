import { api } from '@/lib/api-client'

const BASE = '/api/admin'

export interface Gestoria {
  id: number
  nombre: string
  cif: string
  email_contacto: string
  activa: boolean
  plan_asesores: number
  plan_clientes_tramo: string
  fecha_alta: string | null
}

export interface CrearGestoriaDto {
  nombre: string
  email_contacto: string
  cif: string
  plan_asesores?: number
}

export const listarGestorias = () =>
  api.get<Gestoria[]>(`${BASE}/gestorias`)

export const crearGestoria = (datos: CrearGestoriaDto) =>
  api.post<Gestoria>(`${BASE}/gestorias`, datos)

export const invitarUsuarioGestoria = (
  gestoriaId: number,
  datos: { email: string; nombre: string; rol: string },
) =>
  api.post(`${BASE}/gestorias/${gestoriaId}/invitar`, datos)
