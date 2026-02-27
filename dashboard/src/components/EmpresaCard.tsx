import { Link } from 'react-router-dom'
import type { Empresa } from '../types'

/** Insignia de forma juridica con colores diferenciados */
function InsigniaFormaJuridica({ forma }: { forma: string }) {
  const colores: Record<string, string> = {
    'sl': 'bg-blue-100 text-blue-800',
    'sa': 'bg-purple-100 text-purple-800',
    'autonomo': 'bg-green-100 text-green-800',
    'comunidad': 'bg-amber-100 text-amber-800',
    'cooperativa': 'bg-teal-100 text-teal-800',
  }

  const clave = forma.toLowerCase().replace(/[^a-z]/g, '')
  const estiloColor = Object.entries(colores).find(([k]) => clave.includes(k))?.[1]
    ?? 'bg-gray-100 text-gray-800'

  return (
    <span className={`inline-block px-2 py-0.5 text-xs font-medium rounded-full ${estiloColor}`}>
      {forma}
    </span>
  )
}

interface EmpresaCardProps {
  empresa: Empresa
}

/** Tarjeta de empresa para la cuadricula del panel de control */
export function EmpresaCard({ empresa }: EmpresaCardProps) {
  return (
    <Link
      to={`/empresa/${empresa.id}`}
      className="block bg-white rounded-lg shadow hover:shadow-md transition-shadow border border-gray-200"
    >
      <div className="p-5">
        {/* Nombre */}
        <h3 className="text-lg font-semibold text-gray-800 truncate mb-1">
          {empresa.nombre}
        </h3>

        {/* CIF */}
        <p className="text-sm text-gray-500 mb-3 font-mono">
          {empresa.cif}
        </p>

        {/* Metadata */}
        <div className="flex flex-wrap items-center gap-2">
          <InsigniaFormaJuridica forma={empresa.forma_juridica} />
          <span className="text-xs text-gray-400">
            {empresa.territorio}
          </span>
        </div>

        {/* Regimen IVA */}
        <p className="text-xs text-gray-400 mt-2">
          {empresa.regimen_iva}
        </p>
      </div>

      {/* Franja inferior */}
      <div className="px-5 py-3 bg-gray-50 rounded-b-lg border-t border-gray-100">
        <span className="text-sm text-[var(--color-primary)] font-medium">
          Ver contabilidad
        </span>
      </div>
    </Link>
  )
}
