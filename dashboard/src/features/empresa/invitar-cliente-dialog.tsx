import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { UserPlus, Copy, Check } from 'lucide-react'

interface Props {
  empresaId: number
}

interface ResultadoInvitacion {
  id: number
  email: string
  nombre?: string
  rol: string
  invitacion_url?: string
  mensaje?: string
}

export function InvitarClienteDialog({ empresaId }: Props) {
  const [abierto, setAbierto] = useState(false)
  const [copiado, setCopiado] = useState(false)
  const [urlInv, setUrlInv] = useState<string | null>(null)
  const [form, setForm] = useState({ email: '', nombre: '' })

  const invitar = useMutation({
    mutationFn: async (datos: { email: string; nombre: string }) => {
      const token = sessionStorage.getItem('sfce_token') ?? ''
      const res = await fetch(`/api/empresas/${empresaId}/invitar-cliente`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(datos),
      })
      if (!res.ok) throw new Error(`${res.status}`)
      return res.json() as Promise<ResultadoInvitacion>
    },
    onSuccess: (data) => {
      if (data.invitacion_url) {
        setUrlInv(data.invitacion_url)
      }
    },
  })

  const copiar = () => {
    if (urlInv) {
      navigator.clipboard.writeText(window.location.origin + urlInv)
      setCopiado(true)
      setTimeout(() => setCopiado(false), 2000)
    }
  }

  const cerrar = (v: boolean) => {
    setAbierto(v)
    if (!v) {
      setUrlInv(null)
      setForm({ email: '', nombre: '' })
      invitar.reset()
    }
  }

  return (
    <Dialog open={abierto} onOpenChange={cerrar}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="gap-2">
          <UserPlus className="h-4 w-4" />
          Invitar cliente
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Invitar cliente al portal</DialogTitle>
        </DialogHeader>
        {urlInv ? (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">
              Invitación lista. Comparte este enlace con tu cliente:
            </p>
            <div className="flex gap-2">
              <Input
                readOnly
                value={window.location.origin + urlInv}
                className="text-xs"
              />
              <Button size="icon" variant="outline" onClick={copiar}>
                {copiado ? (
                  <Check className="h-4 w-4 text-green-500" />
                ) : (
                  <Copy className="h-4 w-4" />
                )}
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">Caduca en 7 días.</p>
          </div>
        ) : (
          <form
            onSubmit={(e) => {
              e.preventDefault()
              invitar.mutate(form)
            }}
            className="space-y-4"
          >
            <div>
              <Label htmlFor="nombre">Nombre del cliente</Label>
              <Input
                id="nombre"
                value={form.nombre}
                onChange={(e) => setForm({ ...form, nombre: e.target.value })}
                required
              />
            </div>
            <div>
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                required
              />
            </div>
            <Button
              type="submit"
              disabled={invitar.isPending}
              className="w-full"
            >
              {invitar.isPending ? 'Enviando...' : 'Crear invitación'}
            </Button>
            {invitar.isError && (
              <p className="text-sm text-red-500">Error al crear invitación</p>
            )}
          </form>
        )}
      </DialogContent>
    </Dialog>
  )
}
