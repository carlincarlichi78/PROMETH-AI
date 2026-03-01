import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { listarReglas, crearRegla, eliminarRegla, ReglaClasificacion } from './api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Trash2 } from 'lucide-react'

interface FormRegla {
  patron: string
  accion: string
}

export function ReglasClasificacion({ empresaId }: { empresaId: number }) {
  const qc = useQueryClient()
  const { data: reglas, isLoading } = useQuery({
    queryKey: ['correo-reglas', empresaId],
    queryFn: () => listarReglas(empresaId),
  })

  const { register, handleSubmit, reset, formState: { errors } } = useForm<FormRegla>()

  const crearMutation = useMutation({
    mutationFn: (datos: FormRegla) => crearRegla({ empresa_id: empresaId, ...datos }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['correo-reglas', empresaId] })
      reset()
    },
  })

  const eliminarMutation = useMutation({
    mutationFn: eliminarRegla,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['correo-reglas', empresaId] }),
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Reglas de clasificación</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <form
          onSubmit={handleSubmit((d) => crearMutation.mutate(d))}
          className="flex gap-2 items-end"
        >
          <div className="flex-1">
            <Label>Patrón (asunto/remitente)</Label>
            <Input placeholder="endesa" {...register('patron', { required: true })} />
            {errors.patron && <p className="text-xs text-red-500">Obligatorio</p>}
          </div>
          <div className="flex-1">
            <Label>Acción</Label>
            <Input placeholder="facturas_electricidad" {...register('accion', { required: true })} />
            {errors.accion && <p className="text-xs text-red-500">Obligatorio</p>}
          </div>
          <Button type="submit" size="sm" disabled={crearMutation.isPending}>
            Añadir
          </Button>
        </form>

        {isLoading && <p className="text-sm text-muted-foreground">Cargando reglas...</p>}

        <div className="space-y-2">
          {reglas?.map((r: ReglaClasificacion) => (
            <div key={r.id} className="flex items-center justify-between p-2 border rounded text-sm">
              <span>
                <span className="font-mono bg-muted px-1 rounded">{r.patron}</span>
                <span className="mx-2 text-muted-foreground">→</span>
                <span className="text-primary">{r.accion}</span>
              </span>
              <Button
                size="sm"
                variant="ghost"
                className="text-destructive h-6 w-6 p-0"
                onClick={() => eliminarMutation.mutate(r.id)}
              >
                <Trash2 className="w-3 h-3" />
              </Button>
            </div>
          ))}
          {reglas?.length === 0 && !isLoading && (
            <p className="text-sm text-muted-foreground text-center py-2">Sin reglas definidas.</p>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
