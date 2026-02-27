import { useParams } from 'react-router-dom'

/** Pagina de detalle de empresa — stub */
export function Empresa() {
  const { id } = useParams()

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-800 mb-4">
        Empresa #{id}
      </h1>
      <div className="bg-white rounded-lg shadow p-6">
        <p className="text-gray-500">Resumen de empresa en construccion</p>
      </div>
    </div>
  )
}

/** Pagina stub generica para subrutas de empresa */
export function EmpresaSubpagina({ titulo }: { titulo: string }) {
  const { id } = useParams()

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-800 mb-4">
        {titulo}
      </h1>
      <p className="text-sm text-gray-400 mb-4">Empresa #{id}</p>
      <div className="bg-white rounded-lg shadow p-6">
        <p className="text-gray-500">{titulo} en construccion</p>
      </div>
    </div>
  )
}
