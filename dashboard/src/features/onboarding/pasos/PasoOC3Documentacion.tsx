import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { X } from 'lucide-react'

const schema = z.object({
  email_facturas: z.string().email('Email invalido'),
})

type FormDatos = z.infer<typeof schema>
type Datos = FormDatos & { proveedores: string[] }

interface Props {
  onAvanzar: (datos: Datos) => void
}

export function PasoOC3Documentacion({ onAvanzar }: Props) {
  const [proveedores, setProveedores] = useState<string[]>([])
  const [inputProveedor, setInputProveedor] = useState('')
  const { register, handleSubmit, formState: { errors } } = useForm<FormDatos>({
    resolver: zodResolver(schema),
  })

  const agregarProveedor = () => {
    const nombre = inputProveedor.trim()
    if (nombre && !proveedores.includes(nombre)) {
      setProveedores([...proveedores, nombre])
      setInputProveedor('')
    }
  }

  const quitarProveedor = (p: string) => setProveedores(proveedores.filter((x) => x !== p))

  return (
    <form onSubmit={handleSubmit((d) => onAvanzar({ ...d, proveedores }))} className="space-y-4">
      <h2 className="text-xl font-semibold">Paso 3: Documentacion</h2>
      <p className="text-sm text-muted-foreground">
        Indica donde recibiras las facturas y tus proveedores habituales.
      </p>

      <div>
        <Label htmlFor="email_facturas">Email de recepcion de facturas</Label>
        <Input
          id="email_facturas"
          type="email"
          placeholder="facturas@miempresa.com"
          {...register('email_facturas')}
        />
        {errors.email_facturas && (
          <p className="text-sm text-red-500 mt-1">{errors.email_facturas.message}</p>
        )}
      </div>

      <div className="space-y-2">
        <Label>Proveedores habituales (opcional)</Label>
        <div className="flex gap-2">
          <Input
            placeholder="Repsol, Endesa..."
            value={inputProveedor}
            onChange={(e) => setInputProveedor(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault()
                agregarProveedor()
              }
            }}
          />
          <Button type="button" variant="outline" onClick={agregarProveedor}>
            Anadir
          </Button>
        </div>
        <div className="flex flex-wrap gap-2 pt-1">
          {proveedores.map((p) => (
            <Badge
              key={p}
              variant="secondary"
              className="gap-1 cursor-pointer"
              onClick={() => quitarProveedor(p)}
            >
              {p} <X className="h-3 w-3" />
            </Badge>
          ))}
        </div>
      </div>

      <Button type="submit" className="w-full">Completar onboarding</Button>
    </form>
  )
}
