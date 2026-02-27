import { useState, useEffect } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { FileText, Calculator } from 'lucide-react'
import { PageHeader } from '@/components/page-header'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { api } from '@/lib/api-client'
import { queryKeys } from '@/lib/query-keys'
import { formatearImporte } from '@/lib/formatters'

interface ModeloDisponible {
  codigo: string
  nombre: string
  tipo: 'trimestral' | 'anual'
  descripcion: string
}

interface RespuestaDisponibles {
  modelos: ModeloDisponible[]
}

interface Casilla {
  codigo: string
  descripcion: string
  valor: number | string
}

interface ResultadoModelo {
  modelo: string
  periodo: string
  ejercicio: string
  casillas: Casilla[]
  resultado_total: number
}

const MODELOS_OPCIONES = [
  { codigo: '303', tipo: 'trimestral' },
  { codigo: '111', tipo: 'trimestral' },
  { codigo: '130', tipo: 'trimestral' },
  { codigo: '349', tipo: 'trimestral' },
  { codigo: '390', tipo: 'anual' },
  { codigo: '347', tipo: 'anual' },
]

const PERIODOS_TRIMESTRALES = [
  { value: 'T1', label: '1T (Enero – Marzo)' },
  { value: 'T2', label: '2T (Abril – Junio)' },
  { value: 'T3', label: '3T (Julio – Septiembre)' },
  { value: 'T4', label: '4T (Octubre – Diciembre)' },
]

const PERIODO_ANUAL = [{ value: 'anual', label: 'Anual' }]

function esNumerico(v: number | string): v is number {
  return typeof v === 'number'
}

export default function GenerarPage() {
  const { id } = useParams<{ id: string }>()
  const [searchParams] = useSearchParams()
  const empresaId = Number(id)

  const modeloInicial = searchParams.get('modelo') ?? ''

  const [modeloSeleccionado, setModeloSeleccionado] = useState(modeloInicial)
  const [periodoSeleccionado, setPeriodoSeleccionado] = useState('')

  // Resetear periodo al cambiar modelo
  useEffect(() => {
    setPeriodoSeleccionado('')
  }, [modeloSeleccionado])

  const { data: disponibles } = useQuery({
    queryKey: queryKeys.modelos.disponibles,
    queryFn: () => api.get<RespuestaDisponibles>('/api/modelos/disponibles'),
  })

  const modeloActual = MODELOS_OPCIONES.find((m) => m.codigo === modeloSeleccionado)
  const esAnual = modeloActual?.tipo === 'anual'
  const periodosOpciones = esAnual ? PERIODO_ANUAL : PERIODOS_TRIMESTRALES

  const enabled = !!modeloSeleccionado && !!periodoSeleccionado

  const { data: resultado, isLoading: calculando, isError } = useQuery({
    queryKey: queryKeys.modelos.calcular(empresaId, modeloSeleccionado, periodoSeleccionado),
    queryFn: () =>
      api.post<ResultadoModelo>(`/api/modelos/${empresaId}/calcular`, {
        modelo: modeloSeleccionado,
        periodo: periodoSeleccionado,
      }),
    enabled,
  })

  const nombresDisponibles: Record<string, string> = {}
  if (disponibles?.modelos) {
    for (const m of disponibles.modelos) {
      nombresDisponibles[m.codigo] = m.nombre
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader titulo="Generar Modelo Fiscal" />

      {/* Formulario */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Selecciona modelo y periodo</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-4 items-end">
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Modelo</label>
              <Select value={modeloSeleccionado} onValueChange={setModeloSeleccionado}>
                <SelectTrigger className="w-52">
                  <SelectValue placeholder="Seleccionar modelo..." />
                </SelectTrigger>
                <SelectContent>
                  {MODELOS_OPCIONES.map((m) => (
                    <SelectItem key={m.codigo} value={m.codigo}>
                      {m.codigo}
                      {nombresDisponibles[m.codigo] ? ` — ${nombresDisponibles[m.codigo]}` : ''}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-medium">Periodo</label>
              <Select
                value={periodoSeleccionado}
                onValueChange={setPeriodoSeleccionado}
                disabled={!modeloSeleccionado}
              >
                <SelectTrigger className="w-52">
                  <SelectValue placeholder="Seleccionar periodo..." />
                </SelectTrigger>
                <SelectContent>
                  {periodosOpciones.map((p) => (
                    <SelectItem key={p.value} value={p.value}>
                      {p.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex gap-2">
              <Button
                disabled={!enabled || calculando}
                variant="default"
                onClick={() => {/* useQuery se activa por enabled */}}
              >
                <Calculator className="h-4 w-4 mr-1.5" />
                {calculando ? 'Calculando...' : 'Calcular'}
              </Button>

              <Tooltip>
                <TooltipTrigger asChild>
                  <span>
                    <Button disabled variant="outline">
                      <FileText className="h-4 w-4 mr-1.5" />
                      Generar PDF
                    </Button>
                  </span>
                </TooltipTrigger>
                <TooltipContent>Requiere configuracion</TooltipContent>
              </Tooltip>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Resultado */}
      {calculando && (
        <Card>
          <CardHeader>
            <Skeleton className="h-5 w-48" />
          </CardHeader>
          <CardContent className="space-y-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </CardContent>
        </Card>
      )}

      {isError && !calculando && (
        <Card className="border-destructive">
          <CardContent className="py-6 text-center text-destructive text-sm">
            Error al calcular el modelo. Verifica que los datos del periodo esten disponibles.
          </CardContent>
        </Card>
      )}

      {resultado && !calculando && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              Modelo {resultado.modelo} · {resultado.periodo} · Ejercicio {resultado.ejercicio}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-24">Casilla</TableHead>
                    <TableHead>Descripcion</TableHead>
                    <TableHead className="text-right w-40">Valor</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {resultado.casillas.map((c) => (
                    <TableRow key={c.codigo}>
                      <TableCell className="font-mono text-sm font-medium">{c.codigo}</TableCell>
                      <TableCell className="text-sm">{c.descripcion}</TableCell>
                      <TableCell className="text-right text-sm">
                        {esNumerico(c.valor) ? formatearImporte(c.valor) : String(c.valor)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

            <div className="flex justify-end">
              <div className="rounded-lg bg-muted px-6 py-3 text-right">
                <p className="text-xs text-muted-foreground mb-1">Resultado total</p>
                <p className="text-2xl font-bold">
                  {formatearImporte(resultado.resultado_total)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
