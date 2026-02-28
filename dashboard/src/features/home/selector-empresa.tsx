import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Building2, ChevronRight, Plus } from 'lucide-react'
import { api } from '@/lib/api-client'
import { queryKeys } from '@/lib/query-keys'
import { useEmpresaStore } from '@/stores/empresa-store'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { PageHeader } from '@/components/page-header'
import type { Empresa } from '@/types'

export function SelectorEmpresa() {
  const navigate = useNavigate()
  const setEmpresaActiva = useEmpresaStore((s) => s.setEmpresaActiva)

  const { data: empresas, isLoading } = useQuery({
    queryKey: queryKeys.empresas.todas,
    queryFn: () => api.get<Empresa[]>('/api/empresas'),
  })

  const handleSeleccionar = (empresa: Empresa) => {
    setEmpresaActiva(empresa)
    navigate(`/empresa/${empresa.id}/pyg`)
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader titulo="Panel Principal" descripcion="Selecciona una empresa para comenzar" />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-36 rounded-xl" />
          ))}
        </div>
      </div>
    )
  }

  const empresasActivas = empresas?.filter((e) => e.activa) ?? []
  const empresasInactivas = empresas?.filter((e) => !e.activa) ?? []

  return (
    <div className="space-y-6">
      <PageHeader titulo="Panel Principal" descripcion="Selecciona una empresa para ver su contabilidad" />

      {empresasActivas.length === 0 && (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-12 gap-3 text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-muted">
              <Building2 className="h-6 w-6 text-muted-foreground" />
            </div>
            <div>
              <p className="font-medium">Sin empresas registradas</p>
              <p className="text-sm text-muted-foreground">Crea una empresa para empezar</p>
            </div>
          </CardContent>
        </Card>
      )}

      {empresasActivas.length > 0 && (
        <div>
          <h2 className="text-sm font-medium text-muted-foreground mb-3">Empresas activas</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {empresasActivas.map((empresa) => (
              <TarjetaEmpresa key={empresa.id} empresa={empresa} onSeleccionar={handleSeleccionar} />
            ))}

            <button
              onClick={() => navigate('/directorio')}
              className="group flex flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed border-border p-8 text-muted-foreground transition-colors hover:border-primary hover:text-primary"
            >
              <Plus className="h-6 w-6" />
              <span className="text-sm font-medium">Nuevo cliente</span>
            </button>
          </div>
        </div>
      )}

      {empresasInactivas.length > 0 && (
        <div>
          <h2 className="text-sm font-medium text-muted-foreground mb-3">Inactivas</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {empresasInactivas.map((empresa) => (
              <TarjetaEmpresa key={empresa.id} empresa={empresa} onSeleccionar={handleSeleccionar} inactiva />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

interface TarjetaEmpresaProps {
  empresa: Empresa
  onSeleccionar: (empresa: Empresa) => void
  inactiva?: boolean
}

function TarjetaEmpresa({ empresa, onSeleccionar, inactiva }: TarjetaEmpresaProps) {
  return (
    <Card
      className={`group cursor-pointer transition-all hover:shadow-md hover:border-primary/50 ${inactiva ? 'opacity-60' : ''}`}
      onClick={() => onSeleccionar(empresa)}
    >
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-primary/10">
            <Building2 className="h-5 w-5 text-primary" />
          </div>
          <ChevronRight className="h-4 w-4 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
        </div>
      </CardHeader>
      <CardContent className="space-y-2">
        <CardTitle className="text-base leading-tight">{empresa.nombre}</CardTitle>
        <p className="text-xs text-muted-foreground font-mono">{empresa.cif}</p>
        <div className="flex flex-wrap gap-1 pt-1">
          <Badge variant="secondary" className="text-xs">
            {empresa.forma_juridica}
          </Badge>
          <Badge variant="outline" className="text-xs">
            {empresa.regimen_iva}
          </Badge>
          {inactiva && (
            <Badge variant="destructive" className="text-xs">
              Inactiva
            </Badge>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
