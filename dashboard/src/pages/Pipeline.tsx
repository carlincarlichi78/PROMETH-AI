import { useCallback, useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useWebSocket } from '../hooks/useWebSocket'

/** Evento de progreso del pipeline */
interface EventoProgreso {
  fase: string
  documento: string
  total: number
  procesados: number
}

/** Evento de documento procesado */
interface EventoDocProcesado {
  id: number
  tipo_doc: string
  estado: string
}

/** Entrada en el log de actividad */
interface EntradaLog {
  id: number
  timestamp: string
  mensaje: string
  tipo: 'progreso' | 'procesado' | 'info'
}

/**
 * Pipeline de Procesamiento — vista en tiempo real via WebSocket.
 * Muestra progreso de fases, documento actual y log de actividad.
 */
export function Pipeline() {
  const { id } = useParams()
  const empresaId = Number(id)
  const canal = `empresa_${empresaId}`
  const { conectado, addEventListener } = useWebSocket(canal)

  const [progreso, setProgreso] = useState<EventoProgreso | null>(null)
  const [logEventos, setLogEventos] = useState<EntradaLog[]>([])
  const contadorRef = useRef(0)

  /** Agrega entrada al log (max 20 entradas) */
  const agregarAlLog = useCallback((mensaje: string, tipo: EntradaLog['tipo']) => {
    contadorRef.current += 1
    const entrada: EntradaLog = {
      id: contadorRef.current,
      timestamp: new Date().toLocaleTimeString('es-ES'),
      mensaje,
      tipo,
    }
    setLogEventos((prev) => [entrada, ...prev].slice(0, 20))
  }, [])

  useEffect(() => {
    const limpiarProgreso = addEventListener('pipeline_progreso', (datos) => {
      const evento = datos as EventoProgreso
      setProgreso(evento)
      agregarAlLog(
        `Fase "${evento.fase}" — ${evento.documento} (${evento.procesados}/${evento.total})`,
        'progreso'
      )
    })

    const limpiarProcesado = addEventListener('documento_procesado', (datos) => {
      const evento = datos as EventoDocProcesado
      agregarAlLog(
        `Documento #${evento.id} (${evento.tipo_doc}) — ${evento.estado}`,
        'procesado'
      )
    })

    return () => {
      limpiarProgreso()
      limpiarProcesado()
    }
  }, [addEventListener, agregarAlLog])

  /** Porcentaje de progreso */
  const porcentaje = progreso && progreso.total > 0
    ? Math.round((progreso.procesados / progreso.total) * 100)
    : 0

  /** Nombre legible de la fase */
  const nombreFase = (fase: string): string => {
    const nombres: Record<string, string> = {
      intake: 'Ingesta OCR',
      pre_validation: 'Pre-validacion',
      registration: 'Registro en FS',
      asientos: 'Generacion asientos',
      correction: 'Correcciones',
      cross_validation: 'Validacion cruzada',
      output: 'Salida y reportes',
    }
    return nombres[fase] ?? fase
  }

  /** Color de la entrada de log segun tipo */
  const colorEntrada = (tipo: EntradaLog['tipo']): string => {
    switch (tipo) {
      case 'progreso':
        return 'text-blue-600'
      case 'procesado':
        return 'text-green-600'
      case 'info':
        return 'text-gray-500'
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Pipeline de Procesamiento</h1>
        <div className="flex items-center gap-2">
          <span
            className={`inline-block w-2.5 h-2.5 rounded-full ${
              conectado ? 'bg-green-500' : 'bg-red-500'
            }`}
          />
          <span className="text-sm text-gray-500">
            {conectado ? 'Conectado' : 'Desconectado'}
          </span>
        </div>
      </div>

      {/* Tarjeta de progreso */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-700 mb-4">Progreso actual</h2>

        {progreso ? (
          <div className="space-y-4">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600">
                Fase: <span className="font-medium text-gray-800">{nombreFase(progreso.fase)}</span>
              </span>
              <span className="text-gray-500">
                {progreso.procesados} / {progreso.total}
              </span>
            </div>

            {/* Barra de progreso */}
            <div className="w-full bg-gray-200 rounded-full h-3">
              <div
                className="bg-blue-600 h-3 rounded-full transition-all duration-300"
                style={{ width: `${porcentaje}%` }}
              />
            </div>

            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-500">
                Documento: <span className="font-mono text-gray-700">{progreso.documento}</span>
              </span>
              <span className="font-medium text-blue-600">{porcentaje}%</span>
            </div>
          </div>
        ) : (
          <div className="text-center py-8">
            <p className="text-gray-400">
              {conectado
                ? 'Esperando inicio de pipeline...'
                : 'Conectando al servidor...'}
            </p>
            <p className="text-gray-300 text-sm mt-2">
              Los eventos apareceran aqui en tiempo real
            </p>
          </div>
        )}
      </div>

      {/* Fases del pipeline */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-700 mb-4">Fases</h2>
        <div className="grid grid-cols-7 gap-2">
          {['intake', 'pre_validation', 'registration', 'asientos', 'correction', 'cross_validation', 'output'].map(
            (fase) => {
              const esActual = progreso?.fase === fase
              const faseIndex = ['intake', 'pre_validation', 'registration', 'asientos', 'correction', 'cross_validation', 'output'].indexOf(fase)
              const progresoIndex = progreso
                ? ['intake', 'pre_validation', 'registration', 'asientos', 'correction', 'cross_validation', 'output'].indexOf(progreso.fase)
                : -1
              const completada = progreso !== null && faseIndex < progresoIndex

              return (
                <div
                  key={fase}
                  className={`px-3 py-2 rounded-md text-center text-xs font-medium transition-colors ${
                    esActual
                      ? 'bg-blue-100 text-blue-800 ring-2 ring-blue-300'
                      : completada
                        ? 'bg-green-50 text-green-700'
                        : 'bg-gray-50 text-gray-400'
                  }`}
                >
                  {nombreFase(fase)}
                </div>
              )
            }
          )}
        </div>
      </div>

      {/* Log de actividad */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-700 mb-4">
          Log de actividad
          {logEventos.length > 0 && (
            <span className="text-sm font-normal text-gray-400 ml-2">
              ({logEventos.length} evento{logEventos.length !== 1 ? 's' : ''})
            </span>
          )}
        </h2>

        {logEventos.length === 0 ? (
          <p className="text-gray-400 text-sm text-center py-4">
            Sin eventos registrados
          </p>
        ) : (
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {logEventos.map((entrada) => (
              <div
                key={entrada.id}
                className="flex items-start gap-3 text-sm py-1.5 border-b border-gray-50 last:border-0"
              >
                <span className="text-gray-400 font-mono text-xs shrink-0 mt-0.5">
                  {entrada.timestamp}
                </span>
                <span className={colorEntrada(entrada.tipo)}>
                  {entrada.mensaje}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
