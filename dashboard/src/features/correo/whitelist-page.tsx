import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import { PageTitle } from '@/components/ui/page-title'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { listarRemitentes, anadirRemitente, eliminarRemitente } from './api'

export function WhitelistPage() {
  const { id } = useParams<{ id: string }>()
  const empresaId = Number(id)
  const qc = useQueryClient()
  const [nuevoEmail, setNuevoEmail] = useState('')
  const [nuevoNombre, setNuevoNombre] = useState('')

  const { data } = useQuery({
    queryKey: ['whitelist', empresaId],
    queryFn: () => listarRemitentes(empresaId),
  })

  const mutAdd = useMutation({
    mutationFn: () =>
      anadirRemitente(empresaId, { email: nuevoEmail, nombre: nuevoNombre || undefined }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['whitelist', empresaId] })
      setNuevoEmail('')
      setNuevoNombre('')
    },
  })

  const mutDel = useMutation({
    mutationFn: (rId: number) => eliminarRemitente(rId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['whitelist', empresaId] }),
  })

  return (
    <div className="p-6 space-y-6 max-w-2xl">
      <PageTitle titulo="Remitentes autorizados" />

      {data?.aviso_primer_remitente && (
        <Alert>
          <AlertDescription>
            Has añadido el primer remitente. A partir de ahora, solo se aceptarán
            emails de los remitentes de esta lista. Los demás irán a cuarentena.
          </AlertDescription>
        </Alert>
      )}

      {!data?.whitelist_activa && (
        <p className="text-sm text-muted-foreground">
          Sin whitelist configurada — se aceptan emails de cualquier remitente.
        </p>
      )}

      <div className="flex gap-2">
        <Input
          placeholder="email@dominio.es o @dominio.es (wildcard)"
          value={nuevoEmail}
          onChange={e => setNuevoEmail(e.target.value)}
        />
        <Input
          placeholder="Nombre (opcional)"
          value={nuevoNombre}
          onChange={e => setNuevoNombre(e.target.value)}
        />
        <Button onClick={() => mutAdd.mutate()} disabled={!nuevoEmail || mutAdd.isPending}>
          Añadir
        </Button>
      </div>

      <ul className="space-y-2">
        {data?.remitentes.map(r => (
          <li key={r.id} className="flex items-center justify-between rounded border p-3">
            <div>
              <span className="font-mono text-sm">{r.email}</span>
              {r.nombre && (
                <span className="ml-2 text-muted-foreground text-sm">({r.nombre})</span>
              )}
              {r.email.startsWith('@') && (
                <Badge variant="outline" className="ml-2">wildcard</Badge>
              )}
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => mutDel.mutate(r.id)}
            >
              Eliminar
            </Button>
          </li>
        ))}
      </ul>

      {data?.remitentes.length === 0 && !data?.whitelist_activa && (
        <p className="text-sm text-center text-muted-foreground py-4">
          No hay remitentes configurados.
        </p>
      )}
    </div>
  )
}
