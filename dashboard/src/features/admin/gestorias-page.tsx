import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Building2, Users, CheckCircle, XCircle } from 'lucide-react'
import { listarGestorias, crearGestoria } from './api'
import type { CrearGestoriaDto } from './api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogTrigger,
} from '@/components/ui/dialog'

const QUERY_KEY = ['admin', 'gestorias'] as const

function FormularioGestoria({ onExito }: { onExito: () => void }) {
  const qc = useQueryClient()
  const [form, setForm] = useState<CrearGestoriaDto>({
    nombre: '',
    email_contacto: '',
    cif: '',
    plan_asesores: 5,
  })
  const [error, setError] = useState<string | null>(null)

  const mutacion = useMutation({
    mutationFn: (datos: CrearGestoriaDto) => crearGestoria(datos),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEY })
      onExito()
    },
    onError: (err: Error) => {
      setError(err.message)
    },
  })

  const manejarEnvio = (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    if (!form.nombre.trim() || !form.email_contacto.trim() || !form.cif.trim()) {
      setError('Nombre, email y CIF son obligatorios')
      return
    }
    mutacion.mutate(form)
  }

  return (
    <form onSubmit={manejarEnvio} className="space-y-4">
      <div className="space-y-1.5">
        <Label htmlFor="nombre">Nombre de la gestoria</Label>
        <Input
          id="nombre"
          value={form.nombre}
          onChange={(e) => setForm((prev) => ({ ...prev, nombre: e.target.value }))}
          placeholder="Gestoria Ejemplo S.L."
          required
        />
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="cif">CIF</Label>
        <Input
          id="cif"
          value={form.cif}
          onChange={(e) => setForm((prev) => ({ ...prev, cif: e.target.value }))}
          placeholder="B12345678"
          required
        />
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="email">Email de contacto</Label>
        <Input
          id="email"
          type="email"
          value={form.email_contacto}
          onChange={(e) => setForm((prev) => ({ ...prev, email_contacto: e.target.value }))}
          placeholder="contacto@gestoria.com"
          required
        />
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="plan_asesores">Plan asesores (max)</Label>
        <Input
          id="plan_asesores"
          type="number"
          min={1}
          max={100}
          value={form.plan_asesores}
          onChange={(e) =>
            setForm((prev) => ({ ...prev, plan_asesores: parseInt(e.target.value, 10) || 1 }))
          }
        />
      </div>
      {error && (
        <p className="text-sm text-destructive">{error}</p>
      )}
      <DialogFooter>
        <Button type="submit" disabled={mutacion.isPending}>
          {mutacion.isPending ? 'Creando...' : 'Crear gestoria'}
        </Button>
      </DialogFooter>
    </form>
  )
}

export default function GestoriasPage() {
  const navigate = useNavigate()
  const [dialogAbierto, setDialogAbierto] = useState(false)

  const { data: gestorias = [], isLoading, isError } = useQuery({
    queryKey: QUERY_KEY,
    queryFn: listarGestorias,
  })

  return (
    <div className="p-6 max-w-5xl space-y-6">
      {/* Cabecera */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Gestorias</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {isLoading ? 'Cargando...' : `${gestorias.length} gestorias registradas`}
          </p>
        </div>
        <Dialog open={dialogAbierto} onOpenChange={setDialogAbierto}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Nueva gestoria
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Nueva gestoria</DialogTitle>
            </DialogHeader>
            <FormularioGestoria onExito={() => setDialogAbierto(false)} />
          </DialogContent>
        </Dialog>
      </div>

      {/* Estados de carga / error */}
      {isLoading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-40 rounded-xl border bg-card animate-pulse" />
          ))}
        </div>
      )}

      {isError && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          Error al cargar las gestorias. Verifica que el backend este en ejecucion.
        </div>
      )}

      {/* Grid de cards */}
      {!isLoading && !isError && gestorias.length === 0 && (
        <div className="text-center py-16 text-muted-foreground">
          <Building2 className="mx-auto h-10 w-10 mb-3 opacity-40" />
          <p className="text-sm">No hay gestorias registradas aun.</p>
        </div>
      )}

      {!isLoading && !isError && gestorias.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {gestorias.map((g) => (
            <Card
              key={g.id}
              className="cursor-pointer hover:shadow-md transition-shadow"
              onClick={() => navigate(`/admin/gestorias/${g.id}`)}
            >
              <CardHeader>
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <div className="h-8 w-8 rounded-md bg-primary/10 flex items-center justify-center flex-shrink-0">
                      <Building2 className="h-4 w-4 text-primary" />
                    </div>
                    <div className="min-w-0">
                      <CardTitle className="text-sm truncate">{g.nombre}</CardTitle>
                      <CardDescription className="text-xs">{g.cif}</CardDescription>
                    </div>
                  </div>
                  <Badge
                    variant={g.activa ? 'default' : 'secondary'}
                    className="flex-shrink-0 flex items-center gap-1"
                  >
                    {g.activa ? (
                      <CheckCircle className="h-3 w-3" />
                    ) : (
                      <XCircle className="h-3 w-3" />
                    )}
                    {g.activa ? 'Activa' : 'Inactiva'}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <Users className="h-3.5 w-3.5" />
                  <span>Hasta {g.plan_asesores} asesores</span>
                </div>
                <div className="text-xs text-muted-foreground truncate">
                  {g.email_contacto}
                </div>
                {g.plan_clientes_tramo && (
                  <div className="text-xs text-muted-foreground">
                    Tramo: {g.plan_clientes_tramo}
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
