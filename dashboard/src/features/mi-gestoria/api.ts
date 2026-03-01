import { api } from '@/lib/api-client'

const BASE = '/api/admin'

export interface UsuarioGestoria {
  id: number
  email: string
  nombre: string
  rol: string
  activo: boolean
}

export interface InvitarGestorDto {
  nombre: string
  email: string
}

export interface ResultadoInvitacion {
  id: number
  email: string
  invitacion_token: string
  invitacion_url: string
}

export const listarMisUsuarios = (gestoriaId: number) =>
  api.get<UsuarioGestoria[]>(`${BASE}/gestorias/${gestoriaId}/usuarios`)

export const invitarGestor = (gestoriaId: number, datos: InvitarGestorDto) =>
  api.post<ResultadoInvitacion>(`${BASE}/gestorias/${gestoriaId}/invitar`, {
    ...datos,
    rol: 'gestor',
  })
