import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { CuentaCorreoCard } from "./cuenta-correo-card"
import { useAuth } from "@/context/AuthContext"
import { PageTitle } from "@/components/ui/page-title"

interface NuevaCuentaForm {
  nombre: string
  tipo_cuenta: string
  servidor: string
  puerto: number
  ssl: boolean
  usuario: string
  contrasena: string
  gestoria_id?: number
  empresa_id?: number
  usuario_id?: number
}

async function fetchCuentas(token: string) {
  const r = await fetch("/api/correo/admin/cuentas", {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!r.ok) throw new Error("Error cargando cuentas")
  return r.json()
}

async function crearCuenta(token: string, datos: NuevaCuentaForm) {
  const r = await fetch("/api/correo/admin/cuentas", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(datos),
  })
  if (!r.ok) throw new Error("Error creando cuenta")
  return r.json()
}

async function desactivarCuenta(token: string, id: number) {
  const r = await fetch(`/api/correo/admin/cuentas/${id}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!r.ok) throw new Error("Error desactivando cuenta")
  return r.json()
}

export function CuentasCorreoPage() {
  const { token } = useAuth()
  const tokenStr = token ?? ""
  const qc = useQueryClient()
  const [abierto, setAbierto] = useState(false)
  const [form, setForm] = useState<NuevaCuentaForm>({
    nombre: "",
    tipo_cuenta: "gestoria",
    servidor: "imap.zoho.eu",
    puerto: 993,
    ssl: true,
    usuario: "",
    contrasena: "",
  })

  const { data: cuentas = [], isLoading } = useQuery({
    queryKey: ["cuentas-correo"],
    queryFn: () => fetchCuentas(tokenStr),
  })

  const crearMut = useMutation({
    mutationFn: (datos: NuevaCuentaForm) => crearCuenta(tokenStr, datos),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cuentas-correo"] })
      setAbierto(false)
    },
  })

  const desactivarMut = useMutation({
    mutationFn: (id: number) => desactivarCuenta(tokenStr, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["cuentas-correo"] }),
  })

  const testConexionMut = useMutation({
    mutationFn: async (id: number) => {
      const r = await fetch(`/api/correo/admin/cuentas/${id}/test`, {
        method: "POST",
        headers: { Authorization: `Bearer ${tokenStr}` },
      })
      return r.json()
    },
    onSuccess: (data) => {
      alert(data.ok ? "✓ Conexión exitosa" : `✗ Error: ${data.mensaje}`)
    },
  })

  const porTipo = (tipo: string) => cuentas.filter((c: any) => c.tipo_cuenta === tipo)

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <PageTitle titulo="Cuentas de correo" subtitulo="Buzones IMAP y SMTP Zoho" />
        <Dialog open={abierto} onOpenChange={setAbierto}>
          <DialogTrigger asChild>
            <Button size="sm">Nueva cuenta</Button>
          </DialogTrigger>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle>Añadir cuenta de correo</DialogTitle>
            </DialogHeader>
            <div className="space-y-3 mt-2">
              <div>
                <Label>Nombre</Label>
                <Input
                  value={form.nombre}
                  onChange={(e) => setForm({ ...form, nombre: e.target.value })}
                  placeholder="Gestoría López"
                />
              </div>
              <div>
                <Label>Tipo</Label>
                <Select value={form.tipo_cuenta} onValueChange={(v) => setForm({ ...form, tipo_cuenta: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="dedicada">Catch-all (docs@prometh-ai.es)</SelectItem>
                    <SelectItem value="gestoria">Gestoría</SelectItem>
                    <SelectItem value="sistema">Sistema (noreply)</SelectItem>
                    <SelectItem value="empresa">Empresa individual</SelectItem>
                    <SelectItem value="asesor">Asesor (IMAP personal)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Servidor IMAP</Label>
                <Input
                  value={form.servidor}
                  onChange={(e) => setForm({ ...form, servidor: e.target.value })}
                />
              </div>
              <div>
                <Label>Usuario (email)</Label>
                <Input
                  value={form.usuario}
                  onChange={(e) => setForm({ ...form, usuario: e.target.value })}
                  placeholder="gestoria1@prometh-ai.es"
                />
              </div>
              <div>
                <Label>Contraseña Zoho</Label>
                <Input
                  type="password"
                  value={form.contrasena}
                  onChange={(e) => setForm({ ...form, contrasena: e.target.value })}
                />
              </div>
              <Button
                className="w-full"
                onClick={() => crearMut.mutate(form)}
                disabled={crearMut.isPending}
              >
                {crearMut.isPending ? "Guardando..." : "Guardar"}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {isLoading && <p className="text-muted-foreground text-sm">Cargando...</p>}

      {["dedicada", "sistema", "gestoria", "empresa"].map((tipo) => {
        const lista = porTipo(tipo)
        if (!lista.length) return null
        const labels: Record<string, string> = {
          dedicada: "Catch-all", sistema: "Sistema", gestoria: "Gestoría", empresa: "Empresa",
        }
        return (
          <div key={tipo}>
            <h3 className="text-sm font-semibold text-muted-foreground mb-2 uppercase tracking-wide">
              {labels[tipo]}
            </h3>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {lista.map((c: any) => (
                <CuentaCorreoCard key={c.id} cuenta={c} onDesactivar={desactivarMut.mutate} />
              ))}
            </div>
          </div>
        )
      })}

      {/* Cuentas IMAP Asesores */}
      <div className="mt-8">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-3">
          Cuentas IMAP — Asesores individuales
        </h3>
        {porTipo("asesor").length === 0 ? (
          <p className="text-sm text-muted-foreground">Sin cuentas asesor configuradas.</p>
        ) : (
          <div className="space-y-2">
            {porTipo("asesor").map((c: any) => (
              <div key={c.id} className="flex items-center justify-between p-3 rounded-lg border bg-card">
                <div>
                  <p className="font-medium text-sm">{c.nombre}</p>
                  <p className="text-xs text-muted-foreground">{c.usuario}</p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={c.activa ? "default" : "secondary"}>
                    {c.activa ? "Activa" : "Inactiva"}
                  </Badge>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => testConexionMut.mutate(c.id)}
                    disabled={testConexionMut.isPending}
                  >
                    Probar
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => desactivarMut.mutate(c.id)}
                  >
                    Desactivar
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
