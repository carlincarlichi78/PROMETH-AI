import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useApi } from '../hooks/useApi'

/** Datos de un plazo fiscal devuelto por la API */
interface PlazoFiscal {
  modelo: string
  nombre: string
  inicio?: string
  fin?: string
  fecha_limite?: string
  trimestre: number | null
  anual: boolean
}

/** Respuesta de la API del calendario */
interface RespuestaCalendarioFiscal {
  empresa_id: number
  ejercicio: number
  plazos?: PlazoFiscal[]
  entradas?: PlazoFiscal[]
}

/**
 * Calendario Fiscal — plazos trimestrales y anuales.
 * Muestra tarjetas por trimestre con codigo de colores.
 * Conectado a /api/modelos/calendario/:empresaId/:ejercicio
 */
export function Calendario() {
  const { empresaId } = useParams<{ empresaId: string }>()
  const { fetchConAuth } = useApi()
  const anoActual = new Date().getFullYear()
  const hoy = new Date()

  const [plazos, setPlazos] = useState<PlazoFiscal[]>([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [ejercicio, setEjercicio] = useState(anoActual)

  useEffect(() => {
    const cargar = async () => {
      setCargando(true)
      setError(null)
      try {
        const id = empresaId ?? '1'
        const datos = await fetchConAuth<RespuestaCalendarioFiscal>(`/api/modelos/calendario/${id}/${ejercicio}`)
        // La API puede devolver el listado en "plazos" o "entradas"
        const lista = datos.plazos ?? datos.entradas ?? []
        setPlazos(lista)
      } catch (err) {
        setPlazos([])
        setError(err instanceof Error ? err.message : 'Error al cargar el calendario')
      } finally {
        setCargando(false)
      }
    }
    void cargar()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [empresaId, ejercicio])

  /** Determina el estado del plazo segun la fecha actual */
  const estadoPlazo = (plazo: PlazoFiscal): 'proximo' | 'pasado' | 'vencido' => {
    // Soporte para inicio/fin (formato dd/mm) o fecha_limite (formato ISO)
    if (plazo.inicio && plazo.fin) {
      const [diaI, mesI] = plazo.inicio.split('/')
      const [diaF, mesF] = plazo.fin.split('/')
      const inicio = new Date(anoActual, Number(mesI) - 1, Number(diaI))
      const fin = new Date(anoActual, Number(mesF) - 1, Number(diaF))
      if (hoy > fin) return 'pasado'
      if (hoy >= inicio && hoy <= fin) return 'proximo'
      const diasHastaInicio = Math.ceil((inicio.getTime() - hoy.getTime()) / (1000 * 60 * 60 * 24))
      if (diasHastaInicio <= 30) return 'proximo'
      return 'pasado'
    }
    if (plazo.fecha_limite) {
      const fin = new Date(plazo.fecha_limite)
      if (hoy > fin) return 'vencido'
      const diasRestantes = Math.ceil((fin.getTime() - hoy.getTime()) / (1000 * 60 * 60 * 24))
      if (diasRestantes <= 15) return 'proximo'
      return 'pasado'
    }
    return 'pasado'
  }

  /** Colores segun estado */
  const colorEstado = (estado: 'proximo' | 'pasado' | 'vencido'): string => {
    switch (estado) {
      case 'proximo':
        return 'bg-yellow-50 border-yellow-200 text-yellow-800'
      case 'pasado':
        return 'bg-green-50 border-green-200 text-green-700'
      case 'vencido':
        return 'bg-red-50 border-red-200 text-red-700'
    }
  }

  /** Color del punto indicador */
  const colorPunto = (estado: 'proximo' | 'pasado' | 'vencido'): string => {
    switch (estado) {
      case 'proximo':
        return 'bg-yellow-400'
      case 'pasado':
        return 'bg-green-400'
      case 'vencido':
        return 'bg-red-400'
    }
  }

  /** Plazos trimestrales agrupados */
  const plazosPorTrimestre = (trimestre: number): PlazoFiscal[] => {
    return plazos.filter((p) => p.trimestre === trimestre)
  }

  /** Plazos anuales en un trimestre determinado segun mes de inicio */
  const plazosAnualesEnTrimestre = (trimestre: number): PlazoFiscal[] => {
    return plazos.filter((p) => {
      if (!p.anual) return false
      // Derivar mes de inicio desde inicio (dd/mm) o fecha_limite (ISO)
      let mes = 0
      if (p.inicio) {
        mes = Number(p.inicio.split('/')[1])
      } else if (p.fecha_limite) {
        mes = new Date(p.fecha_limite).getMonth() + 1
      }
      if (trimestre === 1 && mes >= 1 && mes <= 3) return true
      if (trimestre === 2 && mes >= 4 && mes <= 6) return true
      if (trimestre === 3 && mes >= 7 && mes <= 9) return true
      if (trimestre === 4 && mes >= 10 && mes <= 12) return true
      return false
    })
  }

  /** Nombre del trimestre */
  const nombreTrimestre = (t: number): string => {
    const periodos: Record<number, string> = {
      1: 'Enero - Marzo',
      2: 'Abril - Junio',
      3: 'Julio - Septiembre',
      4: 'Octubre - Diciembre',
    }
    return periodos[t] ?? ''
  }

  /** Texto de fechas del plazo */
  const textoFechas = (plazo: PlazoFiscal): string => {
    if (plazo.inicio && plazo.fin) return `${plazo.inicio} - ${plazo.fin}`
    if (plazo.fecha_limite) {
      const partes = plazo.fecha_limite.split('-')
      return partes.length === 3 ? `Limite: ${partes[2]}/${partes[1]}/${partes[0]}` : plazo.fecha_limite
    }
    return ''
  }

  return (
    <div>
      <div className="mb-6 flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Calendario Fiscal</h1>
          <p className="text-sm text-gray-500 mt-1">Plazos de presentacion {ejercicio}</p>
        </div>
        <div className="flex items-center gap-3">
          <label className="text-sm text-gray-600">Ejercicio:</label>
          <select
            value={ejercicio}
            onChange={(e) => setEjercicio(Number(e.target.value))}
            className="border border-gray-300 rounded px-3 py-1.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {[anoActual - 1, anoActual, anoActual + 1].map((ano) => (
              <option key={ano} value={ano}>{ano}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Leyenda */}
      <div className="flex gap-6 mb-6 text-xs text-gray-600">
        <div className="flex items-center gap-1.5">
          <span className="inline-block w-2.5 h-2.5 rounded-full bg-green-400" />
          Presentado / futuro
        </div>
        <div className="flex items-center gap-1.5">
          <span className="inline-block w-2.5 h-2.5 rounded-full bg-yellow-400" />
          Proximo / en plazo
        </div>
        <div className="flex items-center gap-1.5">
          <span className="inline-block w-2.5 h-2.5 rounded-full bg-red-400" />
          Vencido
        </div>
      </div>

      {/* Error */}
      {error && !cargando && (
        <div className="mb-4 bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* Loading skeleton */}
      {cargando && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="bg-white rounded-lg shadow p-6 animate-pulse">
              <div className="h-5 bg-gray-200 rounded w-24 mb-4" />
              <div className="space-y-2">
                {[1, 2, 3].map((j) => (
                  <div key={j} className="h-8 bg-gray-100 rounded" />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Tarjetas por trimestre */}
      {!cargando && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {[1, 2, 3, 4].map((trimestre) => {
            const trimestrales = plazosPorTrimestre(trimestre)
            const anuales = plazosAnualesEnTrimestre(trimestre)
            const todosPlazos = [...trimestrales, ...anuales]

            return (
              <div key={trimestre} className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-semibold text-gray-800">T{trimestre}</h2>
                  <span className="text-sm text-gray-400">{nombreTrimestre(trimestre)}</span>
                </div>

                {todosPlazos.length === 0 ? (
                  <p className="text-sm text-gray-400">Sin plazos en este trimestre</p>
                ) : (
                  <div className="space-y-2">
                    {todosPlazos.map((plazo, idx) => {
                      const estado = estadoPlazo(plazo)
                      return (
                        <div
                          key={`${plazo.modelo}-${idx}`}
                          className={`flex items-center justify-between px-3 py-2 rounded-md border text-sm ${colorEstado(estado)}`}
                        >
                          <div className="flex items-center gap-2">
                            <span className={`inline-block w-2 h-2 rounded-full ${colorPunto(estado)}`} />
                            <span className="font-medium">Mod. {plazo.modelo}</span>
                            <span className="text-xs opacity-75">
                              {plazo.anual ? '(anual)' : ''}
                            </span>
                          </div>
                          <span className="text-xs font-mono">
                            {textoFechas(plazo)}
                          </span>
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
