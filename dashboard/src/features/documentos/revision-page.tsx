import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select"
import { PageTitle } from "@/components/ui/page-title"

const BASE = import.meta.env.VITE_API_URL ?? ""
async function apiFetch(path: string, opts?: RequestInit) {
  const token = localStorage.getItem("sfce_token")
  const res = await fetch(`${BASE}${path}`, {
    ...opts,
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}), ...opts?.headers },
  })
  if (!res.ok) throw new Error(`${res.status}`)
  return res.json()
}

interface DocRevision {
  id: number
  cola_id: number
  nombre: string
  tipo_doc: string
  empresa_id: number
  empresa_nombre: string
  fecha_subida: string | null
  datos_ocr?: Record<string, unknown>
}

function useDocsRevision() {
  return useQuery<DocRevision[]>({
    queryKey: ["docs-revision"],
    queryFn: () => apiFetch("/api/gestor/documentos/revision"),
  })
}

function useAprobar(empresaId: number, docId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (hints: Record<string, unknown>) =>
      apiFetch(`/api/portal/${empresaId}/documentos/${docId}/aprobar`, {
        method: "POST",
        body: JSON.stringify(hints),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["docs-revision"] }),
  })
}

function useRechazar(empresaId: number, docId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (motivo: string) =>
      apiFetch(`/api/portal/${empresaId}/documentos/${docId}/rechazar`, {
        method: "POST",
        body: JSON.stringify({ motivo }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["docs-revision"] }),
  })
}

const TIPOS_DOC = ["FC", "FV", "NC", "SUM", "NOM", "BAN", "RLC", "IMP"]

function DocCard({ doc }: { doc: DocRevision }) {
  const ocr = (doc.datos_ocr || {}) as Record<string, string>
  const [tipo, setTipo] = useState(doc.tipo_doc || "FV")
  const [cif, setCif] = useState(ocr.proveedor_cif || "")
  const [nombre, setNombre] = useState(ocr.proveedor_nombre || "")
  const [total, setTotal] = useState(ocr.total ? String(ocr.total) : "")

  const aprobar = useAprobar(doc.empresa_id, doc.id)
  const rechazar = useRechazar(doc.empresa_id, doc.id)

  return (
    <Card className="mb-4">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium truncate max-w-xs">{doc.nombre}</CardTitle>
          <Badge variant="outline">{doc.empresa_nombre}</Badge>
        </div>
        {doc.fecha_subida && (
          <p className="text-xs text-muted-foreground">
            {new Date(doc.fecha_subida).toLocaleString("es-ES")}
          </p>
        )}
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="text-xs text-muted-foreground block mb-1">Tipo</label>
            <Select value={tipo} onValueChange={setTipo}>
              <SelectTrigger className="h-8">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {TIPOS_DOC.map((t) => (
                  <SelectItem key={t} value={t}>{t}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <label className="text-xs text-muted-foreground block mb-1">Total (€)</label>
            <Input
              className="h-8"
              value={total}
              onChange={(e) => setTotal(e.target.value)}
              placeholder="0.00"
            />
          </div>
          <div>
            <label className="text-xs text-muted-foreground block mb-1">CIF proveedor</label>
            <Input
              className="h-8"
              value={cif}
              onChange={(e) => setCif(e.target.value)}
              placeholder="B12345678"
            />
          </div>
          <div>
            <label className="text-xs text-muted-foreground block mb-1">Nombre proveedor</label>
            <Input
              className="h-8"
              value={nombre}
              onChange={(e) => setNombre(e.target.value)}
            />
          </div>
        </div>
        <div className="flex gap-2 pt-1">
          <Button
            size="sm"
            className="flex-1"
            onClick={() =>
              aprobar.mutate({
                tipo_doc: tipo,
                proveedor_cif: cif || undefined,
                proveedor_nombre: nombre || undefined,
                total: parseFloat(total) || undefined,
              })
            }
            disabled={aprobar.isPending}
          >
            {aprobar.isPending ? "Aprobando..." : "Aprobar"}
          </Button>
          <Button
            size="sm"
            variant="destructive"
            onClick={() => rechazar.mutate("Rechazado por gestor")}
            disabled={rechazar.isPending}
          >
            {rechazar.isPending ? "Rechazando..." : "Rechazar"}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

export function RevisionPage() {
  const { data: docs = [], isLoading } = useDocsRevision()

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <PageTitle
        titulo="Documentos pendientes de revisión"
        subtitulo="Enriquece y aprueba los documentos antes de procesarlos"
      />
      {isLoading && <p className="text-muted-foreground mt-4">Cargando...</p>}
      {!isLoading && docs.length === 0 && (
        <p className="text-muted-foreground mt-8 text-center">
          No hay documentos pendientes de revisión.
        </p>
      )}
      {docs.map((doc) => (
        <DocCard key={doc.id} doc={doc} />
      ))}
    </div>
  )
}
