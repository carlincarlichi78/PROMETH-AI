// Tipos TypeScript — Configuracion del sistema

export interface ConfigApariencia {
  tema: 'light' | 'dark' | 'system'
  densidad: 'compacta' | 'comoda'
  idioma: string
  formato_fecha: string
  formato_numero: string
}

export interface Backup {
  id: string
  fecha: string
  tamano: string
  tipo: 'manual' | 'automatico'
}

export interface Integracion {
  nombre: string
  tipo: 'erp' | 'ocr' | 'ia' | 'email'
  estado: 'conectado' | 'desconectado' | 'error'
  url?: string
}

export interface EstadoLicencia {
  plan: string
  max_empresas: number
  max_usuarios: number
  modulos: string[]
  valida_hasta: string | null
  version: string
}

export interface Usuario {
  id: number
  email: string
  nombre: string
  rol: 'admin' | 'gestor' | 'cliente'
  activo: boolean
  empresa_id: number | null
  fecha_creacion: string
}
