import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'

/** Estado posible de un modelo fiscal */
type EstadoModelo = 'pendiente' | 'generado' | 'presentado' | 'vencido'

/** Entrada del calendario fiscal por empresa */
interface EntradaCalendario {
  modelo: string
  nombre: string
  periodo: string
  trimestre: number | null
  anual: boolean
  fecha_limite: string
  estado: EstadoModelo
}

/** Respuesta de la API del calendario */
interface RespuestaCalendario {
  empresa_id: number
  ejercicio: number
  entradas: EntradaCalendario[]
}


/** Determina el color de la tarjeta segun estado y fecha limite */
function calcularEstadoEfectivo(entrada: EntradaCalendario, hoy: Date): EstadoModelo {
  if (entrada.estado === 'presentado') return 'presentado'
  const fechaLimite = new Date(entrada.fecha_limite)
  if (hoy > fechaLimite) return 'vencido'
  const diasRestantes = Math.ceil((fechaLimite.getTime() - hoy.getTime()) / (1000 * 60 * 60 * 24))
  if (diasRestantes <= 15) return entrada.estado === 'generado' ? 'generado' : 'pendiente'
  return entrada.estado
}

/** Clases CSS segun estado efectivo */
function clasesEstado(estadoEfectivo: EstadoModelo, estaProxima: boolean): string {
  if (estadoEfectivo === 'presentado') return 'bg-green-50 border-green-200'
  if (estadoEfectivo === 'vencido') return 'bg-red-50 border-red-200'
  if (estadoEfectivo === 'generado') return 'bg-blue-50 border-blue-200'
  if (estaProxima) return 'bg-yellow-50 border-yellow-200'
  return 'bg-white border-gray-200'
}

/** Badge de estado */
function BadgeEstado({ estado, estaProxima }: { estado: EstadoModelo; estaProxima: boolean }) {
  if (estado === 'presentado') {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
        Presentado
      </span>
    )
  }
  if (estado === 'vencido') {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
        Vencido
      </span>
    )
  }
  if (estado === 'generado') {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
        Generado
      </span>
    )
  }
  if (estaProxima) {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
        Proximo
      </span>
    )
  }
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
      Pendiente
    </span>
  )
}

/** Formatea fecha ISO a DD/MM/YYYY */
function formatearFecha(iso: string): string {
  const partes = iso.split('-')
  if (partes.length === 3) return `${partes[2]}/${partes[1]}/${partes[0]}`
  return iso
}

/** Tarjeta de un modelo fiscal dentro de un trimestre */
function TarjetaModelo({
  entrada,
  hoy,
  empresaId,
  ejercicio,
}: {
  entrada: EntradaCalendario
  hoy: Date
  empresaId: string
  ejercicio: number
}) {
  const fechaLimite = new Date(entrada.fecha_limite)
  const diasRestantes = Math.ceil((fechaLimite.getTime() - hoy.getTime()) / (1000 * 60 * 60 * 24))
  const estaProxima = diasRestantes >= 0 && diasRestantes <= 15
  const estadoEfectivo = calcularEstadoEfectivo(entrada, hoy)

  return (
    <div className={`border rounded-lg p-3 ${clasesEstado(estadoEfectivo, estaProxima)}`}>
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold text-gray-800">Mod. {entrada.modelo}</span>
            <BadgeEstado estado={estadoEfectivo} estaProxima={estaProxima} />
          </div>
          <p className="text-xs text-gray-500 mt-0.5 truncate">{entrada.nombre}</p>
          <p className="text-xs text-gray-400 mt-1 font-mono">Limite: {formatearFecha(entrada.fecha_limite)}</p>
          {estadoEfectivo !== 'presentado' && estadoEfectivo !== 'vencido' && diasRestantes >= 0 && (
            <p className={`text-xs mt-0.5 ${estaProxima ? 'text-yellow-700 font-medium' : 'text-gray-400'}`}>
              {diasRestantes} dias restantes
            </p>
          )}
        </div>
        <Link
          to={`/empresa/${empresaId}/modelos-fiscales/generar?modelo=${entrada.modelo}&periodo=${entrada.periodo}&ejercicio=${ejercicio}`}
          className="shrink-0 px-2 py-1 text-xs bg-white border border-gray-300 text-gray-700 rounded hover:bg-gray-50 transition-colors whitespace-nowrap"
          onClick={(e) => e.stopPropagation()}
        >
          Generar
        </Link>
      </div>
    </div>
  )
}

/**
 * ModelosFiscales — calendario de modelos por trimestre y anuales.
 * Ruta: /empresa/:id/modelos-fiscales
 */
