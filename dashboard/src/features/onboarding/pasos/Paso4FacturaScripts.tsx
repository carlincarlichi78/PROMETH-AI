import { useForm } from 'react-hook-form'
import { useMutation } from '@tanstack/react-query'
import { actualizarFacturaScripts, DatosFacturaScripts } from '../api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

export function Paso4FacturaScripts({ empresaId, onAvanzar }: { empresaId: number; onAvanzar: () => void }) {
  const { register, handleSubmit } = useForm<DatosFacturaScripts>()

  const mutation = useMutation({
    mutationFn: (datos: DatosFacturaScripts) => actualizarFacturaScripts(empresaId, datos),
    onSuccess: onAvanzar,
  })

  const saltar = () => onAvanzar()

  return (
    <form onSubmit={handleSubmit((d) => mutation.mutate(d))} className="space-y-4">
      <h2 className="text-xl font-semibold">Paso 4: FacturaScripts</h2>
      <p className="text-sm text-muted-foreground">
        Si ya tienes esta empresa en FacturaScripts, introduce los identificadores para sincronización.
        Puedes saltarlo si no usas FacturaScripts o lo configurarás más adelante.
      </p>

      <div>
        <Label htmlFor="idempresa_fs">ID empresa en FacturaScripts</Label>
        <Input
          id="idempresa_fs"
          type="number"
          min={1}
          placeholder="1"
          {...register('idempresa_fs', { valueAsNumber: true })}
        />
      </div>

      <div>
        <Label htmlFor="codejercicio_fs">Código ejercicio en FacturaScripts</Label>
        <Input
          id="codejercicio_fs"
          placeholder="0001 / C422..."
          {...register('codejercicio_fs')}
        />
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
          {mutation.error instanceof Error ? mutation.error.message : 'Error al guardar'}
        </p>
      )}
    </form>
  )
}
