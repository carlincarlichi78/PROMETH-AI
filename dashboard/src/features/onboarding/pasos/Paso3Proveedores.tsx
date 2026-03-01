import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useMutation } from '@tanstack/react-query'
import { anadirProveedor, ProveedorHabitual } from '../api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'

export function Paso3Proveedores({ empresaId, onAvanzar }: { empresaId: number; onAvanzar: () => void }) {
  const [anadidos, setAnadidos] = useState<ProveedorHabitual[]>([])
  const { register, handleSubmit, reset, formState: { errors } } = useForm<ProveedorHabitual>()

  const mutation = useMutation({
    mutationFn: (datos: ProveedorHabitual) => anadirProveedor(empresaId, datos),
    onSuccess: (_, datos) => {
      setAnadidos((prev) => [...prev, datos])
      reset()
    },
  })

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">Paso 3: Proveedores habituales</h2>
      <p className="text-sm text-muted-foreground">
        Añade los proveedores recurrentes (luz, teléfono, alquiler...). Puedes saltarlo y añadirlos después.
      </p>

      <form onSubmit={handleSubmit((d) => mutation.mutate(d))} className="space-y-3 border rounded-lg p-4">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label htmlFor="prov-cif">CIF proveedor</Label>
            <Input id="prov-cif" placeholder="A12345678" {...register('cif', { required: 'Obligatorio' })} />
            {errors.cif && <p className="text-xs text-red-500 mt-1">{errors.cif.message}</p>}
          </div>
          <div>
            <Label htmlFor="prov-nombre">Nombre</Label>
            <Input id="prov-nombre" placeholder="Endesa Energía S.A." {...register('nombre', { required: 'Obligatorio' })} />
            {errors.nombre && <p className="text-xs text-red-500 mt-1">{errors.nombre.message}</p>}
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label htmlFor="prov-email">Email (opcional)</Label>
            <Input id="prov-email" type="email" {...register('email')} />
          </div>
          <div>
            <Label htmlFor="prov-subcuenta">Subcuenta gasto (opcional)</Label>
            <Input id="prov-subcuenta" placeholder="6280000000" {...register('subcuenta_gasto')} />
          </div>
        </div>
        <Button type="submit" size="sm" disabled={mutation.isPending}>
          {mutation.isPending ? 'Añadiendo...' : '+ Añadir proveedor'}
        </Button>
        {mutation.isError && (
          <p className="text-xs text-red-500">
            {mutation.error instanceof Error ? mutation.error.message : 'Error al añadir'}
          </p>
        )}
      </form>

      {anadidos.length > 0 && (
        <div className="space-y-1">
          <p className="text-sm font-medium">Añadidos:</p>
          <div className="flex flex-wrap gap-2">
            {anadidos.map((p) => (
              <Badge key={p.cif} variant="secondary">{p.nombre} ({p.cif})</Badge>
            ))}
          </div>
        </div>
      )}

      <Button onClick={onAvanzar} className="w-full">
        {anadidos.length > 0 ? 'Continuar →' : 'Saltar este paso'}
      </Button>
    </div>
  )
}
