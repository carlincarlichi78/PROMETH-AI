import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'

interface Perfil {
  id: number
  nif: string
  nombre: string
  forma_juridica: string
  confianza: number
  estado: string
}

export function PerfilRevisionCard({ loteId }: { loteId: number }) {
  const qc = useQueryClient()
  const { data: perfiles = [] } = useQuery<Perfil[]>({
    queryKey: ['perfiles', loteId],
    queryFn: async () => {
      const r = await fetch(`/api/onboarding/lotes/${loteId}/perfiles`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      })
      return r.json()
    },
  })

  const { mutate: aprobar } = useMutation({
    mutationFn: async (perfilId: number) => {
      const r = await fetch(`/api/onboarding/perfiles/${perfilId}/aprobar`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      })
      return r.json()
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['perfiles', loteId] }),
  })

  const pendientes = perfiles.filter((p) => p.estado === 'revision')

  if (!pendientes.length) return null

  return (
    <div className="border rounded-lg p-6 space-y-3">
      <h2 className="font-semibold">Pendientes de revisión ({pendientes.length})</h2>
      {pendientes.map((p) => (
        <div key={p.id}
             className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
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
  )
}
