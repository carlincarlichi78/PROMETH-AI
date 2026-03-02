import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { PageTitle } from '@/components/ui/page-title'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { listarEmailsGestor } from './api'
import { ConfirmarEnriquecimientoDialog } from './confirmar-enriquecimiento-dialog'

const ESTADO_BADGE: Record<string, string> = {
  CLASIFICADO: 'bg-green-100 text-green-800',
  CUARENTENA: 'bg-amber-100 text-amber-800',
  PROCESADO: 'bg-blue-100 text-blue-800',
  IGNORADO: 'bg-gray-100 text-gray-600',
}

export function GestorEmailsPage() {
  const params = useParams<{ id?: string; empresaId?: string }>()
  const rawId = params.id ?? params.empresaId ?? ''
  const id = Number(rawId)
  const [estado, setEstado] = useState<string>('')
  const [offset, setOffset] = useState(0)
  const [emailConfirmando, setEmailConfirmando] = useState<{ id: number; campos: string[] } | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['emails-gestor', id, estado, offset],
    queryFn: () => listarEmailsGestor(id, { estado: estado || undefined, limit: 20, offset }),
    enabled: !!id,
  })

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <PageTitle titulo="Emails recibidos" />
        <Select value={estado} onValueChange={v => { setEstado(v); setOffset(0) }}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Todos" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">Todos</SelectItem>
            <SelectItem value="CLASIFICADO">Clasificados</SelectItem>
            <SelectItem value="CUARENTENA">Cuarentena</SelectItem>
            <SelectItem value="PROCESADO">Procesados</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {isLoading && <p className="text-sm text-muted-foreground">Cargando...</p>}

      <div className="rounded border divide-y">
        {data?.emails.map(email => (
          <div key={email.id} className="p-3 flex items-start gap-3">
            <div className="flex-1 min-w-0">
              <p className="font-medium text-sm truncate">{email.asunto}</p>
              <p className="text-xs text-muted-foreground">
                {email.remitente}
                {email.fecha && ` · ${email.fecha}`}
              </p>
              {email.enriquecimiento_aplicado && Object.keys(email.enriquecimiento_aplicado).length > 0 && (
                <p className="text-xs text-blue-600 mt-1">
                  Instrucciones aplicadas: {Object.keys(email.enriquecimiento_aplicado).join(', ')}
                </p>
              )}
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <Badge className={ESTADO_BADGE[email.estado] ?? 'bg-gray-100 text-gray-600'}>
                {email.estado}
              </Badge>
              {email.enriquecimiento_pendiente && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setEmailConfirmando({ id: email.id, campos: [] })}
                >
                  Confirmar
                </Button>
              )}
            </div>
          </div>
        ))}
        {!isLoading && data?.emails.length === 0 && (
          <p className="p-6 text-sm text-center text-muted-foreground">No hay emails.</p>
        )}
      </div>

      <div className="flex justify-between text-sm text-muted-foreground">
        <span>{data?.total ?? 0} emails totales</span>
        <div className="flex gap-2">
          <Button
            variant="ghost"
            size="sm"
            disabled={offset === 0}
            onClick={() => setOffset(o => Math.max(0, o - 20))}
          >
            Anterior
          </Button>
          <Button
            variant="ghost"
            size="sm"
            disabled={(offset + 20) >= (data?.total ?? 0)}
            onClick={() => setOffset(o => o + 20)}
          >
            Siguiente
          </Button>
        </div>
      </div>

      {emailConfirmando && (
        <ConfirmarEnriquecimientoDialog
          emailId={emailConfirmando.id}
          camposPendientes={emailConfirmando.campos}
          empresaId={id}
          onClose={() => setEmailConfirmando(null)}
        />
      )}
    </div>
  )
}
