import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { listarCuentas, crearCuenta, sincronizarCuenta, eliminarCuenta, CuentaImap } from './api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { RefreshCw, Trash2, Plus } from 'lucide-react'

interface FormCuenta {
  servidor: string
  puerto: number
  usuario: string
  password: string
}

export function CuentasCorreo({ empresaId }: { empresaId: number }) {
  const [mostrarForm, setMostrarForm] = useState(false)
  const qc = useQueryClient()

  const { data: cuentas, isLoading } = useQuery({
    queryKey: ['correo-cuentas', empresaId],
    queryFn: () => listarCuentas(empresaId),
  })

  const { register, handleSubmit, reset, formState: { errors } } = useForm<FormCuenta>({
    defaultValues: { puerto: 993 },
  })

  const crearMutation = useMutation({
    mutationFn: (datos: FormCuenta) =>
      crearCuenta({ empresa_id: empresaId, protocolo: 'imap', ...datos }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['correo-cuentas', empresaId] })
      reset({ puerto: 993 })
      setMostrarForm(false)
    },
  })

  const syncMutation = useMutation({
    mutationFn: sincronizarCuenta,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['correo-emails', empresaId] }),
  })

  const eliminarMutation = useMutation({
    mutationFn: eliminarCuenta,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['correo-cuentas', empresaId] }),
  })

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-base">Cuentas IMAP configuradas</CardTitle>
        <Button size="sm" variant="outline" onClick={() => setMostrarForm(!mostrarForm)}>
          <Plus className="w-4 h-4 mr-1" /> Nueva cuenta
        </Button>
      </CardHeader>
      <CardContent className="space-y-3">
        {mostrarForm && (
          <form
            onSubmit={handleSubmit((d) => crearMutation.mutate(d))}
            className="border rounded-lg p-4 space-y-3 bg-muted/30"
          >
            <div className="grid grid-cols-3 gap-3">
              <div className="col-span-2">
                <Label>Servidor IMAP</Label>
                <Input placeholder="imap.gmail.com" {...register('servidor', { required: true })} />
                {errors.servidor && <p className="text-xs text-red-500">Obligatorio</p>}
              </div>
              <div>
                <Label>Puerto</Label>
                <Input type="number" {...register('puerto', { valueAsNumber: true })} />
              </div>
            </div>
            <div>
              <Label>Usuario</Label>
              <Input type="email" {...register('usuario', { required: true })} />
            </div>
            <div>
              <Label>Contraseña / App Password</Label>
              <Input type="password" {...register('password', { required: true })} />
            </div>
            <div className="flex gap-2">
              <Button type="submit" size="sm" disabled={crearMutation.isPending}>
                {crearMutation.isPending ? 'Guardando...' : 'Guardar'}
              </Button>
              <Button type="button" size="sm" variant="ghost" onClick={() => setMostrarForm(false)}>
                Cancelar
              </Button>
            </div>
            {crearMutation.isError && (
              <p className="text-xs text-red-500">Error al guardar la cuenta</p>
            )}
          </form>
        )}

        {isLoading && <p className="text-sm text-muted-foreground">Cargando cuentas...</p>}

        {cuentas?.map((c: CuentaImap) => (
          <div key={c.id} className="flex items-center justify-between p-3 border rounded-lg">
            <div>
              <p className="font-medium text-sm">{c.usuario}</p>
              <p className="text-xs text-muted-foreground">{c.servidor}</p>
              {c.ultimo_sync && (
                <p className="text-xs text-muted-foreground">
                  Último sync: {new Date(c.ultimo_sync).toLocaleDateString('es-ES')}
                </p>
              )}
            </div>
            <div className="flex items-center gap-2">
              <Badge variant={c.activa ? 'default' : 'secondary'}>
                {c.activa ? 'Activa' : 'Inactiva'}
              </Badge>
              <Button
                size="sm"
                variant="outline"
                onClick={() => syncMutation.mutate(c.id)}
                disabled={syncMutation.isPending && syncMutation.variables === c.id}
              >
                <RefreshCw className="w-3 h-3 mr-1" /> Sync
              </Button>
              <Button
                size="sm"
                variant="ghost"
                className="text-destructive"
                onClick={() => eliminarMutation.mutate(c.id)}
              >
                <Trash2 className="w-3 h-3" />
              </Button>
            </div>
          </div>
        ))}

        {cuentas?.length === 0 && !mostrarForm && (
          <p className="text-sm text-muted-foreground text-center py-4">
            No hay cuentas IMAP configuradas.
          </p>
        )}
      </CardContent>
    </Card>
  )
}
