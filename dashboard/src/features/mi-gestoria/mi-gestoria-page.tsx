import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Users, UserPlus, Mail, CheckCircle, Clock, Copy, Check,
} from 'lucide-react'
import { listarMisUsuarios, invitarGestor } from './api'
import type { InvitarGestorDto, ResultadoInvitacion } from './api'
import { useAuth } from '@/context/AuthContext'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Card, CardHeader, CardTitle, CardDescription,
} from '@/components/ui/card'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
  DialogFooter, DialogTrigger,
} from '@/components/ui/dialog'

// --- Formulario de invitacion ---

interface FormularioInvitacionProps {
  gestoriaId: number
  onExito: (resultado: ResultadoInvitacion) => void
}

function FormularioInvitacion({ gestoriaId, onExito }: FormularioInvitacionProps) {
  const qc = useQueryClient()
  const [form, setForm] = useState<InvitarGestorDto>({ nombre: '', email: '' })
  const [error, setError] = useState<string | null>(null)

  const mutacion = useMutation({
    mutationFn: (datos: InvitarGestorDto) => invitarGestor(gestoriaId, datos),
    onSuccess: (resultado) => {
      qc.invalidateQueries({ queryKey: ['mi-gestoria', 'usuarios', gestoriaId] })
      onExito(resultado)
    },
    onError: (err: Error) => {
      setError(err.message)
    },
  })

  const manejarEnvio = (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    if (!form.nombre.trim() || !form.email.trim()) {
      setError('Nombre y email son obligatorios')
      return
    }
    mutacion.mutate(form)
  }

  return (
    <form onSubmit={manejarEnvio} className="space-y-4">
      <div className="space-y-1.5">
        <Label htmlFor="nombre-gestor">Nombre</Label>
        <Input
          id="nombre-gestor"
          value={form.nombre}
          onChange={(e) => setForm((prev) => ({ ...prev, nombre: e.target.value }))}
          placeholder="Nombre del gestor"
          required
        />
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="email-gestor">Email</Label>
        <Input
          id="email-gestor"
          type="email"
          value={form.email}
          onChange={(e) => setForm((prev) => ({ ...prev, email: e.target.value }))}
          placeholder="gestor@ejemplo.com"
          required
        />
      </div>
      {error && (
        <p className="text-sm text-destructive">{error}</p>
      )}
      <DialogFooter>
        <Button type="submit" disabled={mutacion.isPending}>
          {mutacion.isPending ? 'Enviando...' : 'Enviar invitacion'}
        </Button>
      </DialogFooter>
    </form>
  )
}

// --- Panel de URL de invitacion ---

function PanelInvitacion({
  resultado,
  onCerrar,
}: {
  resultado: ResultadoInvitacion
  onCerrar: () => void
}) {
  const [copiado, setCopiado] = useState(false)

  const copiarUrl = async () => {
    try {
      await navigator.clipboard.writeText(resultado.invitacion_url)
      setCopiado(true)
      setTimeout(() => setCopiado(false), 2000)
    } catch {
      // fallback para navegadores sin permisos de portapapeles
    }
  }

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-green-500/30 bg-green-500/10 p-4 space-y-2">
        <p className="text-sm font-medium text-green-700 dark:text-green-400">
          Invitacion enviada a {resultado.email}
        </p>
        <p className="text-xs text-muted-foreground">
          Comparte este enlace con el gestor para que complete su registro:
        </p>
        <div className="flex items-center gap-2 mt-2">
          <code className="flex-1 text-xs bg-muted rounded px-2 py-1.5 truncate select-all">
            {resultado.invitacion_url}
          </code>
          <Button variant="outline" size="sm" onClick={copiarUrl} className="flex-shrink-0">
            {copiado ? (
              <Check className="h-3.5 w-3.5 text-green-500" />
            ) : (
              <Copy className="h-3.5 w-3.5" />
            )}
          </Button>
        </div>
      </div>
      <DialogFooter>
        <Button onClick={onCerrar}>Cerrar</Button>
      </DialogFooter>
    </div>
  )
}

// --- Pagina principal ---

