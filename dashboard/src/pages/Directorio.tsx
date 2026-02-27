import { useState, useMemo, useEffect } from 'react'
import { useApi } from '../hooks/useApi'

/** Entidad del directorio de empresas y personas */
interface EntidadDirectorio {
  id: number
  cif: string | null
  nombre: string
  nombre_comercial: string | null
  pais: string
  tipo_persona: 'fisica' | 'juridica' | null
  validado_aeat: boolean
  validado_vies: boolean
  fecha_alta: string
  aliases: string[]
}

/** Overlay empresa-especifico para una entidad */
interface OverlayEmpresa {
  id: number
  empresa_nombre: string
  tipo: 'proveedor' | 'cliente'
  subcuenta_gasto: string
  codimpuesto: string
  regimen: string
}

/** Datos del panel de detalle al hacer click en una fila */
interface DetalleEntidad {
  entidad: EntidadDirectorio
  overlays: OverlayEmpresa[]
}

/** Formulario para nueva entidad */
interface FormNuevaEntidad {
  cif: string
  nombre: string
  nombre_comercial: string
  pais: string
  tipo_persona: 'fisica' | 'juridica' | ''
}

/** Opciones de pais para el filtro */
const FILTROS_PAIS = [
  { valor: 'todos', etiqueta: 'Todos los paises' },
  { valor: 'ESP', etiqueta: 'Espana (ESP)' },
  { valor: 'UE', etiqueta: 'Union Europea' },
  { valor: 'otros', etiqueta: 'Otros' },
]

/** Paises de la UE (sin Espana) */
const PAISES_UE = new Set([
  'AUT', 'BEL', 'BGR', 'CYP', 'CZE', 'DEU', 'DNK', 'EST', 'FIN', 'FRA',
  'GRC', 'HRV', 'HUN', 'IRL', 'ITA', 'LTU', 'LUX', 'LVA', 'MLT', 'NLD',
  'POL', 'PRT', 'ROU', 'SVK', 'SVN', 'SWE',
])

/** Badge de validacion */
function BadgeValidacion({ validado, etiqueta }: { validado: boolean; etiqueta: string }) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
        validado
          ? 'bg-green-100 text-green-700'
          : 'bg-gray-100 text-gray-500'
      }`}
    >
      {validado ? '✓' : '—'} {etiqueta}
    </span>
  )
}

/** Badge de tipo de persona */
function BadgeTipoPersona({ tipo }: { tipo: 'fisica' | 'juridica' | null }) {
  if (!tipo) return <span className="text-gray-300 text-xs">—</span>
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
        tipo === 'juridica'
          ? 'bg-blue-100 text-blue-700'
          : 'bg-purple-100 text-purple-700'
      }`}
    >
      {tipo === 'juridica' ? 'Juridica' : 'Fisica'}
    </span>
  )
}

/**
 * Directorio — vista global de entidades (proveedores/clientes) con validacion AEAT/VIES.
 * Ruta global /directorio — no requiere empresa seleccionada.
 */
