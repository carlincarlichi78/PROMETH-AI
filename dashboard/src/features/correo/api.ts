import { api } from '@/lib/api-client'

export interface CuentaImap {
  id: number
  servidor: string
  usuario: string
  activa: boolean
  ultimo_sync?: string
}

export interface EmailProcesado {
  id: number
  asunto: string
  remitente: string
  fecha: string
  procesado: boolean
  documentos_extraidos: number
}

export interface ReglaClasificacion {
  id: number
  patron: string
  accion: string
}

export const listarCuentas = (empresaId: number) =>
  api.get<CuentaImap[]>(`/api/correo/cuentas?empresa_id=${empresaId}`)

export const crearCuenta = (datos: {
  empresa_id: number
  servidor: string
  puerto: number
  usuario: string
  password: string
  protocolo?: string
}) => api.post<{ id: number }>('/api/correo/cuentas', datos)

export const eliminarCuenta = (cuentaId: number) =>
  api.delete<void>(`/api/correo/cuentas/${cuentaId}`)

export const sincronizarCuenta = (cuentaId: number) =>
  api.post<{ procesados: number }>(`/api/correo/cuentas/${cuentaId}/sincronizar`, {})

export const listarEmails = (empresaId: number, page = 1) =>
  api.get<{ emails: EmailProcesado[]; total: number }>(
    `/api/correo/emails?empresa_id=${empresaId}&page=${page}&limit=50`
  )

export const listarReglas = (empresaId: number) =>
  api.get<ReglaClasificacion[]>(`/api/correo/reglas?empresa_id=${empresaId}`)

export const crearRegla = (datos: { empresa_id: number; patron: string; accion: string }) =>
  api.post<{ id: number }>('/api/correo/reglas', datos)

export const eliminarRegla = (reglaId: number) =>
  api.delete<void>(`/api/correo/reglas/${reglaId}`)

// Whitelist remitentes — G5
export interface Remitente {
  id: number
  email: string
  nombre?: string
}

export interface WhitelistData {
  remitentes: Remitente[]
  whitelist_activa: boolean
  aviso_primer_remitente: boolean
}

export const listarRemitentes = (empresaId: number) =>
  api.get<WhitelistData>(`/api/correo/empresas/${empresaId}/remitentes-autorizados`)

export const anadirRemitente = (empresaId: number, data: { email: string; nombre?: string }) =>
  api.post<{ id: number }>(`/api/correo/empresas/${empresaId}/remitentes-autorizados`, data)

export const eliminarRemitente = (remitenteId: number) =>
  api.delete<void>(`/api/correo/remitentes/${remitenteId}`)
