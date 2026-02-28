// Tipos TypeScript — Copiloto IA

export interface DatosEnriquecidos {
  tablas?: { titulo: string; filas: Record<string, unknown>[] }[]
  charts?: { tipo: string; datos: unknown }[]
  links?: { texto: string; ruta: string }[]
  acciones?: { texto: string; accion: string }[]
}

export interface MensajeCopilot {
  rol: 'user' | 'assistant'
  contenido: string
  timestamp: string
  datos_enriquecidos?: DatosEnriquecidos
}

export interface ConversacionCopilot {
  id: number
  empresa_id: number
  titulo: string
  mensajes: MensajeCopilot[]
  fecha_creacion: string
  fecha_actualizacion: string
}

export interface ConversacionResumen {
  id: number
  titulo: string
  num_mensajes: number
  fecha_creacion: string | null
  fecha_actualizacion: string | null
}

export interface RespuestaCopilot {
  conversacion_id: number
  respuesta: string
  datos_enriquecidos: DatosEnriquecidos | null
  funciones_invocadas: string[]
}

export interface MensajeIn {
  mensaje: string
  conversacion_id?: number
}

export interface FeedbackIn {
  conversacion_id: number
  mensaje_idx: number
  valoracion: 1 | 5  // 1 = dislike, 5 = like
  correccion?: string
}
