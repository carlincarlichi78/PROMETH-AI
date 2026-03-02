import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { FileText } from 'lucide-react'
import { PageHeader } from '@/components/page-header'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { Card, CardContent } from '@/components/ui/card'
import {
  Table, TableBody, TableCell, TableHead,
  TableHeader, TableRow,
} from '@/components/ui/table'
import { api } from '@/lib/api-client'
import { formatearImporte } from '@/lib/formatters'

interface Perceptor {
  nif: string | null
  nombre: string
  clave_percepcion: 'A' | 'E'
  percepcion_dineraria: number
  retencion_dineraria: number
  porcentaje_retencion: number
  completo: boolean
  campos_faltantes: string[]
  doc_ids: number[]
}

interface Resultado190 {
  empresa_id: number
  ejercicio: number
  completos: Perceptor[]
  incompletos: Perceptor[]
  puede_generar: boolean
  total_percepciones: number
  total_retenciones: number
}

function PerceptorRow({
  perceptor,
  onCorregir,
}: {
  perceptor: Perceptor
  onCorregir: (nif: string, datos: Record<string, unknown>) => void
}) {
  const [editando, setEditando] = useState(false)
  const [nifEdit, setNifEdit] = useState(perceptor.nif ?? '')
  const [percepcionEdit, setPercepcionEdit] = useState(String(perceptor.percepcion_dineraria))
  const [retencionEdit, setRetencionEdit] = useState(String(perceptor.retencion_dineraria))

  const guardar = () => {
    onCorregir(perceptor.nif ?? nifEdit, {
      nif: nifEdit,
      nombre: perceptor.nombre,
      clave_percepcion: perceptor.clave_percepcion,
      percepcion_dineraria: parseFloat(percepcionEdit),
      retencion_dineraria: parseFloat(retencionEdit),
    })
    setEditando(false)
  }

  return (
    <TableRow className={perceptor.completo ? '' : 'bg-red-50 dark:bg-red-950/20'}>
      <TableCell className="font-mono text-sm">
        {editando ? (
          <Input value={nifEdit} onChange={(e) => setNifEdit(e.target.value)} className="h-7 w-28" />
        ) : (
          perceptor.nif ?? <span className="text-red-500 italic">Sin NIF</span>
        )}
      </TableCell>
      <TableCell className="text-sm max-w-48 truncate">{perceptor.nombre}</TableCell>
      <TableCell>
        <Badge variant={perceptor.clave_percepcion === 'A' ? 'default' : 'secondary'}>
          {perceptor.clave_percepcion === 'A' ? 'Trabajo' : 'Profesional'}
        </Badge>
      </TableCell>
      <TableCell className="text-right text-sm">
        {editando ? (
          <Input
            value={percepcionEdit}
            onChange={(e) => setPercepcionEdit(e.target.value)}
            className="h-7 w-28 text-right"
          />
        ) : (
          formatearImporte(perceptor.percepcion_dineraria)
        )}
      </TableCell>
      <TableCell className="text-right text-sm">
        {editando ? (
          <Input
            value={retencionEdit}
            onChange={(e) => setRetencionEdit(e.target.value)}
            className="h-7 w-28 text-right"
          />
        ) : (
          formatearImporte(perceptor.retencion_dineraria)
        )}
      </TableCell>
      <TableCell className="text-right text-sm">
        {perceptor.porcentaje_retencion.toFixed(2)}%
      </TableCell>
      <TableCell>
        {perceptor.completo ? (
          <Badge variant="outline" className="text-green-600 border-green-600">Completo</Badge>
        ) : editando ? (
          <div className="flex gap-1">
            <Button size="sm" onClick={guardar}>Guardar</Button>
            <Button size="sm" variant="ghost" onClick={() => setEditando(false)}>Cancelar</Button>
          </div>
        ) : (
          <Button size="sm" variant="destructive" onClick={() => setEditando(true)}>
            Corregir
          </Button>
        )}
      </TableCell>
    </TableRow>
  )
}

