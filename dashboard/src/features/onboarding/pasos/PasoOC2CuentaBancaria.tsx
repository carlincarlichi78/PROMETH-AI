import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

const schema = z.object({
  iban: z.string().min(15).max(34).regex(/^[A-Z]{2}\d{2}/, 'Formato IBAN invalido'),
  banco_nombre: z.string().min(2, 'Nombre del banco requerido'),
})

type Datos = z.infer<typeof schema>

interface Props {
  onAvanzar: (datos: Datos) => void
}

export function PasoOC2CuentaBancaria({ onAvanzar }: Props) {
  const { register, handleSubmit, formState: { errors } } = useForm<Datos>({
    resolver: zodResolver(schema),
  })

  return (
    <form onSubmit={handleSubmit(onAvanzar)} className="space-y-4">
      <h2 className="text-xl font-semibold">Paso 2: Cuenta bancaria</h2>
      <p className="text-sm text-muted-foreground">
        Tu IBAN permite a la gestoria realizar la conciliacion bancaria automaticamente.
      </p>

      <div>
        <Label htmlFor="iban">IBAN</Label>
        <Input id="iban" placeholder="ES91 2100 0418 4502 0005 1332" {...register('iban')} />
        {errors.iban && <p className="text-sm text-red-500 mt-1">{errors.iban.message}</p>}
      </div>

      <div>
        <Label htmlFor="banco_nombre">Banco</Label>
        <Input id="banco_nombre" placeholder="CaixaBank" {...register('banco_nombre')} />
        {errors.banco_nombre && <p className="text-sm text-red-500 mt-1">{errors.banco_nombre.message}</p>}
      </div>

      <Button type="submit" className="w-full">Siguiente &rarr;</Button>
    </form>
  )
}
