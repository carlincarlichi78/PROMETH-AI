import { useForm, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation } from '@tanstack/react-query'
import { crearEmpresa, DatosBasicosEmpresa } from '../api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'

const schema = z.object({
  cif: z.string().min(9).max(9),
  nombre: z.string().min(3),
  forma_juridica: z.enum(['autonomo', 'sl', 'sa', 'cb', 'sc', 'coop']),
  territorio: z.enum(['peninsula', 'canarias', 'ceuta']),
  regimen_iva: z.enum(['general', 'simplificado', 'recargo_equivalencia']),
})

export function Paso1DatosBasicos({ onAvanzar }: { onAvanzar: (id: number) => void }) {
  const { register, handleSubmit, control, formState: { errors } } = useForm<DatosBasicosEmpresa>({
    resolver: zodResolver(schema),
    defaultValues: { forma_juridica: 'sl', territorio: 'peninsula', regimen_iva: 'general' },
  })

  const mutation = useMutation({
    mutationFn: crearEmpresa,
    onSuccess: (data) => onAvanzar(data.id),
  })

  return (
    <form onSubmit={handleSubmit((d) => mutation.mutate(d))} className="space-y-4">
      <h2 className="text-xl font-semibold">Paso 1: Datos básicos</h2>

      <div>
        <Label htmlFor="cif">CIF / NIF</Label>
        <Input id="cif" placeholder="B12345678" {...register('cif')} />
        {errors.cif && <p className="text-sm text-red-500 mt-1">{errors.cif.message}</p>}
      </div>

      <div>
        <Label htmlFor="nombre">Nombre / Razón social</Label>
        <Input id="nombre" placeholder="Mi Empresa S.L." {...register('nombre')} />
        {errors.nombre && <p className="text-sm text-red-500 mt-1">{errors.nombre.message}</p>}
      </div>

      <div>
        <Label>Forma jurídica</Label>
        <Controller
          name="forma_juridica"
          control={control}
          render={({ field }) => (
            <Select value={field.value} onValueChange={field.onChange}>
              <SelectTrigger><SelectValue placeholder="Seleccionar..." /></SelectTrigger>
              <SelectContent>
                <SelectItem value="autonomo">Autónomo</SelectItem>
                <SelectItem value="sl">S.L.</SelectItem>
                <SelectItem value="sa">S.A.</SelectItem>
                <SelectItem value="cb">C.B.</SelectItem>
                <SelectItem value="sc">S.C.</SelectItem>
                <SelectItem value="coop">Cooperativa</SelectItem>
              </SelectContent>
            </Select>
          )}
        />
        {errors.forma_juridica && <p className="text-sm text-red-500 mt-1">{errors.forma_juridica.message}</p>}
      </div>

      <div>
        <Label>Territorio</Label>
        <Controller
          name="territorio"
          control={control}
          render={({ field }) => (
            <Select value={field.value} onValueChange={field.onChange}>
              <SelectTrigger><SelectValue placeholder="Seleccionar..." /></SelectTrigger>
              <SelectContent>
                <SelectItem value="peninsula">Península e Islas Baleares</SelectItem>
                <SelectItem value="canarias">Canarias</SelectItem>
                <SelectItem value="ceuta">Ceuta / Melilla</SelectItem>
              </SelectContent>
            </Select>
          )}
        />
      </div>

      <div>
        <Label>Régimen de IVA</Label>
        <Controller
          name="regimen_iva"
          control={control}
          render={({ field }) => (
            <Select value={field.value} onValueChange={field.onChange}>
              <SelectTrigger><SelectValue placeholder="Seleccionar..." /></SelectTrigger>
              <SelectContent>
                <SelectItem value="general">General</SelectItem>
                <SelectItem value="simplificado">Simplificado</SelectItem>
                <SelectItem value="recargo_equivalencia">Recargo de equivalencia</SelectItem>
              </SelectContent>
            </Select>
          )}
        />
      </div>

      <Button type="submit" disabled={mutation.isPending} className="w-full">
        {mutation.isPending ? 'Creando empresa...' : 'Siguiente →'}
      </Button>
      {mutation.isError && (
        <p className="text-sm text-red-500">
          {mutation.error instanceof Error ? mutation.error.message : 'Error al crear empresa'}
        </p>
      )}
    </form>
  )
}
