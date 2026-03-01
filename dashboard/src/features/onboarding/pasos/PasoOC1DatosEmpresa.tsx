import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

const schema = z.object({
  domicilio: z.string().min(5, 'Direccion requerida'),
  telefono: z.string().optional(),
  persona_contacto: z.string().min(2, 'Nombre de contacto requerido'),
})

type Datos = z.infer<typeof schema>

interface Props {
  onAvanzar: (datos: Datos) => void
}

export function PasoOC1DatosEmpresa({ onAvanzar }: Props) {
  const { register, handleSubmit, formState: { errors } } = useForm<Datos>({
    resolver: zodResolver(schema),
  })

  return (
    <form onSubmit={handleSubmit(onAvanzar)} className="space-y-4">
      <h2 className="text-xl font-semibold">Paso 1: Datos de tu empresa</h2>
      <p className="text-sm text-muted-foreground">Confirma los datos de contacto de tu empresa.</p>

      <div>
        <Label htmlFor="domicilio">Domicilio fiscal</Label>
        <Input id="domicilio" placeholder="Calle Mayor 1, 28001 Madrid" {...register('domicilio')} />
        {errors.domicilio && <p className="text-sm text-red-500 mt-1">{errors.domicilio.message}</p>}
      </div>

      <div>
        <Label htmlFor="telefono">Telefono (opcional)</Label>
        <Input id="telefono" placeholder="600 000 000" {...register('telefono')} />
      </div>

      <div>
        <Label htmlFor="persona_contacto">Persona de contacto</Label>
        <Input id="persona_contacto" placeholder="Juan Garcia" {...register('persona_contacto')} />
        {errors.persona_contacto && <p className="text-sm text-red-500 mt-1">{errors.persona_contacto.message}</p>}
      </div>

      <Button type="submit" className="w-full">Siguiente &rarr;</Button>
    </form>
  )
}
