import { NavLink, useParams } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

interface EnlaceSidebar {
  ruta: string
  etiqueta: string
}

/** Grupo de enlaces en el sidebar */
interface GrupoSidebar {
  titulo: string
  enlaces: EnlaceSidebar[]
}

/**
 * Sidebar de navegacion con fondo oscuro.
 * Muestra enlaces generales y, si hay empresa seleccionada, enlaces de empresa.
 */
export function Sidebar() {
  const { usuario, logout } = useAuth()
  const { id: empresaId } = useParams()

  /** Enlaces principales (siempre visibles) */
  const enlacesPrincipales: EnlaceSidebar[] = [
    { ruta: '/', etiqueta: 'Inicio' },
  ]

  /** Grupos de enlaces de empresa (visibles solo con empresa seleccionada) */
  const gruposEmpresa: GrupoSidebar[] = empresaId
    ? [
        {
          titulo: 'Contabilidad',
          enlaces: [
            { ruta: `/empresa/${empresaId}`, etiqueta: 'Resumen' },
            { ruta: `/empresa/${empresaId}/pyg`, etiqueta: 'Perdidas y Ganancias' },
            { ruta: `/empresa/${empresaId}/balance`, etiqueta: 'Balance' },
            { ruta: `/empresa/${empresaId}/diario`, etiqueta: 'Libro Diario' },
            { ruta: `/empresa/${empresaId}/facturas`, etiqueta: 'Facturas' },
            { ruta: `/empresa/${empresaId}/activos`, etiqueta: 'Activos Fijos' },
          ],
        },
        {
          titulo: 'Documentos',
          enlaces: [
            { ruta: `/empresa/${empresaId}/documentos`, etiqueta: 'Documentos' },
            { ruta: `/empresa/${empresaId}/cuarentena`, etiqueta: 'Cuarentena' },
            { ruta: `/empresa/${empresaId}/inbox`, etiqueta: 'Bandeja Entrada' },
          ],
        },
        {
          titulo: 'Operaciones',
          enlaces: [
            { ruta: `/empresa/${empresaId}/importar`, etiqueta: 'Importar' },
            { ruta: `/empresa/${empresaId}/exportar`, etiqueta: 'Exportar' },
            { ruta: `/empresa/${empresaId}/calendario`, etiqueta: 'Calendario Fiscal' },
            { ruta: `/empresa/${empresaId}/cierre`, etiqueta: 'Cierre Ejercicio' },
          ],
        },
      ]
    : []

  /** Estilos para enlaces activos/inactivos */
  const estiloEnlace = ({ isActive }: { isActive: boolean }) =>
    `block px-4 py-2 rounded-md text-sm transition-colors ${
      isActive
        ? 'bg-[var(--color-sidebar-active)] text-white font-medium'
        : 'text-[var(--color-sidebar-text)] hover:bg-slate-700 hover:text-white'
    }`

  return (
    <aside className="w-64 min-h-screen bg-[var(--color-sidebar-bg)] flex flex-col shrink-0">
      {/* Logo */}
      <div className="px-6 py-5 border-b border-slate-700">
        <h1 className="text-xl font-bold text-white tracking-wide">SFCE</h1>
        <p className="text-xs text-slate-400 mt-1">Sistema Fiscal Contable</p>
      </div>

      {/* Navegacion */}
      <nav className="flex-1 px-3 py-4 space-y-6 overflow-y-auto">
        {/* Enlaces principales */}
        <div className="space-y-1">
          {enlacesPrincipales.map((enlace) => (
            <NavLink key={enlace.ruta} to={enlace.ruta} end className={estiloEnlace}>
              {enlace.etiqueta}
            </NavLink>
          ))}
        </div>

        {/* Grupos de empresa */}
        {gruposEmpresa.map((grupo) => (
          <div key={grupo.titulo}>
            <h3 className="px-4 text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
              {grupo.titulo}
            </h3>
            <div className="space-y-1">
              {grupo.enlaces.map((enlace) => (
                <NavLink key={enlace.ruta} to={enlace.ruta} end className={estiloEnlace}>
                  {enlace.etiqueta}
                </NavLink>
              ))}
            </div>
          </div>
        ))}
      </nav>

      {/* Usuario y logout */}
      <div className="px-4 py-4 border-t border-slate-700">
        {usuario && (
          <div className="mb-3">
            <p className="text-sm text-white font-medium truncate">{usuario.nombre}</p>
            <p className="text-xs text-slate-400 truncate">{usuario.email}</p>
          </div>
        )}
        <button
          onClick={logout}
          className="w-full px-4 py-2 text-sm text-slate-300 hover:text-white hover:bg-slate-700 rounded-md transition-colors text-left"
        >
          Cerrar sesion
        </button>
      </div>
    </aside>
  )
}