export function Directorio() {
  const { fetchConAuth } = useApi()

  const [entidades, setEntidades] = useState<EntidadDirectorio[]>([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busqueda, setBusqueda] = useState('')
  const [filtroPais, setFiltroPais] = useState('todos')
  const [filtroTipoPersona, setFiltroTipoPersona] = useState('todos')
  const [detalle, setDetalle] = useState<DetalleEntidad | null>(null)
  const [verificando, setVerificando] = useState<number | null>(null)
  const [modalAbierto, setModalAbierto] = useState(false)
  const [mensajeExito, setMensajeExito] = useState<string | null>(null)
  const [formNueva, setFormNueva] = useState<FormNuevaEntidad>({
    cif: '',
    nombre: '',
    nombre_comercial: '',
    pais: 'ESP',
    tipo_persona: '',
  })

  const cargarEntidades = async () => {
    setCargando(true)
    setError(null)
    try {
      const datos = await fetchConAuth<EntidadDirectorio[]>('/api/directorio/')
      setEntidades(datos)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al cargar directorio')
    } finally {
      setCargando(false)
    }
  }

  useEffect(() => {
    void cargarEntidades()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  /** Filtra entidades segun busqueda y filtros activos */
  const entidadesFiltradas = useMemo(() => {
    return entidades.filter((e) => {
      // Filtro busqueda por CIF o nombre
      if (busqueda.trim()) {
        const termino = busqueda.trim().toLowerCase()
        const coincide =
          e.cif?.toLowerCase().includes(termino) ||
          e.nombre.toLowerCase().includes(termino) ||
          e.nombre_comercial?.toLowerCase().includes(termino) ||
          e.aliases.some((a) => a.toLowerCase().includes(termino))
        if (!coincide) return false
      }

      // Filtro por pais
      if (filtroPais !== 'todos') {
        if (filtroPais === 'ESP' && e.pais !== 'ESP') return false
        if (filtroPais === 'UE' && !PAISES_UE.has(e.pais)) return false
        if (filtroPais === 'otros' && (e.pais === 'ESP' || PAISES_UE.has(e.pais))) return false
      }

      // Filtro por tipo de persona
      if (filtroTipoPersona !== 'todos' && e.tipo_persona !== filtroTipoPersona) return false

      return true
    })
  }, [entidades, busqueda, filtroPais, filtroTipoPersona])

  /** Abre el panel de detalle para una entidad y carga sus overlays */
  const abrirDetalle = async (entidad: EntidadDirectorio) => {
    setDetalle({ entidad, overlays: [] })
    try {
      const overlays = await fetchConAuth<OverlayEmpresa[]>(`/api/directorio/${entidad.id}/overlays`)
      setDetalle({ entidad, overlays })
    } catch {
      // Si no hay overlays o el endpoint devuelve 404, mostrar lista vacia
      setDetalle({ entidad, overlays: [] })
    }
  }

  /** Verifica la entidad contra AEAT/VIES via API */
  const verificarEntidad = async (entidadId: number) => {
    setVerificando(entidadId)
    try {
      const resultado = await fetchConAuth<EntidadDirectorio>(`/api/directorio/${entidadId}/verificar`)
      setEntidades((prev) =>
        prev.map((e) => (e.id === entidadId ? { ...e, ...resultado } : e))
      )
      // Actualizar detalle si esta abierto
      if (detalle?.entidad.id === entidadId) {
        setDetalle((prev) => (prev ? { ...prev, entidad: { ...prev.entidad, ...resultado } } : null))
      }
      setMensajeExito('Verificacion completada')
      setTimeout(() => setMensajeExito(null), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al verificar entidad')
      setTimeout(() => setError(null), 4000)
    } finally {
      setVerificando(null)
    }
  }

  /** Guarda una nueva entidad via API */
  const guardarNuevaEntidad = async () => {
    if (!formNueva.nombre.trim()) return
    const datos = {
      cif: formNueva.cif.trim() || null,
      nombre: formNueva.nombre.trim().toUpperCase(),
      nombre_comercial: formNueva.nombre_comercial.trim() || null,
      pais: formNueva.pais,
      tipo_persona: (formNueva.tipo_persona as 'fisica' | 'juridica') || null,
    }
    try {
      const nueva = await fetchConAuth<EntidadDirectorio>('/api/directorio/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: datos,
      })
      setEntidades((prev) => [...prev, nueva])
      setModalAbierto(false)
      setFormNueva({ cif: '', nombre: '', nombre_comercial: '', pais: 'ESP', tipo_persona: '' })
      setMensajeExito('Entidad creada correctamente')
      setTimeout(() => setMensajeExito(null), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al crear entidad')
      setTimeout(() => setError(null), 4000)
    }
  }

  /** Formatea la fecha de alta */
  const formatearFecha = (fecha: string): string => {
    const [anio, mes, dia] = fecha.split('-')
    return `${dia}/${mes}/${anio}`
  }

  return (
    <div>
      {/* Cabecera */}
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Directorio de Entidades</h1>
          <p className="text-sm text-gray-500 mt-1">
            {entidades.length} entidad{entidades.length !== 1 ? 'es' : ''} registrada{entidades.length !== 1 ? 's' : ''}{' '}
            &middot; {entidadesFiltradas.length} visible{entidadesFiltradas.length !== 1 ? 's' : ''}
          </p>
        </div>
        <button
          onClick={() => setModalAbierto(true)}
          className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 transition-colors"
        >
          + Nueva entidad
        </button>
      </div>

      {/* Estado de carga */}
      {cargando && (
        <div className="bg-white rounded-lg shadow border border-gray-200 p-5 animate-pulse">
          <div className="h-5 bg-gray-200 rounded w-3/4 mb-3" />
          <div className="h-4 bg-gray-200 rounded w-1/3 mb-3" />
          <div className="h-4 bg-gray-200 rounded w-1/2" />
        </div>
      )}

      {/* Error */}
      {error && !cargando && (
        <div className="mb-4 bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-700 mb-2">{error}</p>
          <button
            onClick={() => void cargarEntidades()}
            className="px-4 py-2 text-sm bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
          >
            Reintentar
          </button>
        </div>
      )}

      {/* Mensaje de exito */}
      {mensajeExito && (
        <div className="mb-4 bg-green-50 border border-green-200 rounded-lg px-4 py-3 text-green-700 text-sm">
          {mensajeExito}
        </div>
      )}

      {!cargando && (
        <>
          {/* Barra de busqueda y filtros */}
          <div className="mb-4 flex flex-wrap gap-3">
            <input
              type="text"
              placeholder="Buscar por CIF, nombre o alias..."
              value={busqueda}
              onChange={(e) => setBusqueda(e.target.value)}
              className="flex-1 min-w-48 px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <select
              value={filtroPais}
              onChange={(e) => setFiltroPais(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white"
            >
              {FILTROS_PAIS.map((f) => (
                <option key={f.valor} value={f.valor}>
                  {f.etiqueta}
                </option>
              ))}
            </select>
            <select
              value={filtroTipoPersona}
              onChange={(e) => setFiltroTipoPersona(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white"
            >
              <option value="todos">Todos los tipos</option>
              <option value="juridica">Persona juridica</option>
              <option value="fisica">Persona fisica</option>
            </select>
          </div>

          {/* Layout principal: tabla + panel detalle */}
          <div className="flex gap-4">
            {/* Tabla de entidades */}
            <div className={`${detalle ? 'flex-1' : 'w-full'} bg-white rounded-lg shadow overflow-hidden`}>
              {entidadesFiltradas.length === 0 ? (
                <div className="p-12 text-center">
                  <p className="text-gray-400 text-lg">No se encontraron entidades</p>
                  <p className="text-gray-300 text-sm mt-2">Prueba con otros terminos de busqueda o filtros</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 border-b border-gray-200">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                          CIF
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                          Nombre
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                          Pais
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                          Tipo
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                          Validacion
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                          Fecha alta
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                          Acciones
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {entidadesFiltradas.map((entidad) => (
                        <tr
                          key={entidad.id}
                          onClick={() => void abrirDetalle(entidad)}
                          className={`cursor-pointer transition-colors hover:bg-blue-50 ${
                            detalle?.entidad.id === entidad.id ? 'bg-blue-50' : ''
                          }`}
                        >
                          <td className="px-4 py-3 font-mono text-gray-700">
                            {entidad.cif ?? <span className="text-gray-300 italic">sin CIF</span>}
                          </td>
                          <td className="px-4 py-3">
                            <div className="font-medium text-gray-800">{entidad.nombre}</div>
                            {entidad.nombre_comercial && (
                              <div className="text-xs text-gray-400">{entidad.nombre_comercial}</div>
                            )}
                          </td>
                          <td className="px-4 py-3">
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-mono bg-gray-100 text-gray-700">
                              {entidad.pais}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <BadgeTipoPersona tipo={entidad.tipo_persona} />
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex flex-wrap gap-1">
                              {entidad.pais === 'ESP' && (
                                <BadgeValidacion validado={entidad.validado_aeat} etiqueta="AEAT" />
                              )}
                              {PAISES_UE.has(entidad.pais) && (
                                <BadgeValidacion validado={entidad.validado_vies} etiqueta="VIES" />
                              )}
                              {entidad.pais !== 'ESP' && !PAISES_UE.has(entidad.pais) && (
                                <span className="text-xs text-gray-300">N/A</span>
                              )}
                            </div>
                          </td>
                          <td className="px-4 py-3 text-gray-500 text-xs">
                            {formatearFecha(entidad.fecha_alta)}
                          </td>
                          <td className="px-4 py-3">
                            <button
                              onClick={(e) => {
                                e.stopPropagation()
                                void verificarEntidad(entidad.id)
                              }}
                              disabled={verificando === entidad.id}
                              className="px-3 py-1 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                            >
                              {verificando === entidad.id ? 'Verificando...' : 'Verificar'}
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Panel de detalle */}
            {detalle && (
              <div className="w-80 shrink-0 bg-white rounded-lg shadow p-5">
                {/* Cabecera detalle */}
                <div className="flex items-start justify-between mb-4">
                  <h2 className="text-sm font-semibold text-gray-800 leading-snug pr-2">
                    {detalle.entidad.nombre}
                  </h2>
                  <button
                    onClick={() => setDetalle(null)}
                    className="text-gray-400 hover:text-gray-600 text-lg leading-none shrink-0"
                    aria-label="Cerrar detalle"
                  >
                    &times;
                  </button>
                </div>

                {/* Datos principales */}
                <div className="space-y-2 text-sm mb-5">
                  <div className="flex justify-between">
                    <span className="text-gray-500">CIF</span>
                    <span className="font-mono text-gray-800">
                      {detalle.entidad.cif ?? <span className="italic text-gray-400">sin CIF</span>}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Pais</span>
                    <span className="font-mono text-gray-800">{detalle.entidad.pais}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Tipo</span>
                    <BadgeTipoPersona tipo={detalle.entidad.tipo_persona} />
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Alta</span>
                    <span className="text-gray-800">{formatearFecha(detalle.entidad.fecha_alta)}</span>
                  </div>
                  {detalle.entidad.nombre_comercial && (
                    <div className="flex justify-between">
                      <span className="text-gray-500">Comercial</span>
                      <span className="text-gray-800">{detalle.entidad.nombre_comercial}</span>
                    </div>
                  )}
                </div>

                {/* Validaciones */}
                <div className="mb-5">
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                    Validaciones
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {detalle.entidad.pais === 'ESP' && (
                      <BadgeValidacion validado={detalle.entidad.validado_aeat} etiqueta="AEAT" />
                    )}
                    {PAISES_UE.has(detalle.entidad.pais) && (
                      <BadgeValidacion validado={detalle.entidad.validado_vies} etiqueta="VIES" />
                    )}
                    {detalle.entidad.pais !== 'ESP' && !PAISES_UE.has(detalle.entidad.pais) && (
                      <span className="text-xs text-gray-400">No aplica validacion automatica</span>
                    )}
                  </div>
                  <button
                    onClick={() => void verificarEntidad(detalle.entidad.id)}
                    disabled={verificando === detalle.entidad.id}
                    className="mt-3 w-full px-3 py-1.5 text-xs bg-blue-50 text-blue-700 border border-blue-200 rounded hover:bg-blue-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {verificando === detalle.entidad.id ? 'Verificando...' : 'Verificar AEAT / VIES'}
                  </button>
                </div>

                {/* Aliases */}
                {detalle.entidad.aliases.length > 0 && (
                  <div className="mb-5">
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                      Aliases
                    </p>
                    <div className="flex flex-wrap gap-1">
                      {detalle.entidad.aliases.map((alias) => (
                        <span
                          key={alias}
                          className="inline-flex items-center px-2 py-0.5 rounded bg-gray-100 text-gray-600 text-xs"
                        >
                          {alias}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Overlays por empresa */}
                <div>
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                    Uso por empresa ({detalle.overlays.length})
                  </p>
                  {detalle.overlays.length === 0 ? (
                    <p className="text-xs text-gray-400 italic">Sin registros en ninguna empresa</p>
                  ) : (
                    <div className="space-y-3">
                      {detalle.overlays.map((overlay) => (
                        <div key={overlay.id} className="bg-gray-50 rounded-md p-3 text-xs">
                          <p className="font-medium text-gray-700 mb-1 truncate">{overlay.empresa_nombre}</p>
                          <div className="space-y-0.5 text-gray-500">
                            <div className="flex justify-between">
                              <span>Tipo</span>
                              <span
                                className={`font-medium ${
                                  overlay.tipo === 'proveedor' ? 'text-orange-600' : 'text-green-600'
                                }`}
                              >
                                {overlay.tipo}
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span>Subcuenta</span>
                              <span className="font-mono text-gray-700">{overlay.subcuenta_gasto}</span>
                            </div>
                            <div className="flex justify-between">
                              <span>Impuesto</span>
                              <span className="font-mono text-gray-700">{overlay.codimpuesto}</span>
                            </div>
                            <div className="flex justify-between">
                              <span>Regimen</span>
                              <span className="text-gray-700">{overlay.regimen}</span>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </>
      )}

      {/* Modal nueva entidad */}
      {modalAbierto && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4 p-6">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-lg font-semibold text-gray-800">Nueva entidad</h2>
              <button
                onClick={() => setModalAbierto(false)}
                className="text-gray-400 hover:text-gray-600 text-xl leading-none"
                aria-label="Cerrar modal"
              >
                &times;
              </button>
            </div>

            <div className="space-y-4">
              {/* CIF */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  CIF / NIF / VAT
                </label>
                <input
                  type="text"
                  placeholder="B12345678"
                  value={formNueva.cif}
                  onChange={(e) => setFormNueva((prev) => ({ ...prev, cif: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono"
                />
                <p className="mt-1 text-xs text-gray-400">Opcional — puede dejarse en blanco</p>
              </div>

              {/* Nombre */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Nombre <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  placeholder="RAZON SOCIAL O NOMBRE COMPLETO"
                  value={formNueva.nombre}
                  onChange={(e) => setFormNueva((prev) => ({ ...prev, nombre: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              {/* Nombre comercial */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Nombre comercial
                </label>
                <input
                  type="text"
                  placeholder="Nombre corto o alias principal"
                  value={formNueva.nombre_comercial}
                  onChange={(e) => setFormNueva((prev) => ({ ...prev, nombre_comercial: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              {/* Pais */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Pais</label>
                <select
                  value={formNueva.pais}
                  onChange={(e) => setFormNueva((prev) => ({ ...prev, pais: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white"
                >
                  <option value="ESP">Espana (ESP)</option>
                  <option value="DEU">Alemania (DEU)</option>
                  <option value="FRA">Francia (FRA)</option>
                  <option value="ITA">Italia (ITA)</option>
                  <option value="PRT">Portugal (PRT)</option>
                  <option value="NLD">Paises Bajos (NLD)</option>
                  <option value="BEL">Belgica (BEL)</option>
                  <option value="DNK">Dinamarca (DNK)</option>
                  <option value="GBR">Reino Unido (GBR)</option>
                  <option value="CHN">China (CHN)</option>
                  <option value="USA">Estados Unidos (USA)</option>
                  <option value="otro">Otro</option>
                </select>
              </div>

              {/* Tipo persona */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Tipo de persona</label>
                <select
                  value={formNueva.tipo_persona}
                  onChange={(e) =>
                    setFormNueva((prev) => ({
                      ...prev,
                      tipo_persona: e.target.value as 'fisica' | 'juridica' | '',
                    }))
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white"
                >
                  <option value="">Sin especificar</option>
                  <option value="juridica">Persona juridica (empresa/sociedad)</option>
                  <option value="fisica">Persona fisica (autonomo/particular)</option>
                </select>
              </div>
            </div>

            {/* Botones del modal */}
            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setModalAbierto(false)}
                className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800 transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={() => void guardarNuevaEntidad()}
                disabled={!formNueva.nombre.trim()}
                className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
              >
                Crear entidad
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
