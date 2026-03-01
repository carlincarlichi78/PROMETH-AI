/** Evento de telemetria anonimizada */
export interface EventoLocal {
  evento: string
  propiedades?: Record<string, unknown>
}

/** Configuracion del cliente de telemetria */
export interface ConfigTelemetria {
  /** URL del endpoint API (ej: https://carloscanetegomez.dev/certigestor/api/telemetria) */
  apiUrl: string
  /** Intervalo de flush en ms (default: 5 minutos) */
  intervaloFlush: number
  /** Si la telemetria esta desactivada por el usuario */
  optOut: boolean
}

/** Estado del cliente */
export interface EstadoTelemetria {
  activa: boolean
  eventosEnCola: number
  ultimoEnvio: string | null
}
