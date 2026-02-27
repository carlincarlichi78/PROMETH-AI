import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import type { Empresa as EmpresaType, ProveedorCliente, Trabajador } from '../types'

/** Tarjeta de estadistica con numero y etiqueta */
function TarjetaEstadistica({ etiqueta, valor, color }: { etiqueta: string; valor: number; color: string }) {
  return (
    <div className={`bg-white rounded-lg shadow border-l-4 p-4 ${color}`}>
      <p className="text-2xl font-bold text-gray-800">{valor}</p>
      <p className="text-sm text-gray-500">{etiqueta}</p>
    </div>
  )
}

/** Enlace rapido a subpagina de empresa */
function EnlaceRapido({ ruta, etiqueta, descripcion }: { ruta: string; etiqueta: string; descripcion: string }) {
  return (
    <Link
      to={ruta}
      className="block bg-white rounded-lg shadow hover:shadow-md transition-shadow border border-gray-200 p-4"
    >
      <h4 className="font-medium text-gray-800 mb-1">{etiqueta}</h4>
      <p className="text-sm text-gray-500">{descripcion}</p>
    </Link>
  )
}

/** Pagina de detalle de empresa — resumen con estadisticas y enlaces rapidos */
export function Empresa() {
  const { id } = useParams()
  const { fetchConAuth } = useApi()
  const empresaId = Number(id)

  const [empresa, setEmpresa] = useState<EmpresaType | null>(null)
  const [proveedores, setProveedores] = useState<ProveedorCliente[]>([])
  const [trabajadores, setTrabajadores] = useState<Trabajador[]>([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const cargarDatos = async () => {
    setCargando(true)
    setError(null)
    try {
      const [emp, provs, trabs] = await Promise.all([
        fetchConAuth<EmpresaType>(`/api/empresas/${empresaId}`),
        fetchConAuth<ProveedorCliente[]>(`/api/empresas/${empresaId}/proveedores`),
        fetchConAuth<Trabajador[]>(`/api/empresas/${empresaId}/trabajadores`),
      ])
      setEmpresa(emp)
      setProveedores(provs)
      setTrabajadores(trabs)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al cargar datos de la empresa')
    } finally {
      setCargando(false)
    }
  }

  useEffect(() => {
    if (empresaId) {
      void cargarDatos()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [empresaId])

  if (cargando) {
    return (
      <div className="animate-pulse">
        <div className="h-8 bg-gray-200 rounded w-1/2 mb-4" />
        <div className="h-4 bg-gray-200 rounded w-1/3 mb-6" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-white rounded-lg shadow p-4 h-20" />
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-700 mb-2">{error}</p>
        <button
          onClick={() => void cargarDatos()}
          className="px-4 py-2 text-sm bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
        >
          Reintentar
        </button>
      </div>
    )
  }

  if (!empresa) return null

  const enlacesContabilidad = [
    { ruta: `/empresa/${empresaId}/pyg`, etiqueta: 'Perdidas y Ganancias', descripcion: 'Ingresos, gastos y resultado del ejercicio' },
    { ruta: `/empresa/${empresaId}/balance`, etiqueta: 'Balance de Situacion', descripcion: 'Activo, pasivo y patrimonio neto' },
    { ruta: `/empresa/${empresaId}/diario`, etiqueta: 'Libro Diario', descripcion: 'Asientos contables con partidas' },
    { ruta: `/empresa/${empresaId}/facturas`, etiqueta: 'Facturas', descripcion: 'Facturas emitidas y recibidas' },
    { ruta: `/empresa/${empresaId}/activos`, etiqueta: 'Activos Fijos', descripcion: 'Bienes de inversion y amortizaciones' },
  ]

  return (
    <div>
      {/* Cabecera */}
      <div className="mb-6">
        <Link to="/" className="text-sm text-[var(--color-primary)] hover:underline mb-2 inline-block">
          Volver al panel
        </Link>
        <h1 className="text-2xl font-bold text-gray-800">{empresa.nombre}</h1>
      </div>

      {/* Informacion general */}
      <div className="bg-white rounded-lg shadow p-5 mb-6">
        <h2 className="text-lg font-semibold text-gray-700 mb-3">Informacion general</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <p className="text-gray-400">CIF</p>
            <p className="font-mono text-gray-800">{empresa.cif}</p>
          </div>
          <div>
            <p className="text-gray-400">Forma juridica</p>
            <p className="text-gray-800">{empresa.forma_juridica}</p>
          </div>
          <div>
            <p className="text-gray-400">Territorio</p>
            <p className="text-gray-800">{empresa.territorio}</p>
          </div>
          <div>
            <p className="text-gray-400">Regimen IVA</p>
            <p className="text-gray-800">{empresa.regimen_iva}</p>
          </div>
        </div>
      </div>

      {/* Estadisticas */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <TarjetaEstadistica
          etiqueta="Proveedores / Clientes"
          valor={proveedores.length}
          color="border-blue-500"
        />
        <TarjetaEstadistica
          etiqueta="Trabajadores activos"
          valor={trabajadores.length}
          color="border-green-500"
        />
        <TarjetaEstadistica
          etiqueta="Total entidades"
          valor={proveedores.length + trabajadores.length}
          color="border-purple-500"
        />
      </div>

      {/* Enlaces rapidos — contabilidad */}
      <h2 className="text-lg font-semibold text-gray-700 mb-3">Contabilidad</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {enlacesContabilidad.map((enlace) => (
          <EnlaceRapido key={enlace.ruta} {...enlace} />
        ))}
      </div>
    </div>
  )
}

/** Pagina stub generica para subrutas que aun no estan implementadas */
export function EmpresaSubpagina({ titulo }: { titulo: string }) {
  const { id } = useParams()

  return (
    <div>
      <div className="mb-4">
        <Link to={`/empresa/${id}`} className="text-sm text-[var(--color-primary)] hover:underline">
          Volver al resumen
        </Link>
      </div>
      <h1 className="text-2xl font-bold text-gray-800 mb-4">
        {titulo}
      </h1>
      <div className="bg-white rounded-lg shadow p-6">
        <p className="text-gray-500">{titulo} -- en construccion</p>
      </div>
    </div>
  )
}