export function ModelosFiscales() {
  const { id } = useParams<{ id: string }>()
  const empresaId = id ?? ''
  const anoActual = new Date().getFullYear()
  const hoy = new Date()

  const [ejercicio, setEjercicio] = useState(anoActual)
  const [calendario, setCalendario] = useState<RespuestaCalendario | null>(null)
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const cargar = async () => {
      setCargando(true)
      setError(null)
      try {
        const resp = await fetch(`/api/modelos/calendario/${empresaId}/${ejercicio}`, {
          headers: { Authorization: `Bearer ${localStorage.getItem('sfce_token') ?? ''}` },
        })
        if (!resp.ok) throw new Error(`Error HTTP ${resp.status}`)
        const datos = (await resp.json()) as RespuestaCalendario
        setCalendario(datos)
      } catch (err) {
        setCalendario(null)
        setError(err instanceof Error ? err.message : 'Error al cargar el calendario')
      } finally {
        setCargando(false)
      }
    }
    void cargar()
  }, [empresaId, ejercicio])

  /** Entradas filtradas por trimestre */
  const entradasTrimestre = (t: number): EntradaCalendario[] =>
    calendario?.entradas.filter((e) => e.trimestre === t) ?? []

  /** Entradas anuales */
  const entradasAnuales = (): EntradaCalendario[] =>
    calendario?.entradas.filter((e) => e.anual) ?? []

  /** Nombre del trimestre */
  const nombreTrimestre = (t: number): string => {
    const nombres: Record<number, string> = {
      1: 'Enero - Marzo',
      2: 'Abril - Junio',
      3: 'Julio - Septiembre',
      4: 'Octubre - Diciembre',
    }
    return nombres[t] ?? ''
  }

  /** Anos disponibles para el selector */
  const anosDisponibles = [anoActual - 1, anoActual, anoActual + 1]

  return (
    <div>
      {/* Cabecera */}
      <Link
        to={`/empresa/${empresaId}`}
        className="text-sm text-[var(--color-primary)] hover:underline mb-2 inline-block"
      >
        Volver al resumen
      </Link>
      <div className="mb-6 flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Modelos Fiscales</h1>
          <p className="text-sm text-gray-500 mt-1">Calendario de obligaciones — ejercicio {ejercicio}</p>
        </div>
        <div className="flex items-center gap-3">
          <label className="text-sm text-gray-600">Ejercicio:</label>
          <select
            value={ejercicio}
            onChange={(e) => setEjercicio(Number(e.target.value))}
            className="border border-gray-300 rounded px-3 py-1.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {anosDisponibles.map((ano) => (
              <option key={ano} value={ano}>
                {ano}
              </option>
            ))}
          </select>
          <Link
            to={`/empresa/${empresaId}/modelos-fiscales/historico`}
            className="px-4 py-2 text-sm bg-gray-100 text-gray-700 rounded hover:bg-gray-200 transition-colors"
          >
            Historico
          </Link>
        </div>
      </div>

      {/* Leyenda */}
      <div className="flex flex-wrap gap-4 mb-6 text-xs text-gray-600">
        <div className="flex items-center gap-1.5">
          <span className="inline-block w-2.5 h-2.5 rounded-full bg-green-400" />
          Presentado
        </div>
        <div className="flex items-center gap-1.5">
          <span className="inline-block w-2.5 h-2.5 rounded-full bg-blue-400" />
          Generado (pendiente presentar)
        </div>
        <div className="flex items-center gap-1.5">
          <span className="inline-block w-2.5 h-2.5 rounded-full bg-yellow-400" />
          Proximo (menos de 15 dias)
        </div>
        <div className="flex items-center gap-1.5">
          <span className="inline-block w-2.5 h-2.5 rounded-full bg-red-400" />
          Vencido
        </div>
        <div className="flex items-center gap-1.5">
          <span className="inline-block w-2.5 h-2.5 rounded-full bg-gray-300" />
          Pendiente
        </div>
      </div>

      {/* Error */}
      {error && !cargando && (
        <div className="mb-4 bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-red-700 text-sm">
          {error}
        </div>
      )}

      {cargando ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="bg-white rounded-lg shadow p-6 animate-pulse">
              <div className="h-5 bg-gray-200 rounded w-24 mb-4" />
              <div className="space-y-3">
                {[1, 2, 3].map((j) => (
                  <div key={j} className="h-14 bg-gray-100 rounded" />
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <>
          {/* Trimestres */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            {[1, 2, 3, 4].map((t) => {
              const entradas = entradasTrimestre(t)
              return (
                <div key={t} className="bg-white rounded-lg shadow p-5">
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-base font-semibold text-gray-800">T{t}</h2>
                    <span className="text-xs text-gray-400">{nombreTrimestre(t)}</span>
                  </div>
                  {entradas.length === 0 ? (
                    <p className="text-sm text-gray-400">Sin modelos en este trimestre</p>
                  ) : (
                    <div className="space-y-2">
                      {entradas.map((entrada, idx) => (
                        <TarjetaModelo
                          key={`${entrada.modelo}-${t}-${idx}`}
                          entrada={entrada}
                          hoy={hoy}
                          empresaId={empresaId}
                          ejercicio={ejercicio}
                        />
                      ))}
                    </div>
                  )}
                </div>
              )
            })}
          </div>

          {/* Anuales */}
          <div className="bg-white rounded-lg shadow p-5">
            <h2 className="text-base font-semibold text-gray-800 mb-4">Modelos Anuales</h2>
            {entradasAnuales().length === 0 ? (
              <p className="text-sm text-gray-400">Sin modelos anuales configurados</p>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {entradasAnuales().map((entrada, idx) => (
                  <TarjetaModelo
                    key={`${entrada.modelo}-anual-${idx}`}
                    entrada={entrada}
                    hoy={hoy}
                    empresaId={empresaId}
                    ejercicio={ejercicio}
                  />
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
