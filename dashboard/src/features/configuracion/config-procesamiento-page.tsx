import { useParams } from 'react-router-dom'
import { PageTitle } from '@/components/ui/page-title'
import { ConfigProcesamientoCard } from './config-procesamiento-card'

export default function ConfigProcesamientoPage() {
  const { id } = useParams<{ id: string }>()
  const empresaId = parseInt(id ?? '0')

  if (!empresaId) return null

  return (
    <div className="p-6 max-w-lg">
      <PageTitle
        titulo="Pipeline de documentos"
        subtitulo="Configura cómo se procesan los documentos subidos por el cliente"
      />
      <div className="mt-6">
        <ConfigProcesamientoCard empresaId={empresaId} />
      </div>
    </div>
  )
}
