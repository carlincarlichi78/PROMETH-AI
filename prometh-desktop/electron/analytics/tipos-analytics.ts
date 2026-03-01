/** Metricas agregadas del desktop */
export interface MetricasDesktop {
  certificados: MetricasCerts
  firmas: MetricasFirmas
  workflows: MetricasWorkflowsLocal
  documentales: MetricasDocumentales
  scheduler: MetricasScheduler
  notificacionesDesktop: MetricasNotificacionesDesktop
}

export interface MetricasCerts {
  totalInstalados: number
  proximosACaducar: number
  caducados: number
  certificados: Array<{
    subject: string
    fechaVencimiento: string
    diasRestantes: number
  }>
}

export interface MetricasFirmas {
  totalFirmados: number
  pendientesSync: number
  porModo: { local: number; autofirma: number }
  historial: Array<{ fecha: string; modo: string }>
}

export interface MetricasWorkflowsLocal {
  totalEjecuciones: number
  exitosas: number
  fallidas: number
  tiempoPromedioMs: number
  historial: Array<{ fecha: string; resultado: string; duracionMs: number }>
}

export interface MetricasDocumentales {
  totalDescargas: number
  exitosas: number
  fallidas: number
  porTipo: Record<string, number>
  historial: Array<{ fecha: string; tipo: string; exito: boolean }>
}

export interface MetricasScheduler {
  tareasActivas: number
  ejecucionesHoy: number
  exitosasHoy: number
  fallidasHoy: number
}

export interface MetricasNotificacionesDesktop {
  pendientes: number
  totalHoy: number
  porTipo: Record<string, number>
}

/** Serie temporal de actividad combinada */
export interface PuntoActividad {
  fecha: string
  firmas: number
  workflows: number
  descargas: number
}
