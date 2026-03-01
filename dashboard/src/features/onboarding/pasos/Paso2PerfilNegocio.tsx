import { useForm } from 'react-hook-form'
import { useMutation } from '@tanstack/react-query'
import { actualizarPerfil, PerfilNegocio } from '../api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

export function Paso2PerfilNegocio({ empresaId, onAvanzar }: { empresaId: number; onAvanzar: () => void }) {
  const { register, handleSubmit } = useForm<PerfilNegocio>()

  const mutation = useMutation({
    mutationFn: (datos: PerfilNegocio) => actualizarPerfil(empresaId, datos),
    onSuccess: onAvanzar,
  })

  const saltar = () => onAvanzar()

  return (
    <form onSubmit={handleSubmit((d) => mutation.mutate(d))} className="space-y-4">
      <h2 className="text-xl font-semibold">Paso 2: Perfil de negocio</h2>
      <p className="text-sm text-muted-foreground">Opcional — puedes completarlo más adelante.</p>

      <div>
        <Label htmlFor="sector">Sector de actividad</Label>
        <Input id="sector" placeholder="Ej: Hostelería, Construcción..." {...register('sector')} />
      </div>

      <div>
        <Label htmlFor="empleados">Número de empleados</Label>
        <Input id="empleados" type="number" min={0} {...register('empleados', { valueAsNumber: true })} />
      </div>

      <div>
        <Label htmlFor="facturacion_anual">Facturación anual estimada (€)</Label>
        <Input id="facturacion_anual" type="number" min={0} step={1000} {...register('facturacion_anual', { valueAsNumber: true })} />
      </div>

      <div>
        <Label htmlFor="descripcion">Descripción breve</Label>
        <Input id="descripcion" placeholder="Actividad principal de la empresa..." {...register('descripcion')} />
      </div>

      <div className="flex gap-3">
        <Button type="submit" disabled={mutation.isPending} className="flex-1">
          {mutation.isPending ? 'Guardando...' : 'Guardar y continuar'}
        </Button>
        <Button type="button" variant="outline" onClick={saltar}>
          Saltar
        </Button>
      </div>
      {mutation.isError && (
        <p className="text-sm text-red-500">
          {mutation.error instanceof Error ? mutation.error.message : 'Error al guardar perfil'}
        </p>
      )}
    </form>
  )
}