export default function Modelo190Page() {
  const { id } = useParams<{ id: string }>()
  const empresaId = id ? parseInt(id) : null
  const ejercicio = new Date().getFullYear() - 1

  const [perceptoresLocales, setPerceptoresLocales] = useState<Perceptor[] | null>(null)
  const [generando, setGenerando] = useState(false)

  const { data, isLoading, error } = useQuery<Resultado190>({
    queryKey: ['190-perceptores', empresaId, ejercicio],
    queryFn: () => api.get(`/api/modelos/190/${empresaId}/${ejercicio}/perceptores`) as Promise<Resultado190>,
    enabled: !!empresaId,
  })

  const corregirMutation = useMutation({
    mutationFn: ({ nif, datos }: { nif: string; datos: Record<string, unknown> }) =>
      api.put(`/api/modelos/190/${empresaId}/${ejercicio}/perceptores/${nif}`, datos) as Promise<Perceptor>,
    onSuccess: (corregido) => {
      const base = perceptoresLocales ?? [...(data?.completos ?? []), ...(data?.incompletos ?? [])]
      setPerceptoresLocales(
        base.map((p) => (p.nif === corregido.nif ? { ...p, ...corregido } : p))
      )
    },
  })

  const descargarBoe = async () => {
    const todos = perceptoresLocales ?? [...(data?.completos ?? []), ...(data?.incompletos ?? [])]
    setGenerando(true)
    try {
      const token = sessionStorage.getItem('sfce_token')
      const r = await fetch(`/api/modelos/190/${empresaId}/${ejercicio}/generar`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ perceptores: todos }),
      })
      if (!r.ok) throw new Error(await r.text())
      const blob = await r.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `190_${empresaId}_${ejercicio}.txt`
      a.click()
      URL.revokeObjectURL(url)
    } finally {
      setGenerando(false)
    }
  }

  if (!empresaId) {
    return (
      <div className="p-6">
        <PageHeader titulo="Modelo 190" descripcion="Resumen anual retenciones IRPF" />
        <p className="text-muted-foreground mt-4">Selecciona una empresa para continuar.</p>
      </div>
    )
  }

  const todos: Perceptor[] = perceptoresLocales ?? [
    ...(data?.completos ?? []),
    ...(data?.incompletos ?? []),
  ]
  const numIncompletos = todos.filter((p) => !p.completo).length
  const puedeGenerar = numIncompletos === 0
  const totalPercepciones = todos.reduce((s, p) => s + p.percepcion_dineraria, 0)
  const totalRetenciones = todos.reduce((s, p) => s + p.retencion_dineraria, 0)

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        titulo="Modelo 190"
        descripcion={`Resumen anual retenciones IRPF — Ejercicio ${ejercicio}`}
        acciones={
          <Tooltip>
            <TooltipTrigger asChild>
              <span>
                <Button
                  onClick={descargarBoe}
                  disabled={!puedeGenerar || generando}
                >
                  <FileText className="mr-2 h-4 w-4" />
                  {generando ? 'Generando...' : 'Generar fichero 190'}
                </Button>
              </span>
            </TooltipTrigger>
            {numIncompletos > 0 && (
              <TooltipContent>
                {numIncompletos} perceptor{numIncompletos > 1 ? 'es' : ''} incompleto{numIncompletos > 1 ? 's' : ''} — corrígelos antes de generar
              </TooltipContent>
            )}
          </Tooltip>
        }
      />

      {/* KPIs */}
      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">Perceptores</p>
            <p className="text-3xl font-bold">{todos.length}</p>
            {numIncompletos > 0 && (
              <p className="text-xs text-red-500 mt-1">{numIncompletos} incompleto{numIncompletos > 1 ? 's' : ''}</p>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">Total percepciones</p>
            <p className="text-3xl font-bold">{formatearImporte(totalPercepciones)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">Total retenciones</p>
            <p className="text-3xl font-bold">{formatearImporte(totalRetenciones)}</p>
          </CardContent>
        </Card>
      </div>

      {/* Tabla */}
      {isLoading && <p className="text-muted-foreground">Cargando perceptores...</p>}
      {error && <p className="text-red-500">Error: {(error as Error).message}</p>}
      {!isLoading && todos.length === 0 && !error && (
        <p className="text-muted-foreground">
          No hay nóminas ni facturas con retención procesadas para el ejercicio {ejercicio}.
        </p>
      )}
      {todos.length > 0 && (
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>NIF</TableHead>
                <TableHead>Nombre</TableHead>
                <TableHead>Tipo</TableHead>
                <TableHead className="text-right">Percepciones</TableHead>
                <TableHead className="text-right">Retenciones</TableHead>
                <TableHead className="text-right">% Ret.</TableHead>
                <TableHead>Estado</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {todos.map((p, i) => (
                <PerceptorRow
                  key={p.nif ?? `incompleto-${i}`}
                  perceptor={p}
                  onCorregir={(nif, datos) => corregirMutation.mutate({ nif, datos })}
                />
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  )
}
