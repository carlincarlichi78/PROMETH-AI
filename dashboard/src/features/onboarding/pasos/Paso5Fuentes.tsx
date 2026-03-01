import { useState } from 'react'
import { useForm, Controller } from 'react-hook-form'
import { useMutation } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { anadirFuenteCorreo, FuenteCorreo } from '../api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'

interface Props {
  empresaId: number
  onAvanzar?: () => void
}

export function Paso5Fuentes({ empresaId }: Props) {
  const [anadidas, setAnadidas] = useState<string[]>([])
  const navigate = useNavigate()
  const { register, handleSubmit, control, reset, formState: { errors } } = useForm<FuenteCorreo>({
    defaultValues: { protocolo: 'imap', puerto: 993 },
  })

  const mutation = useMutation({
    mutationFn: (datos: FuenteCorreo) => anadirFuenteCorreo(empresaId, datos),
    onSuccess: (_, datos) => {
      setAnadidas((prev) => [...prev, datos.usuario])
      reset({ protocolo: 'imap', puerto: 993 })
    },
  })

  const finalizar = () => {
    navigate(`/empresa/${empresaId}`)
  }

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">Paso 5: Fuentes de documentos</h2>
      <p className="text-sm text-muted-foreground">
        Conecta cuentas de correo IMAP para que SFCE recoja facturas automáticamente.
        Puedes saltarlo y configurarlo después en Configuración → Integraciones.
      </p>

      <form onSubmit={handleSubmit((d) => mutation.mutate(d))} className="space-y-3 border rounded-lg p-4">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label htmlFor="servidor">Servidor IMAP</Label>
            <Input id="servidor" placeholder="imap.gmail.com" {...register('servidor', { required: 'Obligatorio' })} />
            {errors.servidor && <p className="text-xs text-red-500 mt-1">{errors.servidor.message}</p>}
          </div>
          <div>
            <Label htmlFor="puerto">Puerto</Label>
            <Input id="puerto" type="number" {...register('puerto', { valueAsNumber: true, required: 'Obligatorio' })} />
          </div>
        </div>

        <div>
          <Label htmlFor="usuario">Usuario (email)</Label>
          <Input id="usuario" type="email" placeholder="facturas@miempresa.com" {...register('usuario', { required: 'Obligatorio' })} />
          {errors.usuario && <p className="text-xs text-red-500 mt-1">{errors.usuario.message}</p>}
        </div>

        <div>
          <Label htmlFor="password">Contraseña / App Password</Label>
          <Input id="password" type="password" {...register('password', { required: 'Obligatorio' })} />
        </div>

        <div>
          <Label>Protocolo</Label>
          <Controller
            name="protocolo"
            control={control}
            render={({ field }) => (
              <Select value={field.value} onValueChange={field.onChange}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="imap">IMAP</SelectItem>
                  <SelectItem value="pop3">POP3</SelectItem>
                </SelectContent>
              </Select>
            )}
          />
        </div>

        <Button type="submit" size="sm" disabled={mutation.isPending}>
          {mutation.isPending ? 'Conectando...' : '+ Añadir cuenta'}
        </Button>
        {mutation.isError && (
          <p className="text-xs text-red-500">
            {mutation.error instanceof Error ? mutation.error.message : 'Error al añadir cuenta'}
          </p>
        )}
      </form>

      {anadidas.length > 0 && (
        <div className="space-y-1">
          <p className="text-sm font-medium">Cuentas conectadas:</p>
          <div className="flex flex-wrap gap-2">
            {anadidas.map((u) => (
              <Badge key={u} variant="secondary">{u}</Badge>
            ))}
          </div>
        </div>
      )}

      <Button onClick={finalizar} className="w-full">
        {anadidas.length > 0 ? '¡Listo! Ir a la empresa' : 'Finalizar (sin fuentes)'}
      </Button>
    </div>
  )
}
