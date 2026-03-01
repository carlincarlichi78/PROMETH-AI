import { api } from '@/lib/api-client'

export interface DatosBasicosEmpresa {
  cif: string
  nombre: string
  forma_juridica: 'autonomo' | 'sl' | 'sa' | 'cb' | 'sc' | 'coop'
  territorio: 'peninsula' | 'canarias' | 'ceuta'
  regimen_iva: 'general' | 'simplificado' | 'recargo_equivalencia'
}

export interface PerfilNegocio {
  sector?: string
  empleados?: number
  facturacion_anual?: number
  descripcion?: string
}

export interface ProveedorHabitual {
  cif: string
  nombre: string
  email?: string
  subcuenta_gasto?: string
}

export interface FuenteCorreo {
  servidor: string
  puerto: number
  usuario: string
  password: string
  protocolo?: 'imap' | 'pop3'
}

export interface DatosFacturaScripts {
  idempresa_fs?: number
  codejercicio_fs?: string
}

export const crearEmpresa = (datos: DatosBasicosEmpresa) =>
  api.post<{ id: number; cif: string }>('/api/empresas', datos)

export const actualizarPerfil = (empresaId: number, perfil: PerfilNegocio) =>
  api.patch<{ ok: boolean }>(`/api/empresas/${empresaId}/perfil`, perfil)

export const actualizarFacturaScripts = (empresaId: number, datos: DatosFacturaScripts) =>
  api.patch<{ ok: boolean }>(`/api/empresas/${empresaId}/perfil`, datos)

export const anadirProveedor = (empresaId: number, proveedor: ProveedorHabitual) =>
  api.post<{ id: number }>(`/api/empresas/${empresaId}/proveedores-habituales`, proveedor)

export const anadirFuenteCorreo = (empresaId: number, fuente: FuenteCorreo) =>
  api.post<{ id: number }>(`/api/empresas/${empresaId}/fuentes`, fuente)
