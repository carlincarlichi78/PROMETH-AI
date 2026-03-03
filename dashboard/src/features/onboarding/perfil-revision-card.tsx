import { useState, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Upload, ChevronDown, AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'

const auth = () => ({ Authorization: `Bearer ${sessionStorage.getItem('sfce_token')}` })

interface Perfil {
  id: number
  nif: string
  nombre: string
  forma_juridica: string
  confianza: number
  estado: string
}

interface CompletarResultado {
  nuevo_estado: string
  score: number
  bloqueos: string[]
  advertencias: string[]
}

function PerfilBloqueadoRow({
  perfil,
  onCompletado,
}: {
  perfil: Perfil
  onCompletado: () => void
}) {
  const [expandido, setExpandido] = useState(false)
  const [mensaje, setMensaje] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const qc = useQueryClient()

  const { mutate: completar, isPending } = useMutation<CompletarResultado, Error, File[]>({
    mutationFn: async (archivos: File[]) => {
      const fd = new FormData()
      archivos.forEach((f) => fd.append('archivos', f))
      const r = await fetch(`/api/onboarding/perfiles/${perfil.id}/completar`, {
        method: 'POST',
        headers: auth(),
        body: fd,
      })
      if (!r.ok) throw new Error(await r.text())
      return r.json()
    },
    onSuccess: (data) => {
      if (data.nuevo_estado !== 'bloqueado') {
        setMensaje(`Perfil desbloqueado (score: ${Math.round(data.score)}%) — estado: ${data.nuevo_estado}`)
        onCompletado()
      } else {
        setMensaje(`Sigue bloqueado: ${data.bloqueos.join(', ')}`)
      }
      qc.invalidateQueries({ queryKey: ['perfiles'] })
    },
  })

  const handleArchivos = () => {
    const archivos = Array.from(fileRef.current?.files ?? [])
    if (archivos.length) completar(archivos)
  }

  return (
    <div className="border border-destructive/30 rounded-lg p-3 space-y-2 bg-destructive/5">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-start gap-2 min-w-0">
          <AlertCircle className="h-4 w-4 text-destructive mt-0.5 shrink-0" />
          <div className="min-w-0">
            <div className="font-medium text-sm truncate">{perfil.nombre || perfil.nif || 'Sin nombre'}</div>
            <div className="text-xs text-muted-foreground">
              {perfil.nif} · Bloqueado · Falta 036/037
            </div>
          </div>
        </div>
        <Button
          size="sm"
          variant="outline"
          className="shrink-0 text-xs"
          onClick={() => setExpandido(!expandido)}
        >
          {expandido ? (
            <><ChevronDown className="h-3 w-3 mr-1" />Cerrar</>
          ) : (
            <><Upload className="h-3 w-3 mr-1" />Añadir documentos</>
          )}
        </Button>
      </div>

      {expandido && (
        <div className="pt-1 space-y-2">
          <p className="text-xs text-muted-foreground">
            Sube el modelo 036/037 de esta empresa para desbloquear el perfil.
          </p>
          <div className="flex items-center gap-2">
            <input
              ref={fileRef}
              type="file"
              accept=".pdf,.csv,.xlsx"
              multiple
              className="hidden"
              title="Seleccionar documentos"
              aria-label="Seleccionar documentos"
              onChange={handleArchivos}
            />
            <Button
              size="sm"
              variant="outline"
              onClick={() => fileRef.current?.click()}
              disabled={isPending}
            >
              {isPending ? 'Procesando...' : 'Seleccionar archivos'}
            </Button>
          </div>
          {mensaje && (
            <p className="text-xs font-medium text-muted-foreground">{mensaje}</p>
          )}
        </div>
      )}
    </div>
  )
}

export function PerfilRevisionCard({ loteId }: { loteId: number }) {
  const qc = useQueryClient()
  const { data: perfiles = [] } = useQuery<Perfil[]>({
    queryKey: ['perfiles', loteId],
    queryFn: async () => {
      const r = await fetch(`/api/onboarding/lotes/${loteId}/perfiles`, { headers: auth() })
      return r.json()
    },
  })

  const { mutate: aprobar } = useMutation({
    mutationFn: async (perfilId: number) => {
      const r = await fetch(`/api/onboarding/perfiles/${perfilId}/aprobar`, {
        method: 'POST',
        headers: auth(),
      })
      return r.json()
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['perfiles', loteId] }),
  })

  const pendientes = perfiles.filter((p) => p.estado === 'revision')
  const bloqueados = perfiles.filter((p) => p.estado === 'bloqueado')

  if (!pendientes.length && !bloqueados.length) return null

  return (
    <div className="space-y-4">
      {pendientes.length > 0 && (
        <div className="border rounded-lg p-6 space-y-3">
          <h2 className="font-semibold">Pendientes de revisión ({pendientes.length})</h2>
          {pendientes.map((p) => (
            <div
              key={p.id}
              className="flex items-center justify-between p-3 bg-muted/50 rounded-lg"
            >
              <div>
                <div className="font-medium">{p.nombre || p.nif}</div>
                <div className="text-xs text-muted-foreground">
                  {p.nif} · {p.forma_juridica} · Confianza: {Math.round(p.confianza)}%
                </div>
              </div>
              <Button size="sm" onClick={() => aprobar(p.id)}>
                Aprobar y crear →
              </Button>
            </div>
          ))}
        </div>
      )}

      {bloqueados.length > 0 && (
        <div className="border rounded-lg p-6 space-y-3">
          <h2 className="font-semibold text-destructive">
            Bloqueados — requieren acción ({bloqueados.length})
          </h2>
          {bloqueados.map((p) => (
            <PerfilBloqueadoRow
              key={p.id}
              perfil={p}
              onCompletado={() => qc.invalidateQueries({ queryKey: ['perfiles', loteId] })}
            />
          ))}
        </div>
      )}
    </div>
  )
}
