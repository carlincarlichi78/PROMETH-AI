import { useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { GitBranch, Activity, CheckCircle, AlertCircle } from 'lucide-react'
import { api } from '@/lib/api-client'
import { queryKeys } from '@/lib/query-keys'
import { KPICard } from '@/components/charts/kpi-card'
import { PageHeader } from '@/components/page-header'
import { EmptyState } from '@/components/ui/empty-state'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Card, CardContent } from '@/components/ui/card'

interface FasePipeline {
  fase: string
  total: number
  procesados: number
  errores: number
}

export default function PipelinePage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const empresaId = Number(id)

  const { data: fases = [], isLoading } = useQuery({
    queryKey: queryKeys.documentos.pipeline(empresaId),
    queryFn: () => api.get<FasePipeline[]>(`/api/documentos/${empresaId}/pipeline`),
    enabled: !isNaN(empresaId),
  })

  const totalesGlobales = useMemo(() => {
    const total = fases.reduce((acc, f) => acc + f.total, 0)
    const procesados = fases.reduce((acc, f) => acc + f.procesados, 0)
    const errores = fases.reduce((acc, f) => acc + f.errores, 0)
    const tasaExito = total > 0 ? Math.round((procesados / total) * 100) : 0
    return { total, procesados, errores, tasaExito }
  }, [fases])

  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader
          titulo="Pipeline"
          descripcion="Estado del procesamiento de documentos"
        />
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <KPICard key={i} titulo="" valor="" cargando />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        titulo="Pipeline"
        descripcion="Estado del procesamiento de documentos"
      />

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          titulo="Documentos totales"
          valor={String(totalesGlobales.total)}
          icono={GitBranch}
        />
        <KPICard
          titulo="Procesados"
          valor={String(totalesGlobales.procesados)}
          icono={CheckCircle}
        />
        <KPICard
          titulo="Con errores"
          valor={String(totalesGlobales.errores)}
          icono={AlertCircle}
          invertirColor
        />
        <KPICard
          titulo="Tasa exito"
          valor={`${totalesGlobales.tasaExito}%`}
          icono={Activity}
        />
      </div>

      {fases.length === 0 ? (
        <EmptyState
          icono={<GitBranch className="h-8 w-8" />}
          titulo="Sin pipeline activo"
          descripcion="Cuando proceses documentos desde la Bandeja de Entrada, verás el progreso en tiempo real por cada fase del pipeline."
          accion={{ texto: 'Ir a Bandeja de Entrada', onClick: () => navigate(`/empresa/${id}/inbox`) }}
        />
      ) : (
        <Card className="bg-[var(--surface-1)] border-border/50">
          <CardContent className="pt-6 space-y-5">
            {fases.map((fase) => {
              const porcentaje = fase.total > 0 ? Math.round((fase.procesados / fase.total) * 100) : 0
              return (
                <div key={fase.fase} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">{fase.fase}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-muted-foreground">
                        {fase.procesados}/{fase.total} docs
                      </span>
                      {fase.errores > 0 && (
                        <Badge variant="destructive" className="text-xs">
                          {fase.errores} errores
                        </Badge>
                      )}
                    </div>
                  </div>
                  <Progress value={porcentaje} className="h-2" />
                </div>
              )
            })}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
