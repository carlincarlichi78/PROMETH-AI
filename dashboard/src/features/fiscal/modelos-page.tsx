import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { FileText, Calculator } from 'lucide-react'
import { PageHeader } from '@/components/page-header'
import { EstadoVacio } from '@/components/estado-vacio'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { api } from '@/lib/api-client'
import { queryKeys } from '@/lib/query-keys'

interface ModeloDisponible {
  codigo: string
  nombre: string
  tipo: 'trimestral' | 'anual'
  descripcion: string
}

interface RespuestaDisponibles {
  modelos: ModeloDisponible[]
}

function SkeletonCard() {
  return (
    <Card>
      <CardHeader className="pb-3">
        <Skeleton className="h-8 w-16 mb-1" />
        <Skeleton className="h-4 w-32" />
      </CardHeader>
      <CardContent className="space-y-3">
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-8 w-24" />
      </CardContent>
    </Card>
  )
}

function ModeloCard({
  modelo,
  empresaId,
}: {
  modelo: ModeloDisponible
  empresaId: number
}) {
  const navigate = useNavigate()
  return (
    <Card className="flex flex-col">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-3xl font-bold tracking-tight text-primary">
            {modelo.codigo}
          </CardTitle>
          <Badge variant={modelo.tipo === 'trimestral' ? 'outline' : 'secondary'} className="mt-1">
            {modelo.tipo === 'trimestral' ? 'Trimestral' : 'Anual'}
          </Badge>
        </div>
        <CardDescription className="font-medium text-foreground/80">{modelo.nombre}</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col flex-1 justify-between gap-4">
        <p className="text-sm text-muted-foreground">{modelo.descripcion}</p>
        <Button
          size="sm"
          variant="outline"
          className="w-fit"
          onClick={() =>
            navigate(`/empresa/${empresaId}/fiscal/generar?modelo=${modelo.codigo}`)
          }
        >
          <Calculator className="h-3.5 w-3.5 mr-1.5" />
          Generar
        </Button>
      </CardContent>
    </Card>
  )
}

function GrupoModelos({
  titulo,
  modelos,
  empresaId,
}: {
  titulo: string
  modelos: ModeloDisponible[]
  empresaId: number
}) {
  if (modelos.length === 0) return null
  return (
    <div className="space-y-4">
      <h2 className="text-base font-semibold text-muted-foreground uppercase tracking-wide">
        {titulo}
      </h2>
      <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
        {modelos.map((m) => (
          <ModeloCard key={m.codigo} modelo={m} empresaId={empresaId} />
        ))}
      </div>
    </div>
  )
}

export default function ModelosPage() {
  const { id } = useParams<{ id: string }>()
  const empresaId = Number(id)

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.modelos.disponibles,
    queryFn: () => api.get<RespuestaDisponibles>('/api/modelos/disponibles'),
  })

  const modelos = data?.modelos ?? []

  const trimestrales = modelos.filter((m) => m.tipo === 'trimestral')
  const anuales = modelos.filter((m) => m.tipo === 'anual')

  if (isLoading) {
    return (
      <div className="space-y-8">
        <PageHeader
          titulo="Modelos Fiscales"
          descripcion="Genera y presenta tus modelos fiscales"
        />
        <div className="space-y-4">
          <Skeleton className="h-4 w-32" />
          <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <SkeletonCard key={i} />
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (modelos.length === 0) {
    return (
      <div>
        <PageHeader
          titulo="Modelos Fiscales"
          descripcion="Genera y presenta tus modelos fiscales"
        />
        <EstadoVacio
          titulo="Sin modelos disponibles"
          descripcion="No hay modelos fiscales configurados para este ejercicio."
          icono={FileText}
        />
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <PageHeader
        titulo="Modelos Fiscales"
        descripcion="Genera y presenta tus modelos fiscales"
      />

      <GrupoModelos titulo="Trimestrales" modelos={trimestrales} empresaId={empresaId} />
      <GrupoModelos titulo="Anuales" modelos={anuales} empresaId={empresaId} />
    </div>
  )
}