export default function MiGestoriaPage() {
  const { usuario } = useAuth()
  const gestoriaId = usuario?.gestoria_id ?? null
  const [dialogAbierto, setDialogAbierto] = useState(false)
  const [invitacionResultado, setInvitacionResultado] = useState<ResultadoInvitacion | null>(null)

  const { data: usuarios = [], isLoading, isError } = useQuery({
    queryKey: ['mi-gestoria', 'usuarios', gestoriaId],
    queryFn: () => listarMisUsuarios(gestoriaId as number),
    enabled: gestoriaId !== null,
  })

  const manejarDialogOpenChange = (abierto: boolean) => {
    setDialogAbierto(abierto)
    if (!abierto) setInvitacionResultado(null)
  }

  if (!gestoriaId) {
    return (
      <div className="p-6 max-w-2xl">
        <div className="rounded-lg border border-destructive/50 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          Tu cuenta no esta asociada a ninguna gestoria. Contacta con el administrador.
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 max-w-4xl space-y-6">
      {/* Cabecera */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Mi equipo</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {isLoading
              ? 'Cargando...'
              : `${usuarios.length} ${usuarios.length === 1 ? 'usuario' : 'usuarios'} en tu gestoria`}
          </p>
        </div>

        <Dialog open={dialogAbierto} onOpenChange={manejarDialogOpenChange}>
          <DialogTrigger asChild>
            <Button>
              <UserPlus className="h-4 w-4 mr-2" />
              Invitar gestor
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>
                {invitacionResultado ? 'Invitacion generada' : 'Invitar gestor'}
              </DialogTitle>
            </DialogHeader>
            {invitacionResultado ? (
              <PanelInvitacion
                resultado={invitacionResultado}
                onCerrar={() => manejarDialogOpenChange(false)}
              />
            ) : (
              <FormularioInvitacion
                gestoriaId={gestoriaId}
                onExito={(resultado) => setInvitacionResultado(resultado)}
              />
            )}
          </DialogContent>
        </Dialog>
      </div>

      {/* Error */}
      {isError && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          Error al cargar los usuarios. Verifica que el backend este en ejecucion.
        </div>
      )}

      {/* Skeleton de carga */}
      {isLoading && (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 rounded-xl border bg-card animate-pulse" />
          ))}
        </div>
      )}

      {/* Estado vacio */}
      {!isLoading && !isError && usuarios.length === 0 && (
        <div className="text-center py-16 text-muted-foreground">
          <Users className="mx-auto h-10 w-10 mb-3 opacity-40" />
          <p className="text-sm">No hay gestores en tu equipo aun.</p>
          <p className="text-xs mt-1">Invita al primero usando el boton de arriba.</p>
        </div>
      )}

      {/* Lista de usuarios */}
      {!isLoading && !isError && usuarios.length > 0 && (
        <div className="space-y-3">
          {usuarios.map((u) => (
            <Card key={u.id}>
              <CardHeader className="py-3 px-4">
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="h-9 w-9 rounded-full bg-primary/10 flex items-center justify-center text-sm font-semibold text-primary flex-shrink-0">
                      {u.nombre.charAt(0).toUpperCase()}
                    </div>
                    <div className="min-w-0">
                      <CardTitle className="text-sm truncate">{u.nombre}</CardTitle>
                      <CardDescription className="flex items-center gap-1 text-xs mt-0.5">
                        <Mail className="h-3 w-3 flex-shrink-0" />
                        <span className="truncate">{u.email}</span>
                      </CardDescription>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 flex-shrink-0">
                    <Badge variant="outline" className="text-xs capitalize">
                      {u.rol}
                    </Badge>
                    <Badge
                      variant={u.activo ? 'default' : 'secondary'}
                      className="flex items-center gap-1 text-xs"
                    >
                      {u.activo ? (
                        <>
                          <CheckCircle className="h-3 w-3" />
                          Activo
                        </>
                      ) : (
                        <>
                          <Clock className="h-3 w-3" />
                          Pendiente
                        </>
                      )}
                    </Badge>
                  </div>
                </div>
              </CardHeader>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
